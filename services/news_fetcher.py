import feedparser
import yaml
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dateutil import parser as date_parser

from models.news_item import NewsItem
from services.content_scraper import ContentScraper
from services.deduplicator import NewsDeduplicator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsFetcher:
    """Fetches news from RSS feeds with retry logic and rate limiting"""
    
    def __init__(self, config_path: str = "config/sources.yaml", use_deduplication: bool = True):
        self.config = self._load_config(config_path)
        self.scraper = ContentScraper(
            timeout=self.config['settings']['request_timeout_seconds']
        )
        self.retry_attempts = self.config['settings']['retry_attempts']
        self.retry_delay = self.config['settings']['retry_delay_seconds']
        self.rate_limit_delay = self.config['settings']['rate_limit_delay_seconds']
        self.max_articles = self.config['settings']['max_articles_per_feed']
        
        # Initialize deduplicator
        self.use_deduplication = use_deduplication
        self.deduplicator = None
        if use_deduplication:
            try:
                self.deduplicator = NewsDeduplicator()
                logger.info("✓ Deduplication enabled")
            except Exception as e:
                logger.warning(f"Deduplication disabled due to error: {e}")
                self.use_deduplication = False
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def fetch_all_feeds(self) -> List[NewsItem]:
        """Fetch news from all enabled feeds across all categories"""
        all_news = []
        
        for category, feeds in self.config['feeds'].items():
            logger.info(f"Fetching {category} news...")
            
            # Sort feeds by priority
            sorted_feeds = sorted(feeds, key=lambda x: x['priority'])
            
            for feed_config in sorted_feeds:
                if not feed_config['enabled']:
                    continue
                
                news_items = self._fetch_feed_with_retry(feed_config, category)
                all_news.extend(news_items)
                
                # Rate limiting between feeds
                time.sleep(self.rate_limit_delay)
        
        # Apply deduplication
        if self.use_deduplication and self.deduplicator:
            all_news = self.deduplicator.filter_duplicates(all_news)
        
        logger.info(f"Total unique articles fetched: {len(all_news)}")
        return all_news
    
    def _fetch_feed_with_retry(self, feed_config: Dict, category: str) -> List[NewsItem]:
        """Fetch a single feed with retry logic"""
        url = feed_config['url']
        name = feed_config['name']
        
        for attempt in range(self.retry_attempts + 1):
            try:
                logger.info(f"Fetching {name} (attempt {attempt + 1}/{self.retry_attempts + 1})")
                return self._fetch_feed(url, name, category)
                
            except Exception as e:
                logger.error(f"Error fetching {name}: {str(e)}")
                
                if attempt < self.retry_attempts:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to fetch {name} after {self.retry_attempts + 1} attempts")
        
        return []
    
    def _fetch_feed(self, url: str, source: str, category: str) -> List[NewsItem]:
        """Fetch and parse a single RSS feed"""
        news_items = []
        
        # Parse RSS feed
        feed = feedparser.parse(url)
        
        if feed.bozo:  # Feed parsing error
            logger.warning(f"Feed parsing warning for {source}: {feed.bozo_exception}")
        
        entries = feed.entries[:self.max_articles]  # Limit articles per feed
        
        for entry in entries:
            try:
                news_item = self._parse_entry(entry, source, category)
                if news_item:
                    news_items.append(news_item)
            except Exception as e:
                logger.error(f"Error parsing entry from {source}: {str(e)}")
                continue
        
        logger.info(f"Fetched {len(news_items)} articles from {source}")
        return news_items
    
    def _parse_entry(self, entry, source: str, category: str) -> Optional[NewsItem]:
        """Parse a single RSS entry into NewsItem"""
        
        # Extract basic fields
        title = entry.get('title', '').strip()
        description = entry.get('summary', entry.get('description', '')).strip()
        url = entry.get('link', '')
        
        if not title or not url:
            return None
        
        # Parse published date
        published_date = self._parse_date(entry)
        
        # Get author
        author = entry.get('author', None)
        
        # Scrape full content with fallback to description
        content = None
        image_url = None
        
        if self.scraper.is_scrapable_url(url):
            content, image_url = self.scraper.scrape_article(url, fallback_description=description)
        else:
            logger.info(f"Skipping scraping for: {url}")
            content = description
        
        # Try to get image from RSS if not found during scraping
        if not image_url:
            # Check for media content
            if hasattr(entry, 'media_content') and entry.media_content:
                image_url = entry.media_content[0].get('url')
            elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                image_url = entry.media_thumbnail[0].get('url')
            elif hasattr(entry, 'enclosures') and entry.enclosures:
                for enclosure in entry.enclosures:
                    if enclosure.get('type', '').startswith('image/'):
                        image_url = enclosure.get('href')
                        break
        
        return NewsItem(
            title=title,
            description=description,
            url=url,
            category=category,
            source=source,
            published_date=published_date,
            fetched_at=datetime.now(timezone.utc),
            content=content,
            author=author,
            image_url=image_url
        )
    
    def _parse_date(self, entry) -> datetime:
        """Parse published date from RSS entry"""
        date_fields = ['published', 'pubDate', 'updated', 'created']
        
        for field in date_fields:
            date_str = entry.get(field)
            if date_str:
                try:
                    # Try parsing with dateutil
                    dt = date_parser.parse(date_str)
                    # Ensure timezone awareness
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except:
                    continue
        
        # Fallback to current time
        return datetime.now(timezone.utc)
    
    def fetch_by_category(self, category: str) -> List[NewsItem]:
        """Fetch news from a specific category only"""
        if category not in self.config['feeds']:
            logger.error(f"Category '{category}' not found in config")
            return []
        
        news_items = []
        feeds = sorted(self.config['feeds'][category], key=lambda x: x['priority'])
        
        for feed_config in feeds:
            if not feed_config['enabled']:
                continue
            
            items = self._fetch_feed_with_retry(feed_config, category)
            news_items.extend(items)
            time.sleep(self.rate_limit_delay)
        
        return news_items


# Example usage
if __name__ == "__main__":
    fetcher = NewsFetcher()
    
    # Fetch all news
    all_news = fetcher.fetch_all_feeds()
    
    # Print sample
    for item in all_news[:3]:
        print(f"\n{item.source} - {item.category}")
        print(f"Title: {item.title}")
        print(f"URL: {item.url}")
        print(f"Content length: {len(item.content) if item.content else 0} chars")
        print(f"Published: {item.published_date}")