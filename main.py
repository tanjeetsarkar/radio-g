import redis
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json
import os
from pathlib import Path

# Add parent directory to path for imports

from services.kafka_consumer import NewsKafkaConsumer
from processing_consumer import ProcessedNewsItem
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
    version="1.0.0",
    docs_url="/docs" if not config.is_production() else None,  # Disable docs in prod
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


# In-memory cache for news items
news_cache: dict[str, List[ProcessedNewsItem]] = {"en": [], "hi": [], "bn": []}

# Kafka consumers (one per language)
kafka_consumers: dict[str, NewsKafkaConsumer] = {}

# Health checker
health_checker: Optional[HealthChecker] = None


def initialize_kafka_consumers():
    """Initialize Kafka consumers for each language"""
    topic_mapping = {"en": "news-english", "hi": "news-hindi", "bn": "news-bengali"}

    kafka_config = config.kafka.connection_config

    for lang, topic in topic_mapping.items():
        try:
            consumer = NewsKafkaConsumer(
                bootstrap_servers=config.kafka.bootstrap_servers,
                group_id=f"api-consumer-{lang}-V2",
                auto_offset_reset="latest",
                manage_signals=False,
            )
            consumer.subscribe([topic])
            kafka_consumers[lang] = consumer
            logger.info(f"✓ Initialized consumer for {lang} ({topic})")
        except Exception as e:
            logger.error(
                f"Failed to initialize consumer for {lang}: {e}", exc_info=True
            )


def fetch_latest_news(language: str, max_items: int = 20) -> List[ProcessedNewsItem]:
    """Fetch latest news from Kafka for a language"""
    if language not in kafka_consumers:
        logger.warning(f"No consumer for language: {language}")
        return []


    consumer = kafka_consumers[language]
    items = []

    # Consume available messages
    for _ in range(max_items):
        try:
            msg = consumer.consume_message(timeout=0.5)
            logger.info(f"Got Message: {msg}")
            if msg is None:
                break

            # Parse the ProcessedNewsItem from JSON
            if isinstance(msg, dict):
                item = ProcessedNewsItem.from_dict(msg)
            else:
                continue

            items.append(item)

        except Exception as e:
            logger.error(f"Error consuming message for {language}: {e}")
            break

    return items


def update_cache(language: str):
    """Update cache with latest news"""
    try:
        new_items = fetch_latest_news(language, max_items=20)
        logger.info(f"new items: {new_items}")
        if new_items:
            # Add to cache
            news_cache[language].extend(new_items)

            # Keep only latest 50 items
            news_cache[language] = news_cache[language][-50:]

            logger.info(f"Updated {language} cache: {len(new_items)} new items")
    except Exception as e:
        logger.error(f"Error updating cache for {language}: {e}", exc_info=True)


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = datetime.utcnow()

    response = await call_next(request)

    duration = (datetime.utcnow() - start_time).total_seconds()

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


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={"method": request.method, "path": request.url.path},
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if not config.is_production() else "An error occurred",
        },
    )


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("Starting Multilingual News Radio API...")
    logger.info(f"Environment: {config.environment}")
    logger.info(f"Kafka: {config.kafka.bootstrap_servers}")
    logger.info(f"Redis: {config.redis.host}:{config.redis.port}")

    try:
        initialize_kafka_consumers()

        redis_client = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password,
            ssl=config.redis.ssl,
            decode_responses=True,  # Optional: makes responses strings instead of bytes
        )

        # Initialize health checker
        global health_checker
        health_checker = HealthChecker(
            redis_client=redis_client, kafka_config=config.kafka.connection_config
        )

        # Load initial cache
        for lang in ["en", "hi", "bn"]:
            update_cache(lang)

        logger.info("✓ API ready")
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down API...")

    for consumer in kafka_consumers.values():
        try:
            consumer.close()
        except Exception as e:
            logger.error(f"Error closing consumer: {e}")

    logger.info("✓ API shutdown complete")


