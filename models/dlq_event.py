import json
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from typing import Any, Dict, Optional

@dataclass
class DLQEvent:
    """Event representing a failed pipeline operation"""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    original_id: Optional[str] = None
    source: Optional[str] = None
    stage: str = "unknown"  # 'ingestion', 'translation', 'tts'
    error_message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """Convert to JSON string with safe serialization"""

        def _default_serializer(obj: Any):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if is_dataclass(obj):
                return asdict(obj)
            if isinstance(obj, (set, tuple)):
                return list(obj)
            raise TypeError(f"Type not serializable: {type(obj)}")

        return json.dumps(asdict(self), default=_default_serializer)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DLQEvent':
        return cls(**data)