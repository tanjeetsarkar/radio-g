import redis
import uuid
import asyncio
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import json
import os
from pathlib import Path

# Add parent directory to path for imports
from services.kafka_consumer import NewsKafkaConsumer
from models.news_item import ProcessedNewsItem
from services.language_manager import get_language_manager
from config.config import get_config
from config.logging_config import setup_logging, get_logger
from utils.health import HealthChecker

# Initialize configuration
config = get_config()

# Setup logging
setup_logging(log_level=config.app.log_level, json_format=config.is_production())
logger = get_logger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Multilingual News Radio API",
    description="Production API for streaming multilingual news broadcasts",
    version="2.0.0",
    docs_url="/docs" if not config.is_production() else None,
    redoc_url="/redoc" if not config.is_production() else None,
)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class NewsItemResponse(BaseModel):
    id: str
    title: str
    url: str
    category: str
    source: str
    language: str
    summary: str
    translated_summary: str
    translated_title: Optional[str]
    audio_file: str
    audio_duration: float
    published_date: str
    processed_at: str


class PlaylistResponse(BaseModel):
    language: str
    total_items: int
    items: List[NewsItemResponse]


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    environment: str


# Globals
# Dynamic in-memory cache: { "en": [items], "es": [items] }
news_cache: Dict[str, List[ProcessedNewsItem]] = defaultdict(list)

# Thread-safe lock for cache operations
cache_lock = asyncio.Lock()

# Background task reference for graceful shutdown
background_task: Optional[asyncio.Task] = None

# Single Kafka consumer for all languages (using regex subscription)
kafka_consumer: Optional[NewsKafkaConsumer] = None

# Language Manager for dynamic config
language_manager = get_language_manager()

# Health checker
health_checker: Optional[HealthChecker] = None


def initialize_kafka_consumers():
    """
    Initialize a single Kafka consumer that subscribes to all language topics.
    Uses a unique group ID per instance to ensure every API worker builds a full cache.
    """
    global kafka_consumer

    # Generate unique group ID for this worker/instance
    # This ensures Fan-Out pattern: every API instance gets all messages
    unique_group_id = f"api-consumer-{uuid.uuid4().hex[:8]}"

    try:
        kafka_consumer = NewsKafkaConsumer(
            bootstrap_servers=config.kafka.connection_config,
            group_id=unique_group_id,
            auto_offset_reset="earliest",  # Start from beginning to build cache
            manage_signals=False,
            return_raw=True,
        )

        # Subscribe to all topics starting with 'news-'
        # Note: This requires the regex support in confluent-kafka
        kafka_consumer.subscribe(["^news-.*"])

        logger.info(f"✓ Initialized dynamic consumer (Group: {unique_group_id})")
        logger.info("  Subscribed to pattern: ^news-.*")

    except Exception as e:
        logger.error(f"Failed to initialize consumer: {e}", exc_info=True)


