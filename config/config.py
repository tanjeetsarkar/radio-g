import os
from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class KafkaConfig:
    """Kafka configuration"""
    bootstrap_servers: str
    security_protocol: str = "SASL_SSL"
    sasl_mechanism: str = "PLAIN"
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None
    
    @property
    def connection_config(self) -> dict:
        """Get connection configuration for confluent-kafka"""
        config = {
            'bootstrap.servers': self.bootstrap_servers,
        }
        
        if self.sasl_username and self.sasl_password:
            config.update({
                'security.protocol': self.security_protocol,
                'sasl.mechanism': self.sasl_mechanism,
                'sasl.username': self.sasl_username,
                'sasl.password': self.sasl_password,
            })
        
        return config


@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    username: str = "default"  # <--- ADDED
    ssl: bool = False
    ttl_hours: int = 24


@dataclass
class APIConfig:
    """External API configuration"""
    gemini_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    translation_provider: str = "mock"  # mock or gemini
    tts_provider: str = "mock"  # mock or elevenlabs


@dataclass
class AppConfig:
    """Application configuration"""
    environment: str = "production"  # development, staging, production
    log_level: str = "INFO"
    audio_output_dir: str = "audio_output"
    max_workers: int = 4
    fetch_interval_minutes: int = 15
    enable_deduplication: bool = True
    # GCS Storage Configuration
    storage_backend: str = "local"  # "local" or "gcs"
    gcs_bucket_name: Optional[str] = None
    gcs_project_id: Optional[str] = None
    storage_retention_days: int = 1


class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "production")
        self._validate_required_vars()
        
        # Initialize sub-configs
        self.kafka = self._load_kafka_config()
        self.redis = self._load_redis_config()
        self.api = self._load_api_config()
        self.app = self._load_app_config()
        
        logger.info(f"Configuration loaded for environment: {self.environment}")
    
    def _validate_required_vars(self):
        """Validate required environment variables"""
        required = []
        
        if self.environment == "production":
            required = [
                "KAFKA_BOOTSTRAP_SERVERS",
                "REDIS_HOST"
            ]
        
        missing = [var for var in required if not os.getenv(var)]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    def _load_kafka_config(self) -> KafkaConfig:
        """Load Kafka configuration"""
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9093")
        
        # Parse credentials from format "KEY:SECRET" or separate env vars
        kafka_creds = os.getenv("KAFKA_CREDENTIALS", "")
        
        if kafka_creds and ":" in kafka_creds:
            username, password = kafka_creds.split(":", 1)
        else:
            username = os.getenv("KAFKA_USERNAME")
            password = os.getenv("KAFKA_PASSWORD")
        
        return KafkaConfig(
            bootstrap_servers=bootstrap_servers,
            sasl_username=username,
            sasl_password=password
        )
    
    def _load_redis_config(self) -> RedisConfig:
        """Load Redis configuration"""
        # Get password, convert empty string to None
        redis_password = os.getenv("REDIS_PASSWORD", "")
        if not redis_password or redis_password.strip() == "":
            redis_password = None
        
        return RedisConfig(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=redis_password,
            username=os.getenv("REDIS_USERNAME", "default"),  # <--- ADDED
            ssl=os.getenv("REDIS_SSL", "false").lower() == "true",
            ttl_hours=int(os.getenv("REDIS_TTL_HOURS", "24"))
        )
    
    def _load_api_config(self) -> APIConfig:
        """Load external API configuration"""
        return APIConfig(
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
            translation_provider=os.getenv("TRANSLATION_PROVIDER", "mock"),
            tts_provider=os.getenv("TTS_PROVIDER", "mock")
        )
    
    def _load_app_config(self) -> AppConfig:
        """Load application configuration"""
        return AppConfig(
            environment=self.environment,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            audio_output_dir=os.getenv("AUDIO_OUTPUT_DIR", "audio_output"),
            max_workers=int(os.getenv("MAX_WORKERS", "4")),
            fetch_interval_minutes=int(os.getenv("FETCH_INTERVAL_MINUTES", "15")),
            enable_deduplication=os.getenv("ENABLE_DEDUPLICATION", "true").lower() == "true",
            storage_backend=os.getenv("STORAGE_BACKEND", "local"),
            gcs_bucket_name=os.getenv("GCS_BUCKET_NAME"),
            gcs_project_id=os.getenv("GCS_PROJECT_ID"),
            storage_retention_days=int(os.getenv("STORAGE_RETENTION_DAYS", "1"))
        )
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config():
    """Reload configuration (useful for testing)"""
    global _config
    _config = Config()


# Example usage
if __name__ == "__main__":
    config = get_config()
    print(f"Environment: {config.environment}")
    print(f"Kafka: {config.kafka.bootstrap_servers}")
    print(f"Redis: {config.redis.username}@{config.redis.host}:{config.redis.port}")
    print(f"Translation Provider: {config.api.translation_provider}")
    print(f"TTS Provider: {config.api.tts_provider}")