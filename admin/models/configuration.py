"""
Configuration management models
"""

from datetime import datetime
from typing import Any, Dict, Optional, List
from bson import ObjectId
from .base import BaseModel


class AdminSetting(BaseModel):
    """Model for admin configuration settings."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.key: str = kwargs.get('key', '')
        self.value: Any = kwargs.get('value')
        self.category: str = kwargs.get('category', 'general')
        self.description: str = kwargs.get('description', '')
        self.validation_rules: Dict[str, Any] = kwargs.get('validation_rules', {})
        self.is_sensitive: bool = kwargs.get('is_sensitive', False)
        self.requires_restart: bool = kwargs.get('requires_restart', False)
    
    def validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate a value against the setting's validation rules."""
        rules = self.validation_rules
        
        # Type validation
        if 'type' in rules:
            expected_type = rules['type']
            if expected_type == 'string' and not isinstance(value, str):
                return False, f"Expected string, got {type(value).__name__}"
            elif expected_type == 'number' and not isinstance(value, (int, float)):
                return False, f"Expected number, got {type(value).__name__}"
            elif expected_type == 'boolean' and not isinstance(value, bool):
                return False, f"Expected boolean, got {type(value).__name__}"
        
        # Range validation for numbers
        if isinstance(value, (int, float)):
            if 'min' in rules and value < rules['min']:
                return False, f"Value {value} is below minimum {rules['min']}"
            if 'max' in rules and value > rules['max']:
                return False, f"Value {value} is above maximum {rules['max']}"
        
        # Length validation for strings
        if isinstance(value, str):
            if 'min_length' in rules and len(value) < rules['min_length']:
                return False, f"String length {len(value)} is below minimum {rules['min_length']}"
            if 'max_length' in rules and len(value) > rules['max_length']:
                return False, f"String length {len(value)} is above maximum {rules['max_length']}"
        
        # Allowed values validation
        if 'allowed_values' in rules and value not in rules['allowed_values']:
            return False, f"Value {value} not in allowed values: {rules['allowed_values']}"
        
        return True, None


class ConfigurationCache(BaseModel):
    """Model for caching frequently accessed configuration settings."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.key: str = kwargs.get('key', '')
        self.value: Any = kwargs.get('value')
        self.expires_at: datetime = kwargs.get('expires_at', datetime.utcnow())
        self.hit_count: int = kwargs.get('hit_count', 0)
        self.last_accessed: datetime = kwargs.get('last_accessed', datetime.utcnow())
    
    def is_expired(self) -> bool:
        """Check if the cached value has expired."""
        expires_at = self.expires_at
        if isinstance(expires_at, str):
            # Handle case where datetime was serialized to string
            from datetime import datetime
            try:
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            except:
                # If parsing fails, consider it expired
                return True
        
        return datetime.utcnow() > expires_at
    
    def access(self) -> Any:
        """Record an access to this cached value."""
        self.hit_count += 1
        self.last_accessed = datetime.utcnow()
        return self.value