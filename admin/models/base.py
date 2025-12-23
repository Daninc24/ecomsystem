"""
Base model classes for the admin system
"""

from datetime import datetime
from typing import Any, Dict, Optional
from bson import ObjectId


class BaseModel:
    """Base model class with common functionality for all admin models."""
    
    def __init__(self, **kwargs):
        """Initialize base model with common fields."""
        self.id: Optional[ObjectId] = kwargs.get('_id')
        self.created_at: datetime = kwargs.get('created_at', datetime.utcnow())
        self.updated_at: datetime = kwargs.get('updated_at', datetime.utcnow())
        self.created_by: Optional[ObjectId] = kwargs.get('created_by')
        self.updated_by: Optional[ObjectId] = kwargs.get('updated_by')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for MongoDB storage."""
        data = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                # Handle enum conversion
                if hasattr(value, 'value'):  # It's an enum
                    data[key] = value.value
                else:
                    data[key] = value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """Create model instance from dictionary."""
        return cls(**data)
    
    def update_timestamp(self, user_id: Optional[ObjectId] = None) -> None:
        """Update the updated_at timestamp and optionally updated_by."""
        self.updated_at = datetime.utcnow()
        if user_id:
            self.updated_by = user_id