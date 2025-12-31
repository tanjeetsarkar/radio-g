from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import hashlib
import json


@dataclass
class NewsItem:
    """Data model for a news article"""
    
    title: str
    description: str
    url: str
    category: str
    source: str
    published_date: datetime
    fetched_at: datetime
    content: Optional[str] = None
    author: Optional[str] = None
    image_url: Optional[str] = None
    id: Optional[str] = None
    
    def __post_init__(self):
        """Generate unique ID after initialization"""
        if not self.id:
            self.id = self.generate_id()
    
    def generate_id(self) -> str:
        """Generate unique ID based on URL and published date"""
        unique_string = f"{self.url}:{self.published_date.isoformat()}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def to_dict(self) -> dict:
        """Convert to dictionary with serialized datetime"""
        data = asdict(self)
        data['published_date'] = self.published_date.isoformat()
        data['fetched_at'] = self.fetched_at.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NewsItem':
        """Create NewsItem from dictionary"""
        data['published_date'] = datetime.fromisoformat(data['published_date'])
        data['fetched_at'] = datetime.fromisoformat(data['fetched_at'])
        return cls(**data)
    
    def __repr__(self) -> str:
        return f"NewsItem(id={self.id}, title={self.title[:50]}..., source={self.source})"


@dataclass
class ProcessedNewsItem:
    original_id: Optional[str]
    original_title: str
    original_url: str
    category: str
    source: str
    published_date: str
    language: str
    summary: str
    translated_summary: str
    audio_file: str
    audio_duration: float
    processed_at: str
    processing_provider: str
    tts_provider: str
    translated_title: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_dict(cls, data: dict) -> "ProcessedNewsItem":
        """Create from dictionary"""
        return cls(**data)