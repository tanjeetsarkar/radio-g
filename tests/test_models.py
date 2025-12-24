"""
Unit tests for news_item model
Located at: tests/test_models.py
"""

import pytest
from datetime import datetime, timezone
import json

from models.news_item import NewsItem


@pytest.mark.unit
class TestNewsItem:
    """Test NewsItem model"""
    
    def test_create_news_item(self):
        """Test creating a NewsItem"""
        item = NewsItem(
            title="Test Title",
            description="Test Description",
            url="https://example.com/test",
            category="technology",
            source="Test Source",
            published_date=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc)
        )
        
        assert item.title == "Test Title"
        assert item.category == "technology"
        assert item.id is not None  # Auto-generated
    
    def test_news_item_id_generation(self):
        """Test that ID is auto-generated"""
        mocked_published_date = datetime.now(timezone.utc)
        item1 = NewsItem(
            title="Same Title",
            description="Description",
            url="https://example.com/test",
            category="tech",
            source="Source",
            published_date=mocked_published_date,
            fetched_at=datetime.now(timezone.utc)
        )
        
        item2 = NewsItem(
            title="Same Title",
            description="Description",
            url="https://example.com/test",
            category="tech",
            source="Source",
            published_date=mocked_published_date,
            fetched_at=datetime.now(timezone.utc)
        )
        
        # Same URL and time should generate same ID
        assert item1.id == item2.id
    
    def test_news_item_to_dict(self):
        """Test converting NewsItem to dictionary"""
        now = datetime.now(timezone.utc)
        item = NewsItem(
            title="Test",
            description="Desc",
            url="https://example.com/test",
            category="tech",
            source="Source",
            published_date=now,
            fetched_at=now,
            content="Full content",
            author="Author Name"
        )
        
        data = item.to_dict()
        
        assert isinstance(data, dict)
        assert data['title'] == "Test"
        assert data['content'] == "Full content"
        assert data['author'] == "Author Name"
        assert isinstance(data['published_date'], str)  # Serialized
    
    def test_news_item_to_json(self):
        """Test converting NewsItem to JSON"""
        item = NewsItem(
            title="Test",
            description="Desc",
            url="https://example.com/test",
            category="tech",
            source="Source",
            published_date=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc)
        )
        
        json_str = item.to_json()
        
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed['title'] == "Test"
    
    def test_news_item_from_dict(self):
        """Test creating NewsItem from dictionary"""
        now = datetime.now(timezone.utc)
        data = {
            'title': 'Test',
            'description': 'Desc',
            'url': 'https://example.com/test',
            'category': 'tech',
            'source': 'Source',
            'published_date': now.isoformat(),
            'fetched_at': now.isoformat(),
            'content': 'Content',
            'author': 'Author',
            'image_url': 'https://example.com/img.jpg',
            'id': 'test-id-123'
        }
        
        item = NewsItem.from_dict(data)
        
        assert item.title == 'Test'
        assert item.author == 'Author'
        assert isinstance(item.published_date, datetime)
    
    def test_news_item_roundtrip(self):
        """Test serialization roundtrip"""
        original = NewsItem(
            title="Roundtrip Test",
            description="Testing serialization",
            url="https://example.com/roundtrip",
            category="test",
            source="Test",
            published_date=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc),
            content="Full content here"
        )
        
        # to_dict -> from_dict
        data = original.to_dict()
        restored = NewsItem.from_dict(data)
        
        assert restored.title == original.title
        assert restored.url == original.url
        assert restored.content == original.content
        assert restored.id == original.id
    
    def test_news_item_optional_fields(self):
        """Test optional fields default to None"""
        item = NewsItem(
            title="Minimal",
            description="Minimal description",
            url="https://example.com/minimal",
            category="test",
            source="Test",
            published_date=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc)
        )
        
        assert item.content is None
        assert item.author is None
        assert item.image_url is None
    
    def test_news_item_repr(self):
        """Test string representation"""
        item = NewsItem(
            title="A very long title that should be truncated in the repr",
            description="Desc",
            url="https://example.com/test",
            category="tech",
            source="Source",
            published_date=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc)
        )
        
        repr_str = repr(item)
        
        assert "NewsItem" in repr_str
        assert item.source in repr_str
        assert item.id in repr_str