@app.get("/")
async def root():
    """API root"""
    return {
        "name": "Multilingual News Radio API",
        "version": "1.0.0",
        "environment": config.environment,
        "languages": ["en", "hi", "bn"],
        "endpoints": {
            "health": "/health",
            "readiness": "/ready",
            "liveness": "/live",
            "playlist": "/playlist/{language}",
            "audio": "/audio/{filename}",
            "refresh": "/refresh/{language}",
            "languages": "/languages",
        },
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check"""
    if health_checker:
        health = health_checker.full_health_check()
        logger.info(f"health : {health}")
        return {
            "status": health["status"],
            "timestamp": health["timestamp"],
            "version": "1.0.0",
            "environment": config.environment,
        }

    return {
        "status": "unknown",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": config.environment,
    }


@app.get("/ready")
async def readiness_check():
    """Kubernetes/Cloud Run readiness probe"""
    if health_checker and health_checker.readiness_check():
        return {"status": "ready"}

    raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/live")
async def liveness_check():
    """Kubernetes/Cloud Run liveness probe"""
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
    if language not in ["en", "hi", "bn"]:
        raise HTTPException(
            status_code=400, detail="Invalid language. Use: en, hi, or bn"
        )

    try:
        # Update cache with latest items
        update_cache(language)

        # Get items from cache
        items = news_cache[language]

        # Filter by category if specified
        if category:
            items = [
                item for item in items if item.category.lower() == category.lower()
            ]

        # Limit items
        items = items[-limit:]

        # Convert to response format
        response_items = []
        for item in items:
            response_items.append(
                NewsItemResponse(
                    id=item.original_id,
                    title=item.original_title,
                    url=item.original_url,
                    category=item.category,
                    source=item.source,
                    language=item.language,
                    summary=item.summary,
                    translated_summary=item.translated_summary,
                    audio_file=Path(item.audio_file).name,
                    audio_duration=item.audio_duration,
                    published_date=item.published_date,
                    processed_at=item.processed_at,
                )
            )

        logger.info(f"Served playlist for {language}: {len(response_items)} items")

        return PlaylistResponse(
            language=language, total_items=len(response_items), items=response_items
        )
    except Exception as e:
        logger.error(f"Error getting playlist for {language}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch playlist")


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """Stream audio file"""
    try:
        # Audio files are in audio_output directory
        audio_dir = Path(config.app.audio_output_dir)
        audio_path = audio_dir / filename

        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")

        # Check if it's a real audio file or mock
        if audio_path.stat().st_size == 0:
            # Mock file - return metadata instead
            metadata_path = audio_path.with_suffix(".json")
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)

                return {
                    "message": "Mock audio file (development mode)",
                    "filename": filename,
                    "metadata": metadata,
                }
            else:
                raise HTTPException(status_code=404, detail="Audio file is empty")

        # Return real audio file
        return FileResponse(audio_path, media_type="audio/mpeg", filename=filename)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving audio {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to serve audio")


@app.get("/refresh/{language}")
async def refresh_playlist(language: str):
    """Manually refresh playlist for a language"""
    if language not in ["en", "hi", "bn"]:
        raise HTTPException(status_code=400, detail="Invalid language")

    try:
        update_cache(language)

        return {
            "message": f"Refreshed {language} playlist",
            "items_count": len(news_cache[language]),
        }
    except Exception as e:
        logger.error(f"Error refreshing {language}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to refresh playlist")


@app.get("/languages")
async def get_languages():
    """Get available languages with item counts"""
    return {
        "languages": [
            {"code": "en", "name": "English", "items": len(news_cache["en"])},
            {"code": "hi", "name": "Hindi", "items": len(news_cache["hi"])},
            {"code": "bn", "name": "Bengali", "items": len(news_cache["bn"])},
        ]
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level=config.app.log_level.lower(),
        access_log=True,
    )
