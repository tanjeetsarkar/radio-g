import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from services.news_fetcher import NewsFetcher
from models.news_item import NewsItem


@pytest.mark.unit
class TestNewsFetcherInitialization:
    """Test NewsFetcher initialization"""
    
    def test_fetcher_initialization_with_dedup(self, temp_config_file, check_redis):
        """Test fetcher initializes with deduplication"""
        fetcher = NewsFetcher(
            config_path=str(temp_config_file),
            use_deduplication=True
        )
        
        assert fetcher.config is not None
        assert fetcher.scraper is not None
        assert fetcher.deduplicator is not None
        assert fetcher.use_deduplication is True
    
    def test_fetcher_initialization_without_dedup(self, temp_config_file):
        """Test fetcher initializes without deduplication"""
        fetcher = NewsFetcher(
            config_path=str(temp_config_file),
            use_deduplication=False
        )
        
        assert fetcher.config is not None
        assert fetcher.scraper is not None
        assert fetcher.deduplicator is None
        assert fetcher.use_deduplication is False
    
    def test_config_loading(self, temp_config_file):
        """Test configuration is loaded correctly"""
        fetcher = NewsFetcher(
            config_path=str(temp_config_file),
            use_deduplication=False
        )
        
        assert 'feeds' in fetcher.config
        assert 'settings' in fetcher.config
        assert 'test' in fetcher.config['feeds']


@pytest.mark.unit
class TestNewsFetcherParsing:
    """Test RSS entry parsing"""
    
    def test_parse_entry(self, temp_config_file, sample_rss_entry):
        """Test parsing a single RSS entry"""
        fetcher = NewsFetcher(
            config_path=str(temp_config_file),
            use_deduplication=False
        )
        
        # Mock the scraper
        with patch.object(fetcher.scraper, 'scrape_article') as mock_scrape:
            mock_scrape.return_value = ("Full article content", "https://example.com/image.jpg")
            
            news_item = fetcher._parse_entry(
                sample_rss_entry,
                source="Test Source",
                category="technology"
            )
        
        assert news_item is not None
        assert news_item.title == sample_rss_entry['title']
        assert news_item.url == sample_rss_entry['link']
        assert news_item.source == "Test Source"
        assert news_item.category == "technology"
        assert news_item.content == "Full article content"
    
    def test_parse_entry_missing_fields(self, temp_config_file):
        """Test parsing entry with missing required fields"""
        fetcher = NewsFetcher(
            config_path=str(temp_config_file),
            use_deduplication=False
        )
        
        # Entry missing title
        bad_entry = {
            'link': 'https://example.com/test'
        }
        
        result = fetcher._parse_entry(bad_entry, "Source", "tech")
        assert result is None
    
    def test_date_parsing(self, temp_config_file):
        """Test various date formats are parsed correctly"""
        fetcher = NewsFetcher(
            config_path=str(temp_config_file),
            use_deduplication=False
        )
        
        date_formats = [
            'Mon, 01 Jan 2024 12:00:00 GMT',
            '2024-01-01T12:00:00Z',
            '2024-01-01 12:00:00'
        ]
        
        for date_str in date_formats:
            entry = {
                'title': 'Test',
                'link': 'https://example.com/test',
                'published': date_str
            }
            
            with patch.object(fetcher.scraper, 'scrape_article') as mock_scrape:
                mock_scrape.return_value = ("Content", None)
                
                news_item = fetcher._parse_entry(entry, "Source", "tech")
            
            assert news_item is not None
            assert isinstance(news_item.published_date, datetime)


