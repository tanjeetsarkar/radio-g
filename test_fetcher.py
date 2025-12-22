"""
Test script for news fetcher with deduplication
Run: python test_fetcher.py
"""

import sys
import logging
from services.news_fetcher import NewsFetcher
from services.deduplicator import NewsDeduplicator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_redis_connection():
    """Test Redis connection"""
    try:
        dedup = NewsDeduplicator()
        health = dedup.check_health()
        logger.info(f"Redis Health Check: {health}")
        return health['connected']
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return False


def test_news_fetching():
    """Test news fetching from all sources"""
    try:
        logger.info("="*60)
        logger.info("Starting News Fetcher Test")
        logger.info("="*60)
        
        # Initialize fetcher with deduplication
        fetcher = NewsFetcher(use_deduplication=True)
        
        # Fetch all news
        logger.info("\n🔍 Fetching news from all sources...")
        news_items = fetcher.fetch_all_feeds()
        
        # Display results
        logger.info("\n" + "="*60)
        logger.info(f"✓ Successfully fetched {len(news_items)} unique articles")
        logger.info("="*60)
        
        # Group by category
        by_category = {}
        for item in news_items:
            if item.category not in by_category:
                by_category[item.category] = []
            by_category[item.category].append(item)
        
        # Display breakdown
        logger.info("\n📊 Articles by Category:")
        for category, items in sorted(by_category.items()):
            logger.info(f"  {category.upper()}: {len(items)} articles")
        
        # Show sample articles
        logger.info("\n📰 Sample Articles (first 3):")
        for i, item in enumerate(news_items[:3], 1):
            logger.info(f"\n  [{i}] {item.source} - {item.category.upper()}")
            logger.info(f"      Title: {item.title}")
            logger.info(f"      URL: {item.url}")
            logger.info(f"      Content length: {len(item.content)} chars")
            logger.info(f"      Published: {item.published_date}")
            logger.info(f"      Image: {'Yes' if item.image_url else 'No'}")
        
        # Test deduplication
        if fetcher.deduplicator:
            cached_count = fetcher.deduplicator.get_seen_count()
            logger.info(f"\n💾 Cached articles in Redis: {cached_count}")
        
        logger.info("\n" + "="*60)
        logger.info("✓ Test completed successfully!")
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False


def test_single_category():
    """Test fetching from a single category"""
    try:
        logger.info("\n🔍 Testing single category fetch (technology)...")
        fetcher = NewsFetcher(use_deduplication=True)
        
        tech_news = fetcher.fetch_by_category('technology')
        logger.info(f"✓ Fetched {len(tech_news)} technology articles")
        
        if tech_news:
            sample = tech_news[0]
            logger.info(f"\nSample: {sample.title[:70]}...")
            logger.info(f"Source: {sample.source}")
            logger.info(f"Content: {sample.content[:200]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"Single category test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("NEWS FETCHER TEST SUITE")
    print("="*60)
    
    # Test 1: Redis connection
    print("\n[Test 1] Redis Connection...")
    redis_ok = test_redis_connection()
    if not redis_ok:
        print("⚠️  WARNING: Redis not available. Deduplication will be disabled.")
        print("   To start Redis: docker-compose up -d redis")
        print("   Continuing without deduplication...\n")
    
    # Test 2: Fetch all news
    print("\n[Test 2] Fetch All News Sources...")
    if not test_news_fetching():
        sys.exit(1)
    
    # Test 3: Single category
    print("\n[Test 3] Fetch Single Category...")
    if not test_single_category():
        sys.exit(1)
    
    print("\n" + "="*60)
    print("✓ ALL TESTS PASSED!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()