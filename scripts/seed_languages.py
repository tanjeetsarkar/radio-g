import sys
import os
import logging
import time
import signal

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.language_manager import get_language_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Language configurations
SUPPORTED_LANGUAGES = {
    "en": {
        "name": "English",
        "flag": "ENG",
        "voice_id": "JBFqnCBsd6RMkjVDRZzb",  # George
        "model_id": "eleven_turbo_v2_5",  # 50% cheaper, high quality
        "enabled": True
    },
    "hi": {
        "name": "Hindi",
        "flag": "HI",
        "voice_id": "FDQcYNtvPtQjNlTyU3du",  # Sumi
        "model_id": "eleven_turbo_v2_5",  # 50% cheaper, supports Hindi
        "enabled": True
    },
    "bn": {
        "name": "Bengali",
        "flag": "BEN",
        "voice_id": "FDQcYNtvPtQjNlTyU3du",  # Sumi
        "model_id": "eleven_multilingual_v2",  # Bengali support (turbo v2.5 doesn't support Bengali yet)
        "enabled": True
    }
}

# Timeout handler
class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

def test_redis_connection(mgr, max_retries=3, timeout=10):
    """Test Redis connection with timeout and retries."""
    for attempt in range(max_retries):
        try:
            logger.info(f"Testing Redis connection (attempt {attempt + 1}/{max_retries})...")
            
            # Set alarm for timeout
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)
            
            try:
                result = mgr.ping()
                signal.alarm(0)  # Cancel alarm
                
                if result:
                    logger.info("✅ Redis connection successful")
                    return True
                else:
                    logger.warning(f"⚠️  Redis ping returned False")
            except TimeoutError:
                signal.alarm(0)
                logger.warning(f"⏱️  Redis connection timeout after {timeout}s")
            
        except Exception as e:
            signal.alarm(0)
            logger.error(f"❌ Redis connection failed: {e}")
        
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # Exponential backoff
            logger.info(f"Retrying in {wait_time}s...")
            time.sleep(wait_time)
    
    return False

def seed_with_retry(mgr, config, max_retries=3):
    """Seed configuration with retry logic."""
    for attempt in range(max_retries):
        try:
            logger.info(f"Seeding languages (attempt {attempt + 1}/{max_retries})...")
            
            # Set timeout for seeding operation
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(15)  # 15 second timeout for seeding
            
            try:
                mgr.set_config(config)
                signal.alarm(0)  # Cancel alarm
                logger.info("✅ Configuration written to Redis")
                return True
            except TimeoutError:
                signal.alarm(0)
                logger.warning(f"⏱️  Seeding operation timeout")
                
        except Exception as e:
            signal.alarm(0)
            logger.error(f"❌ Error seeding configuration: {e}")
        
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt
            logger.info(f"Retrying in {wait_time}s...")
            time.sleep(wait_time)
    
    return False

def verify_seeded_data(mgr, expected_langs):
    """Verify that data was correctly seeded."""
    try:
        logger.info("Verifying seeded languages...")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)
        
        try:
            config = mgr.get_config()
            signal.alarm(0)
            
            seeded_langs = set(config.keys())
            expected = set(expected_langs)
            
            if seeded_langs == expected:
                logger.info(f"✅ Verified {len(config)} languages in Redis: {', '.join(sorted(seeded_langs))}")
                return True
            else:
                missing = expected - seeded_langs
                extra = seeded_langs - expected
                if missing:
                    logger.warning(f"⚠️  Missing languages: {', '.join(missing)}")
                if extra:
                    logger.warning(f"⚠️  Extra languages: {', '.join(extra)}")
                return False
                
        except TimeoutError:
            signal.alarm(0)
            logger.warning("⏱️  Verification timeout")
            return False
            
    except Exception as e:
        signal.alarm(0)
        logger.error(f"❌ Verification failed: {e}")
        return False

def seed():
    """Main seeding function with comprehensive error handling."""
    logger.info("=" * 60)
    logger.info("Starting language configuration seeding...")
    logger.info("=" * 60)
    
    try:
        # Initialize manager
        logger.info("Initializing language manager...")
        mgr = get_language_manager()
        logger.info(f"Manager initialized (Redis: {mgr.redis.connection_pool.connection_kwargs.get('host')})")
        
        # Test connection
        if not test_redis_connection(mgr):
            logger.error("❌ Cannot establish Redis connection, aborting")
            sys.exit(1)
        
        # Seed configuration
        logger.info(f"Seeding {len(SUPPORTED_LANGUAGES)} languages: {', '.join(SUPPORTED_LANGUAGES.keys())}")
        
        if not seed_with_retry(mgr, SUPPORTED_LANGUAGES):
            logger.error("❌ Failed to seed configuration after retries")
            sys.exit(1)
        
        # Verify
        if not verify_seeded_data(mgr, SUPPORTED_LANGUAGES.keys()):
            logger.warning("⚠️  Verification failed, but seeding may have succeeded")
        
        # Final success
        logger.info("=" * 60)
        logger.info("✅ Language configuration seeded successfully")
        logger.info("=" * 60)
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"❌ Fatal error during seeding: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Cancel any pending alarms
        signal.alarm(0)

if __name__ == "__main__":
    # Set overall script timeout (3 minutes)
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(180)
    
    try:
        seed()
    except TimeoutError:
        logger.error("❌ Script exceeded maximum execution time (3 minutes)")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(1)
    finally:
        signal.alarm(0)