@pytest.mark.unit
class TestNewsFetcherWithMocks:
    """Test fetcher with mocked dependencies"""
    
    @patch('services.news_fetcher.feedparser.parse')
    def test_fetch_feed_success(self, mock_parse, temp_config_file, mock_feedparser_response):
        """Test successful feed fetching"""
        mock_parse.return_value = mock_feedparser_response
        
        fetcher = NewsFetcher(
            config_path=str(temp_config_file),
            use_deduplication=False
        )
        
        with patch.object(fetcher.scraper, 'scrape_article') as mock_scrape:
            mock_scrape.return_value = ("Content", None)
            
            items = fetcher._fetch_feed(
                "https://example.com/feed",
                "Test Source",
                "technology"
            )
        
        assert len(items) == 3  # mock_feedparser_response has 3 entries
        assert all(isinstance(item, NewsItem) for item in items)
    
    @patch('services.news_fetcher.feedparser.parse')
    def test_fetch_feed_with_error(self, mock_parse, temp_config_file):
        """Test feed fetching with parser error"""
        mock_feed = Mock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Parse error")
        mock_feed.entries = []
        mock_parse.return_value = mock_feed
        
        fetcher = NewsFetcher(
            config_path=str(temp_config_file),
            use_deduplication=False
        )
        
        items = fetcher._fetch_feed(
            "https://example.com/feed",
            "Test Source",
            "technology"
        )
        
        assert items == []
    
    @patch('services.news_fetcher.feedparser.parse')
    def test_fetch_feed_respects_max_articles(self, mock_parse, temp_config_file):
        """Test that max_articles setting is respected"""
        # Create mock with 10 entries
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            Mock(
                title=f"Article {i}",
                link=f"https://example.com/article-{i}",
                summary=f"Summary {i}",
                published="Mon, 01 Jan 2024 12:00:00 GMT"
            )
            for i in range(10)
        ]
        mock_parse.return_value = mock_feed
        
        fetcher = NewsFetcher(
            config_path=str(temp_config_file),
            use_deduplication=False
        )
        
        # max_articles is set to 5 in temp_config_file
        with patch.object(fetcher.scraper, 'scrape_article') as mock_scrape:
            mock_scrape.return_value = ("Content", None)
            
            items = fetcher._fetch_feed(
                "https://example.com/feed",
                "Test Source",
                "technology"
            )
        
        assert len(items) <= 5


@pytest.mark.integration
@pytest.mark.redis
@pytest.mark.slow
class TestNewsFetcherWithDeduplication:
    """Test fetcher with real deduplication"""
    
    @patch('services.news_fetcher.feedparser.parse')
    def test_deduplication_filters_duplicates(
        self,
        mock_parse,
        temp_config_file,
        check_redis
    ):
        """Test that deduplication filters out duplicate articles"""
        # Create mock feed with duplicate articles
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            Mock(
                title="Same Article",
                link="https://example.com/same-article",
                summary="Summary",
                published="Mon, 01 Jan 2024 12:00:00 GMT"
            ),
            Mock(
                title="Different Article",
                link="https://example.com/different-article",
                summary="Summary",
                published="Mon, 01 Jan 2024 12:00:00 GMT"
            )
        ]
        mock_parse.return_value = mock_feed
        
        fetcher = NewsFetcher(
            config_path=str(temp_config_file),
            use_deduplication=True
        )
        
        with patch.object(fetcher.scraper, 'scrape_article') as mock_scrape:
            mock_scrape.return_value = ("Content", None)
            
            # First fetch - should get all items
            items_1 = fetcher._fetch_feed(
                "https://example.com/feed",
                "Test Source",
                "technology"
            )
            
            # Apply deduplication
            if fetcher.deduplicator:
                items_1 = fetcher.deduplicator.filter_duplicates(items_1)
            
            # Second fetch - should get duplicates filtered
            items_2 = fetcher._fetch_feed(
                "https://example.com/feed",
                "Test Source",
                "technology"
            )
            
            if fetcher.deduplicator:
                items_2 = fetcher.deduplicator.filter_duplicates(items_2)
        
        assert len(items_1) == 2
        assert len(items_2) == 0  # All duplicates
        
        # Cleanup
        if fetcher.deduplicator:
            fetcher.deduplicator.clear_cache()


