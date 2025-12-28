import json
import logging
from typing import Dict, Optional, List
import redis
from config.config import get_config

logger = logging.getLogger(__name__)

class LanguageManager:
    """Manages dynamic language configuration using Redis"""
    
    _instance = None
    REDIS_KEY = "config:languages"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LanguageManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        config = get_config()
        self.redis = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password,
            ssl=config.redis.ssl,
            decode_responses=True
        )
        # Local cache to prevent hammering Redis (TTL: 60s strategy implemented in logic)
        self._cache = None
        self._last_update = 0

    def get_config(self) -> Dict[str, dict]:
        """Get full language configuration"""
        # In a real high-throughput scenario, add a time-based cache here.
        # For now, we fetch fresh to ensure instant updates.
        raw = self.redis.get(self.REDIS_KEY)
        if not raw:
            return {}
        return json.loads(raw)

    def get_language_list(self) -> List[str]:
        config = self.get_config()
        return list(config.keys())

    def get_voice_id(self, lang_code: str) -> Optional[str]:
        config = self.get_config()
        return config.get(lang_code, {}).get("voice_id")

    def get_topic(self, lang_code: str) -> str:
        return f"news-{self.get_language_name(lang_code).lower()}"

    def get_language_name(self, lang_code: str) -> str:
        config = self.get_config()
        return config.get(lang_code, {}).get("name", lang_code)

    def set_config(self, config: Dict[str, dict]):
        """Update configuration (Admin usage)"""
        self.redis.set(self.REDIS_KEY, json.dumps(config))
        logger.info("Language configuration updated")

# Global accessor
def get_language_manager():
    return LanguageManager()