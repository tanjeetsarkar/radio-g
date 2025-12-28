import feedparser
import yaml
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any
from dateutil import parser as date_parser

from models.news_item import NewsItem
from models.dlq_event import DLQEvent
from services.content_scraper import ContentScraper
from services.deduplicator import NewsDeduplicator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsFetcher:
    """Fetches news from RSS feeds with retry logic and rate limiting"""

    def __init__(
        self, config_path: str = "config/sources.yaml", use_deduplication: bool = True
    ):
        self.config = self._load_config(config_path)
        self.scraper = ContentScraper(
            timeout=self.config["settings"]["request_timeout_seconds"]
        )
        self.retry_attempts = self.config["settings"]["retry_attempts"]
        self.retry_delay = self.config["settings"]["retry_delay_seconds"]
        self.rate_limit_delay = self.config["settings"]["rate_limit_delay_seconds"]
        self.max_articles = self.config["settings"]["max_articles_per_feed"]

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
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def fetch_all_feeds(self) -> Tuple[List[NewsItem], List[DLQEvent]]:
        """
        Fetch news from all enabled feeds across all categories.
        Returns: Tuple of (Successful Items, Failed Events)
        """
        all_news = []
        all_failures = []

        for category, feeds in self.config["feeds"].items():
            logger.info(f"Fetching {category} news...")

            # Sort feeds by priority
            sorted_feeds = sorted(feeds, key=lambda x: x["priority"])

            for feed_config in sorted_feeds:
                if not feed_config["enabled"]:
                    continue

                news_items, failures = self._fetch_feed_with_retry(
                    feed_config, category, include_failures=True
                )
                all_news.extend(news_items)
                all_failures.extend(failures)

                # Rate limiting between feeds
                time.sleep(self.rate_limit_delay)

        # Apply deduplication
        if self.use_deduplication and self.deduplicator:
            all_news = self.deduplicator.filter_duplicates(all_news)

        logger.info(f"Total unique articles fetched: {len(all_news)}")
        logger.info(f"Total failures captured: {len(all_failures)}")
        return all_news, all_failures

    def _fetch_feed_with_retry(
        self, feed_config: Dict, category: str, include_failures: bool = False
    ) -> Tuple[List[NewsItem], List[DLQEvent]]:
        """Fetch a single feed with retry logic"""
        url = feed_config["url"]
        name = feed_config["name"]

        for attempt in range(self.retry_attempts + 1):
            try:
                logger.info(
                    f"Fetching {name} (attempt {attempt + 1}/{self.retry_attempts + 1})"
                )
                news_items, failures = self._fetch_feed(url, name, category)
                return (news_items, failures) if include_failures else (news_items, [])

            except Exception as e:
                logger.error(f"Error fetching {name}: {str(e)}")

                if attempt < self.retry_attempts:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    # Capture feed-level failure
                    logger.error(
                        f"Failed to fetch {name} after {self.retry_attempts + 1} attempts"
                    )
                    failure = DLQEvent(
                        source=name,
                        stage="ingestion_feed_fetch",
                        error_message=str(e),
                        payload={"url": url, "category": category},
                    )
                    return ([], [failure]) if include_failures else ([], [])

        return ([], [])

    def _fetch_feed(
        self, url: str, source: str, category: str
    ) -> Tuple[List[NewsItem], List[DLQEvent]]:
        """Fetch and parse a single RSS feed"""
        news_items = []
        failures = []

        # Parse RSS feed
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            raise e  # Let retry logic handle connection errors

        if feed.bozo:  # Feed parsing error
            logger.warning(f"Feed parsing warning for {source}: {feed.bozo_exception}")
            # We don't necessarily fail here as feedparser often salvages content

        entries = feed.entries[: self.max_articles]  # Limit articles per feed

        for entry in entries:
            try:
                news_item, scrape_failures = self._parse_entry(entry, source, category)
                failures.extend(scrape_failures)
                if news_item:
                    news_items.append(news_item)
            except Exception as e:
                logger.error(f"Error parsing entry from {source}: {str(e)}")

                # Try to serialize entry safely for DLQ
                entry_data = {}
                try:
                    entry_data = {
                        k: str(v)
                        for k, v in entry.items()
                        if k in ["title", "link", "summary"]
                    }
                except Exception:
                    entry_data = {"raw": "Could not serialize entry"}

                failures.append(
                    DLQEvent(
                        source=source,
                        stage="ingestion_entry_parse",
                        error_message=str(e),
                        payload=entry_data,
                    )
                )
                continue

        logger.info(f"Fetched {len(news_items)} articles from {source}")
        return news_items, failures

    def _parse_entry(
        self, entry, source: str, category: str
    ) -> Tuple[Optional[NewsItem], List[DLQEvent]]:
        """Parse a single RSS entry into NewsItem and collect scrape fallbacks"""

        dlq_events: List[DLQEvent] = []

        def _get(e: Any, key: str, default=None):
            """Safely extract values from dicts, feedparser objects, or mocks."""
            try:
                if isinstance(e, dict):
                    return e.get(key, default)

                # For objects (including Mock), prefer real attributes already set
                attrs = getattr(e, "__dict__", {})
                if key in attrs:
                    return attrs.get(key, default)

                if hasattr(e, key):
                    return getattr(e, key, default)
            except Exception:
                pass
            return default

        # Extract basic fields
        title = (_get(entry, "title") or "").strip()
        description = (
            _get(entry, "summary") or _get(entry, "description") or ""
        ).strip()
        url = _get(entry, "link") or ""

        if not title or not url:
            return None, dlq_events

        # Parse published date
        published_date = self._parse_date(entry)

        # Get author
        author = _get(entry, "author", None)

        # Scrape full content with fallback to description
        content = None
        image_url = None
        scrape_meta = {"status": "unknown"}

        if self.scraper.is_scrapable_url(url):
            content, image_url, scrape_meta = self.scraper.scrape_article(
                url, fallback_description=description
            )
        else:
            logger.info(f"Skipping scraping for: {url}")
            content = description
            scrape_meta = {
                "status": "fallback_non_scrapable",
                "reason": "non_scrapable_url",
            }

        # Try to get image from RSS if not found during scraping
        if not image_url:
            image_url = self._extract_image_from_entry(entry)

        news_item = NewsItem(
            title=title,
            description=description,
            url=url,
            category=category,
            source=source,
            published_date=published_date,
            fetched_at=datetime.now(timezone.utc),
            content=content,
            author=author,
            image_url=image_url,
        )

        # Record scrape fallbacks into DLQ
        if scrape_meta.get("status", "").startswith("fallback"):
            dlq_events.append(
                DLQEvent(
                    original_id=news_item.id,
                    source=source,
                    stage="ingestion_scrape_fallback",
                    error_message=scrape_meta.get("reason", scrape_meta["status"]),
                    payload={
                        "url": url,
                        "category": category,
                        "scrape_status": scrape_meta,
                        "news_item": news_item.to_dict(),
                    },
                )
            )

        return news_item, dlq_events

    def _extract_image_from_entry(self, entry) -> Optional[str]:
        """Best-effort extraction of an image URL from common RSS fields."""

        def _as_sequence(value: Any):
            return value if isinstance(value, (list, tuple)) else None

        # Prefer explicit attributes/dict fields without triggering Mock auto-creation
        if isinstance(entry, dict):
            media_content = entry.get("media_content")
            media_thumbnail = entry.get("media_thumbnail")
            enclosures = entry.get("enclosures")
        else:
            attrs = getattr(entry, "__dict__", {})
            media_content = attrs.get("media_content")
            media_thumbnail = attrs.get("media_thumbnail")
            enclosures = attrs.get("enclosures")

        media_content = _as_sequence(media_content)
        media_thumbnail = _as_sequence(media_thumbnail)
        enclosures = _as_sequence(enclosures)

        if media_content:
            first = media_content[0]
            if isinstance(first, dict):
                return first.get("url") or first.get("href")

        if media_thumbnail:
            first = media_thumbnail[0]
            if isinstance(first, dict):
                return first.get("url") or first.get("href")

        if enclosures:
            for enclosure in enclosures:
                if isinstance(enclosure, dict) and enclosure.get("type", "").startswith(
                    "image/"
                ):
                    return enclosure.get("href") or enclosure.get("url")

        return None

    def _parse_date(self, entry) -> datetime:
        """Parse published date from RSS entry"""
        date_fields = ["published", "pubDate", "updated", "created"]
        for field in date_fields:
            date_str = None
            try:
                if hasattr(entry, "get"):
                    date_str = entry.get(field)
                else:
                    date_str = getattr(entry, field, None)
            except Exception:
                date_str = getattr(entry, field, None)
            if date_str:
                try:
                    dt = date_parser.parse(date_str)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except Exception:
                    continue
        return datetime.now(timezone.utc)