async def update_cache(max_messages: int = 50):
    """
    Consume a batch of messages from any language topic and update the cache.
    This runs blindly on the single consumer stream.
    Thread-safe with asyncio.Lock.
    """
    if not kafka_consumer:
        logger.warning("Kafka consumer not initialized")
        return

    messages_processed = 0

    # Consume a batch of messages
    for _ in range(max_messages):
        try:
            # Poll with short timeout (run in executor to not block event loop)
            msg = await asyncio.get_event_loop().run_in_executor(
                None, kafka_consumer.consumer.poll, 0.1
            )

            if msg is None:
                break

            if msg.error():
                continue

            # Parse message
            value = msg.value().decode("utf-8")
            data = json.loads(value)

            # Convert to object
            item = ProcessedNewsItem.from_dict(data)

            # Add to appropriate language bucket with lock
            lang_code = item.language

            async with cache_lock:
                # Deduplicate by ID
                existing_ids = {x.original_id for x in news_cache[lang_code]}

                if item.original_id not in existing_ids:
                    news_cache[lang_code].append(item)
                    # Sort by date descending
                    news_cache[lang_code].sort(key=lambda x: x.published_date, reverse=True)
                    # Keep only latest 50
                    news_cache[lang_code] = news_cache[lang_code][:50]
                    messages_processed += 1

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            continue

    if messages_processed > 0:
        logger.info(f"Cache updated: processed {messages_processed} new items")


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = datetime.utcnow()
    response = await call_next(request)
    duration = (datetime.utcnow() - start_time).total_seconds()

    # Skip health check logging to reduce noise
    if request.url.path not in ["/health", "/live", "/ready"]:
        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_seconds": round(duration, 3),
                "client_host": request.client.host if request.client else None,
            },
        )
    return response


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("Starting Multilingual News Radio API (Dynamic)...")
    logger.info(f"Environment: {config.environment}")

    try:
        initialize_kafka_consumers()

        # Build Redis connection params
        redis_params = {
            'host': config.redis.host,
            'port': config.redis.port,
            'db': config.redis.db,
            'username': config.redis.username,  # <--- ADDED
            'decode_responses': True,
        }
        
        # Only add password if it's not None and not empty
        if config.redis.password:
            redis_params['password'] = config.redis.password
        
        # Only add SSL if True
        if config.redis.ssl:
            redis_params['ssl'] = config.redis.ssl
        
        redis_client = redis.Redis(**redis_params)

        # Initialize health checker
        global health_checker
        health_checker = HealthChecker(
            redis_client=redis_client, kafka_config=config.kafka.connection_config
        )

        # Initial cache warm-up (try to fetch existing history)
        logger.info("Warming up cache...")
        await update_cache(max_messages=200)

        # Start background polling task
        global background_task
        background_task = asyncio.create_task(background_cache_updater())
        logger.info("✓ Background cache updater started (30s interval)")

        logger.info("✓ API ready")
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise


async def background_cache_updater():
    """Background task to continuously update cache from Kafka"""
    poll_interval = int(os.getenv("CACHE_UPDATE_INTERVAL_SECONDS", "30"))
    logger.info(f"Starting background cache updater (interval: {poll_interval}s)")
    
    while True:
        try:
            await asyncio.sleep(poll_interval)
            await update_cache(max_messages=20)
        except asyncio.CancelledError:
            logger.info("Background cache updater cancelled")
            break
        except Exception as e:
            logger.error(f"Error in background cache updater: {e}", exc_info=True)
            # Continue running even if there's an error
            await asyncio.sleep(poll_interval)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down API...")
    
    # Cancel background task
    if background_task:
        logger.info("Cancelling background cache updater...")
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
        logger.info("✓ Background task cancelled")
    
    # Close Kafka consumer
    if kafka_consumer:
        logger.info("Closing Kafka consumer...")
        kafka_consumer.close()
        logger.info("✓ Kafka consumer closed")
    
    logger.info("✓ API shutdown complete")