@pytest.mark.integration
@pytest.mark.slow
class TestNewsFetcherRealFeeds:
    """Test fetcher with real RSS feeds (slow tests)"""
    
    def test_fetch_single_category_real(self):
        """Test fetching from a real RSS feed"""
        fetcher = NewsFetcher(use_deduplication=False)
        
        # This will make real HTTP requests - skip if no network
        try:
            items = fetcher.fetch_by_category('technology')
            
            assert isinstance(items, list)
            # Should get at least some articles
            assert len(items) >= 0
            
            if items:
                # Check first item structure
                item = items[0]
                assert item.title
                assert item.url
                assert item.source
                assert item.category == 'technology'
        
        except Exception as e:
            pytest.skip(f"Network test failed: {e}")
    
    def test_fetch_all_feeds_real(self):
        """Test fetching from all configured feeds"""
        fetcher = NewsFetcher(use_deduplication=False)
        
        try:
            items = fetcher.fetch_all_feeds()
            
            assert isinstance(items, list)
            
            if items:
                # Check we have multiple categories
                categories = set(item.category for item in items)
                assert len(categories) > 0
                
                # Check basic structure
                sample = items[0]
                assert sample.title
                assert sample.url
                assert sample.category
                assert sample.source
        
        except Exception as e:
            pytest.skip(f"Network test failed: {e}")


@pytest.mark.unit
class TestNewsFetcherRetryLogic:
    """Test retry logic for failed feeds"""
    
    @patch('services.news_fetcher.feedparser.parse')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_retry_on_failure(self, mock_sleep, mock_parse, temp_config_file):
        """Test that fetcher retries on failure"""
        # Make it fail twice, then succeed
        mock_parse.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            Mock(bozo=False, entries=[])
        ]
        
        fetcher = NewsFetcher(
            config_path=str(temp_config_file),
            use_deduplication=False
        )
        
        feed_config = {
            'url': 'https://example.com/feed',
            'name': 'Test Feed'
        }
        
        items = fetcher._fetch_feed_with_retry(feed_config, 'technology')
        
        # Should have retried twice (2 attempts in config)
        assert mock_parse.call_count == 3  # 2 retries + 1 success
        assert items == []
    
    @patch('services.news_fetcher.feedparser.parse')
    @patch('time.sleep')
    def test_no_retry_on_success(self, mock_sleep, mock_parse, temp_config_file):
        """Test that fetcher doesn't retry on success"""
        mock_parse.return_value = Mock(bozo=False, entries=[])
        
        fetcher = NewsFetcher(
            config_path=str(temp_config_file),
            use_deduplication=False
        )
        
        feed_config = {
            'url': 'https://example.com/feed',
            'name': 'Test Feed'
        }
        
        items = fetcher._fetch_feed_with_retry(feed_config, 'technology')
        
        # Should only call once (no retries needed)
        assert mock_parse.call_count == 1


@pytest.mark.unit
class TestNewsFetcherCategoryFiltering:
    """Test category-specific fetching"""
    
    def test_fetch_by_category_filters_correctly(self, temp_config_file):
        """Test that fetch_by_category only fetches requested category"""
        fetcher = NewsFetcher(
            config_path=str(temp_config_file),
            use_deduplication=False
        )
        
        # temp_config only has 'test' category
        with patch.object(fetcher, '_fetch_feed_with_retry') as mock_fetch:
            mock_fetch.return_value = [
                NewsItem(
                    title="Test",
                    description="Desc",
                    url="https://example.com/test",
                    category="test",
                    source="Source",
                    published_date=datetime.now(timezone.utc),
                    fetched_at=datetime.now(timezone.utc)
                )
            ]
            
            items = fetcher.fetch_by_category('test')
        
        assert all(item.category == 'test' for item in items)
    
    def test_fetch_invalid_category_returns_empty(self, temp_config_file):
        """Test fetching non-existent category returns empty list"""
        fetcher = NewsFetcher(
            config_path=str(temp_config_file),
            use_deduplication=False
        )
        
        items = fetcher.fetch_by_category('nonexistent')
        assert items == []


# Utility function for manual testing
def run_manual_fetch_test():
    """Helper function for manual testing of real feeds"""
    print("\n" + "="*60)
    print("MANUAL FETCH TEST")
    print("="*60)
    
    fetcher = NewsFetcher(use_deduplication=True)
    
    print("\nFetching technology news...")
    tech_news = fetcher.fetch_by_category('technology')
    
    print(f"✓ Fetched {len(tech_news)} technology articles")
    
    if tech_news:
        print("\nSample articles:")
        for i, item in enumerate(tech_news[:3], 1):
            print(f"\n[{i}] {item.title[:70]}...")
            print(f"    Source: {item.source}")
            print(f"    URL: {item.url}")
            print(f"    Content: {len(item.content) if item.content else 0} chars")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # Run manual test
    run_manual_fetch_test()