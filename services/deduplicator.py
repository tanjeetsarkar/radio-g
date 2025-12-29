import redis
import logging
from typing import List, Optional
from models.news_item import NewsItem
import hashlib
import json

logger = logging.getLogger(__name__)


class NewsDeduplicator:
    """
    Deduplicates news articles using Redis as cache
    Stores article hashes with 24-hour TTL
    """
    
    def __init__(
        self, 
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        redis_ssl: bool = False,
        ttl_hours: int = 24
    ):
        """
        Initialize Redis connection for deduplication
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            redis_password: Redis password (optional)
            redis_ssl: Use SSL connection (optional)
            ttl_hours: Time-to-live for cached articles in hours
        """
        # Only include password and SSL if provided
        redis_params = {
            'host': redis_host,
            'port': redis_port,
            'db': redis_db,
            'decode_responses': True,
            'socket_connect_timeout': 5,
            'socket_timeout': 5
        }
        
        # Only add password if it's not None and not empty
        if redis_password:
            redis_params['password'] = redis_password
        
        # Only add SSL if True
        if redis_ssl:
            redis_params['ssl'] = redis_ssl
        
        self.redis_client = redis.Redis(**redis_params)
        self.ttl_seconds = ttl_hours * 3600
        self.key_prefix = "news:seen:"
        
        # Test connection
        try:
            self.redis_client.ping()
            logger.info(f"✓ Connected to Redis at {redis_host}:{redis_port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _generate_hash(self, news_item: NewsItem) -> str:
        """
        Generate unique hash for a news item
        Based on URL and title to catch duplicates across sources
        """
        # Combine URL and normalized title
        unique_string = f"{news_item.url}:{news_item.title.lower().strip()}"
        return hashlib.sha256(unique_string.encode()).hexdigest()
    
    def is_duplicate(self, news_item: NewsItem) -> bool:
        """
        Check if news item has been seen before
        
        Returns:
            True if duplicate, False if new
        """
        article_hash = self._generate_hash(news_item)
        key = f"{self.key_prefix}{article_hash}"
        
        try:
            exists = self.redis_client.exists(key)
            
            if exists:
                logger.debug(f"Duplicate found: {news_item.title[:50]}...")
                return True
            
            return False
            
        except redis.RedisError as e:
            logger.error(f"Redis error checking duplicate: {e}")
            # If Redis fails, assume not duplicate to avoid losing articles
            return False
    
    def mark_as_seen(self, news_item: NewsItem) -> bool:
        """
        Mark news item as seen in Redis cache
        
        Returns:
            True if successfully marked, False otherwise
        """
        article_hash = self._generate_hash(news_item)
        key = f"{self.key_prefix}{article_hash}"
        
        try:
            # Store with metadata for debugging
            metadata = {
                'id': news_item.id,
                'title': news_item.title,
                'url': news_item.url,
                'source': news_item.source,
                'category': news_item.category,
                'timestamp': news_item.fetched_at.isoformat()
            }
            
            # Set with TTL
            self.redis_client.setex(
                key,
                self.ttl_seconds,
                json.dumps(metadata)
            )
            
            logger.debug(f"Marked as seen: {news_item.title[:50]}...")
            return True
            
        except redis.RedisError as e:
            logger.error(f"Redis error marking as seen: {e}")
            return False
    
    def filter_duplicates(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """
        Filter out duplicate news items from a list
        
        Args:
            news_items: List of news items to filter
            
        Returns:
            List of unique news items (not seen before)
        """
        unique_items = []
        duplicate_count = 0
        
        for item in news_items:
            if not self.is_duplicate(item):
                unique_items.append(item)
                self.mark_as_seen(item)
            else:
                duplicate_count += 1
        
        logger.info(
            f"Filtered {len(news_items)} articles: "
            f"{len(unique_items)} unique, {duplicate_count} duplicates"
        )
        
        return unique_items
    
    def get_seen_count(self) -> int:
        """Get total count of articles currently in cache"""
        try:
            keys = self.redis_client.keys(f"{self.key_prefix}*")
            return len(keys)
        except redis.RedisError as e:
            logger.error(f"Redis error getting count: {e}")
            return 0
    
    def clear_cache(self) -> bool:
        """Clear all cached articles (useful for testing)"""
        try:
            keys = self.redis_client.keys(f"{self.key_prefix}*")
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cached articles")
            return True
        except redis.RedisError as e:
            logger.error(f"Redis error clearing cache: {e}")
            return False
    
    def get_article_info(self, news_item: NewsItem) -> Optional[dict]:
        """Get cached metadata for an article (for debugging)"""
        article_hash = self._generate_hash(news_item)
        key = f"{self.key_prefix}{article_hash}"
        
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except redis.RedisError as e:
            logger.error(f"Redis error getting article info: {e}")
            return None
    
    def check_health(self) -> dict:
        """Check Redis connection health and get stats"""
        try:
            info = self.redis_client.info()
            cached_count = self.get_seen_count()
            
            return {
                'status': 'healthy',
                'connected': True,
                'cached_articles': cached_count,
                'memory_used': info.get('used_memory_human', 'unknown'),
                'uptime_seconds': info.get('uptime_in_seconds', 0)
            }
        except redis.RedisError as e:
            return {
                'status': 'unhealthy',
                'connected': False,
                'error': str(e)
            }


# Example usage
if __name__ == "__main__":
    from datetime import datetime, timezone
    
    # Initialize deduplicator
    dedup = NewsDeduplicator(redis_host="localhost", redis_port=6379)
    
    # Health check
    health = dedup.check_health()
    print(f"Redis Health: {health}")
    
    # Create sample news items
    item1 = NewsItem(
        title="Breaking: Major Tech Announcement",
        description="Tech company announces new product",
        url="https://example.com/article1",
        category="technology",
        source="TechCrunch",
        published_date=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        content="Full article content here..."
    )
    
    item2 = NewsItem(
        title="Breaking: Major Tech Announcement",  # Same title
        description="Different description",
        url="https://example.com/article1",  # Same URL
        category="technology",
        source="The Verge",  # Different source
        published_date=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        content="Different content..."
    )
    
    # Test deduplication
    print(f"\nChecking item1: Duplicate? {dedup.is_duplicate(item1)}")
    dedup.mark_as_seen(item1)
    print("Marked item1 as seen")
    
    print(f"\nChecking item2 (same URL): Duplicate? {dedup.is_duplicate(item2)}")
    
    print(f"\nTotal cached articles: {dedup.get_seen_count()}")