@app.get("/")
async def root():
    """API root with dynamic language list"""
    # Get enabled languages dynamically
    lang_config = language_manager.get_config()
    available_langs = [
        code for code, cfg in lang_config.items() if cfg.get("enabled", True)
    ]

    return {
        "name": "Multilingual News Radio API",
        "version": "2.0.0",
        "environment": config.environment,
        "languages": available_langs,
        "endpoints": {
            "health": "/health",
            "playlist": "/playlist/{language}",
            "audio": "/audio/{filename}",
            "languages": "/languages",
        },
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check"""
    if health_checker:
        health = health_checker.full_health_check()
        return {
            "status": health["status"],
            "timestamp": health["timestamp"],
            "version": "2.0.0",
            "environment": config.environment,
        }
    return {
        "status": "unknown",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "environment": config.environment,
    }


@app.get("/ready")
async def readiness_check():
    """Readiness probe"""
    if health_checker and health_checker.readiness_check():
        return {"status": "ready"}
    raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/live")
async def liveness_check():
    """Liveness probe"""
    if health_checker and health_checker.liveness_check():
        return {"status": "alive"}
    raise HTTPException(status_code=503, detail="Service not alive")


@app.get("/playlist/{language}", response_model=PlaylistResponse)
async def get_playlist(
    language: str,
    limit: Optional[int] = Query(20, ge=1, le=50),
    category: Optional[str] = None,
):
    """Get playlist for a specific language"""
    # Validate language against dynamic config
    lang_config = language_manager.get_config()
    if language not in lang_config:
        # Check if it's a valid code but maybe just not explicitly configured?
        # For safety, we only allow configured languages
        raise HTTPException(
            status_code=404, detail=f"Language '{language}' not configured or not found"
        )

    try:
        # Get items from cache (background task keeps it updated)
        items = news_cache[language]

        # Filter by category if specified
        if category:
            items = [
                item for item in items if item.category.lower() == category.lower()
            ]

        # Limit items
        items = items[:limit]

        # Convert to response format
        response_items = []
        for item in items:
            # Handle backward compatibility - cache may have ProcessedNewsItem objects or dicts
            try:
                # Extract values safely handling both formats
                if isinstance(item, ProcessedNewsItem):
                    translated_title = item.translated_title or item.original_title
                    response_items.append(
                        NewsItemResponse(
                            id=item.original_id or "",
                            title=item.original_title,
                            url=item.original_url,
                            category=item.category,
                            source=item.source,
                            language=item.language,
                            summary=item.summary,
                            translated_summary=item.translated_summary,
                            translated_title=translated_title,
                            audio_file=Path(item.audio_file).name,
                            audio_duration=item.audio_duration,
                            published_date=item.published_date,
                            processed_at=item.processed_at,
                        )
                    )
                else:
                    # Handle dict format (shouldn't happen but for safety)
                    logger.warning("Cache contains dict format, should be ProcessedNewsItem")
                    continue
            except Exception as e:
                logger.error(f"Error converting item to response: {e}", exc_info=True)
                continue

        return PlaylistResponse(
            language=language, total_items=len(response_items), items=response_items
        )
    except Exception as e:
        logger.error(f"Error getting playlist for {language}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch playlist")


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """Stream audio file or redirect to GCS URL"""
    try:
        # Check if any processed item has this audio file
        # First check if it's a GCS URL (stored in cache)
        for items in news_cache.values():
            for item in items:
                # Handle ProcessedNewsItem objects
                if isinstance(item, ProcessedNewsItem):
                    audio_file = item.audio_file
                else:
                    # Skip invalid cache entries
                    continue
                
                # If audio_file is a full GCS URL, redirect to it
                if audio_file and audio_file.startswith("https://"):
                    # Extract filename from URL and compare
                    if filename in audio_file:
                        logger.info(f"Redirecting to GCS URL: {audio_file}")
                        return RedirectResponse(url=audio_file, status_code=302)
                # If audio_file is just filename, check if it matches
                elif audio_file and audio_file.endswith(filename):
                    # It's a local file, continue to serve it
                    break
        
        # Fallback to serving from local filesystem
        # audio_output/ is for production audio files
        audio_dir = Path(config.app.audio_output_dir)
        audio_path = audio_dir / filename

        if not audio_path.exists():
            logger.warning(f"Audio file not found: {audio_path}")
            raise HTTPException(status_code=404, detail=f"Audio file not found: {filename}")

        # Handle mock files for dev/testing (0-byte files with .json metadata)
        if audio_path.stat().st_size == 0:
            metadata_path = audio_path.with_suffix(".json")
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                logger.info(f"Returning mock audio metadata for: {filename}")
                return {
                    "message": "Mock audio file",
                    "filename": filename,
                    "metadata": metadata,
                }
            else:
                logger.warning(f"Empty audio file without metadata: {filename}")
                raise HTTPException(status_code=404, detail="Audio file is empty and has no metadata")

        # Serve real audio file with proper headers for streaming
        return FileResponse(
            audio_path,
            media_type="audio/mpeg",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Disposition": f"inline; filename={filename}"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving audio {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to serve audio")


@app.get("/refresh/{language}")
async def refresh_playlist(language: str):
    """Manually trigger playlist refresh (pulls from Kafka)"""
    try:
        # We consume from the shared stream
        update_cache(max_messages=50)

        return {
            "message": "Refreshed cache (scanned 50 messages)",
            "items_in_cache": len(news_cache[language]),
        }
    except Exception as e:
        logger.error(f"Error refreshing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to refresh")


@app.get("/languages")
async def get_languages():
    """Get available languages with dynamic metadata and item counts"""
    config = language_manager.get_config()
    response = []

    for code, details in config.items():
        if details.get("enabled", True):
            response.append(
                {
                    "code": code,
                    "name": details.get("name", code.title()),
                    "flag": details.get("flag", "🌐"),
                    "items": len(news_cache[code]),
                }
            )

    # Sort by name
    response.sort(key=lambda x: x["name"])

    return {"languages": response}