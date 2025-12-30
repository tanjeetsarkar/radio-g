import sys
import os
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import redis
from confluent_kafka.admin import AdminClient
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tempfile
import yaml

from models.news_item import NewsItem
from services.deduplicator import NewsDeduplicator
from services.kafka_producer import NewsKafkaProducer
from services.kafka_consumer import NewsKafkaConsumer


# ============================================================================
# Test Configuration
# ============================================================================

@pytest.fixture(scope="session")
def test_config():
    """Test configuration"""
    return {
        'redis_host': 'localhost',
        'redis_port': 6379,
        'kafka_servers': 'localhost:9093',
        'test_db': 15,  # Use separate Redis DB for testing
    }


# ============================================================================
# Mocks & Fixtures for Dynamic Services
# ============================================================================

@pytest.fixture
def mock_language_manager():
    """Mock the LanguageManager to return a standard config"""
    with patch('services.language_manager.get_language_manager') as mock_get:
        manager = Mock()
        # Default test config matching the previous hardcoded values
        manager.get_config.return_value = {
            'en': {'name': 'English', 'flag': '🇬🇧', 'voice_id': 'voice_en', 'model_id': 'eleven_multilingual_v2', 'enabled': True},
            'hi': {'name': 'Hindi', 'flag': '🇮🇳', 'voice_id': 'voice_hi', 'model_id': 'eleven_multilingual_v2', 'enabled': True},
            'bn': {'name': 'Bengali', 'flag': '🇧🇩', 'voice_id': 'voice_bn', 'model_id': 'eleven_multilingual_v2', 'enabled': True}
        }
        manager.get_model_id.side_effect = lambda lang: manager.get_config.return_value.get(lang, {}).get('model_id', 'eleven_multilingual_v2')
        mock_get.return_value = manager
        yield manager


# ============================================================================
# Service Availability Checks
# ============================================================================

@pytest.fixture(scope="session")
def check_redis(test_config):
    """Check if Redis is available"""
    try:
        client = redis.Redis(
            host=test_config['redis_host'],
            port=test_config['redis_port'],
            db=test_config['test_db'],
            socket_connect_timeout=2
        )
        client.ping()
        return True
    except redis.ConnectionError:
        pytest.skip("Redis not available")


@pytest.fixture(scope="session")
def check_kafka(test_config):
    """Check if Kafka is available"""
    try:
        admin = AdminClient({
            'bootstrap.servers': test_config['kafka_servers'],
            'socket.timeout.ms': 2000
        })
        admin.list_topics(timeout=2)
        return True
    except Exception:
        pytest.skip("Kafka not available")


# ============================================================================
# Temporary Directories
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def temp_config_file(temp_dir):
    """Create temporary config file"""
    config = {
        'feeds': {
            'test': [
                {
                    'url': 'https://test.example.com/feed',
                    'name': 'Test Feed',
                    'priority': 1,
                    'enabled': True
                }
            ]
        },
        'settings': {
            'fetch_interval_minutes': 15,
            'retry_attempts': 2,
            'retry_delay_seconds': 1,
            'rate_limit_delay_seconds': 0.5,
            'request_timeout_seconds': 10,
            'max_articles_per_feed': 5
        }
    }
    
    config_path = temp_dir / 'test_sources.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    return config_path


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_news_item():
    """Create a sample NewsItem for testing"""
    return NewsItem(
        title="Test Article: Breaking News",
        description="This is a test article description",
        url="https://example.com/test-article",
        category="technology",
        source="Test Source",
        published_date=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        content="Full content of the test article goes here...",
        author="Test Author",
        image_url="https://example.com/image.jpg"
    )


@pytest.fixture
def sample_news_items():
    """Create multiple sample NewsItems"""
    base_time = datetime.now(timezone.utc)
    
    items = []
    for i in range(5):
        item = NewsItem(
            title=f"Test Article {i+1}: News Headline",
            description=f"Description for article {i+1}",
            url=f"https://example.com/article-{i+1}",
            category="technology" if i % 2 == 0 else "business",
            source=f"Source {i % 2 + 1}",
            published_date=base_time,
            fetched_at=base_time,
            content=f"Full content for article {i+1}...",
        )
        items.append(item)
    
    return items


@pytest.fixture
def sample_rss_entry():
    """Create a sample RSS feed entry"""
    return {
        'title': 'Sample RSS Article',
        'summary': 'This is the article summary from RSS',
        'link': 'https://example.com/rss-article',
        'published': 'Mon, 01 Jan 2024 12:00:00 GMT',
        'author': 'RSS Author'
    }


# ============================================================================
# Service Fixtures
# ============================================================================

@pytest.fixture
def redis_deduplicator(test_config, check_redis):
    """Create a deduplicator with test Redis DB"""
    dedup = NewsDeduplicator(
        redis_host=test_config['redis_host'],
        redis_port=test_config['redis_port'],
        redis_db=test_config['test_db']
    )
    
    yield dedup
    
    # Cleanup: clear test database
    dedup.clear_cache()


@pytest.fixture
def kafka_producer(test_config, check_kafka):
    """Create a Kafka producer for testing"""
    producer = NewsKafkaProducer(
        bootstrap_servers=test_config['kafka_servers']
    )
    
    yield producer
    
    # Cleanup
    producer.close()


@pytest.fixture
def kafka_consumer(test_config, check_kafka):
    """Create a Kafka consumer for testing"""
    consumer = NewsKafkaConsumer(
        bootstrap_servers=test_config['kafka_servers'],
        group_id='test-group',
        auto_offset_reset='earliest'
    )
    
    yield consumer
    
    # Cleanup
    consumer.close()


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_feedparser_response():
    """Mock feedparser response"""
    class MockEntry:
        def __init__(self, i):
            self.title = f"Article {i}"
            self.summary = f"Summary for article {i}"
            self.link = f"https://example.com/article-{i}"
            self.published = "Mon, 01 Jan 2024 12:00:00 GMT"
            self.author = f"Author {i}"
    
    class MockFeed:
        def __init__(self):
            self.bozo = False
            self.entries = [MockEntry(i) for i in range(3)]
    
    return MockFeed()


@pytest.fixture
def mock_requests_response():
    """Mock requests response"""
    class MockResponse:
        def __init__(self, content="<html><body>Test content</body></html>", status_code=200):
            self.content = content.encode() if isinstance(content, str) else content
            self.status_code = status_code
            self.text = content if isinstance(content, str) else content.decode()
        
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")
    
    return MockResponse


# ============================================================================
# Markers for Test Organization
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (require Docker services)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests"
    )
    config.addinivalue_line(
        "markers", "kafka: Tests requiring Kafka"
    )
    config.addinivalue_line(
        "markers", "redis: Tests requiring Redis"
    )


# ============================================================================
# Cleanup Hooks
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_artifacts():
    """Cleanup test artifacts after all tests"""
    yield
    
    # Clean up test files
    test_dirs = ['test_audio_output', 'test_logs']
    for test_dir in test_dirs:
        if Path(test_dir).exists():
            shutil.rmtree(test_dir, ignore_errors=True)


# ============================================================================
# Test Output Configuration
# ============================================================================

@pytest.fixture(autouse=True)
def setup_test_logging(caplog):
    """Setup logging for tests"""
    caplog.set_level('INFO')