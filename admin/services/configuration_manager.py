"""
Configuration Management Service
Handles real-time site settings and configuration changes
"""

from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from bson import ObjectId
from .base_service import BaseService
from ..models.configuration import AdminSetting, ConfigurationCache
from .settings_validator import SettingsValidator, ValidationResult
from .change_notifier import ChangeNotifier
from .configuration_cache import ConfigurationCache as CacheManager


class ConfigurationManager(BaseService):
    """Service for managing configuration settings with real-time updates."""
    
    def __init__(self, mongo_db):
        super().__init__(mongo_db)
        self.cache_collection = self.db.admin_config_cache
        
        # Initialize components
        self.validator = SettingsValidator()
        self.change_notifier = ChangeNotifier()
        self.cache_manager = CacheManager(mongo_db, default_ttl=timedelta(hours=1))
        
        # Legacy support for existing change listeners
        self.change_listeners = []
        self.cache_ttl = timedelta(hours=1)  # Default cache TTL
    
    def _get_collection_name(self) -> str:
        return 'admin_settings'
    
    def get_setting(self, key: str, use_cache: bool = True) -> Any:
        """Get a configuration setting value."""
        # Try cache first if enabled
        if use_cache:
            cached_value = self.cache_manager.get(key)
            if cached_value is not None:
                return cached_value
        
        # Get from database
        setting_doc = self.collection.find_one({'key': key})
        if not setting_doc:
            return None
        
        setting = AdminSetting.from_dict(setting_doc)
        
        # Cache the value if caching is enabled
        if use_cache:
            self.cache_manager.set(key, setting.value)
        
        return setting.value
    
    def update_setting(self, key: str, value: Any, user_id: Optional[ObjectId] = None) -> bool:
        """Update a configuration setting and broadcast changes."""
        # Get existing setting for validation
        existing_doc = self.collection.find_one({'key': key})
        if not existing_doc:
            return False
        
        existing_setting = AdminSetting.from_dict(existing_doc)
        
        # Validate the new value using the validator
        validation_result = self.validator.validate_setting(existing_setting, value)
        if not validation_result.is_valid:
            raise ValueError(validation_result.error_message)
        
        # Store old value for change notification
        old_value = existing_setting.value
        
        # Update the setting
        success = self.update(existing_setting.id, {'value': value}, user_id)
        
        if success:
            # Invalidate cache
            self.cache_manager.invalidate(key)
            
            # Broadcast change using the new change notifier system
            self.change_notifier.broadcast_change(key, old_value, value, str(user_id) if user_id else None)
            
            # Legacy support - call legacy listeners directly
            change_event = {
                'key': key,
                'old_value': old_value,
                'new_value': value,
                'timestamp': datetime.utcnow()
            }
            
            for listener in self.change_listeners:
                try:
                    listener(change_event)
                except Exception as e:
                    # Log error but don't fail the broadcast
                    print(f"Error in legacy change listener: {e}")
        
        return success
    
    def validate_setting(self, key: str, value: Any) -> ValidationResult:
        """Validate a configuration setting value."""
        setting_doc = self.collection.find_one({'key': key})
        if not setting_doc:
            return ValidationResult(False, f"Setting '{key}' not found")
        
        setting = AdminSetting.from_dict(setting_doc)
        return self.validator.validate_setting(setting, value)
    
    def broadcast_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """Broadcast configuration changes to all registered listeners."""
        change_event = {
            'key': key,
            'old_value': old_value,
            'new_value': new_value,
            'timestamp': datetime.utcnow()
        }
        
        for listener in self.change_listeners:
            try:
                listener(change_event)
            except Exception as e:
                # Log error but don't fail the broadcast
                print(f"Error in change listener: {e}")
    
    def get_all_settings(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get all configuration settings, optionally filtered by category."""
        query = {}
        if category:
            query['category'] = category
        
        settings_docs = self.find(query)
        settings = {}
        
        for doc in settings_docs:
            setting = AdminSetting.from_dict(doc)
            settings[setting.key] = setting.value
        
        return settings
    
    def create_setting(self, key: str, value: Any, category: str = 'general', 
                      description: str = '', validation_rules: Dict[str, Any] = None,
                      is_sensitive: bool = False, user_id: Optional[ObjectId] = None) -> ObjectId:
        """Create a new configuration setting."""
        if validation_rules is None:
            validation_rules = {}
        
        # Check if setting already exists
        if self.collection.find_one({'key': key}):
            raise ValueError(f"Setting '{key}' already exists")
        
        setting_data = {
            'key': key,
            'value': value,
            'category': category,
            'description': description,
            'validation_rules': validation_rules,
            'is_sensitive': is_sensitive,
            'requires_restart': False
        }
        
        return self.create(setting_data, user_id)
    
    def register_change_listener(self, listener_func) -> None:
        """Register a function to be called when configuration changes."""
        # Add to legacy listeners list only
        self.change_listeners.append(listener_func)
    
    def register_change_listener_advanced(self, listener_id: str, callback, 
                                        filter_keys: Optional[List[str]] = None, 
                                        priority: int = 0) -> None:
        """Register an advanced change listener with filtering and priority."""
        self.change_notifier.register_listener(listener_id, callback, filter_keys, priority)
    
    def unregister_change_listener(self, listener_id: str) -> bool:
        """Unregister a change listener."""
        return self.change_notifier.unregister_listener(listener_id)
    
    def get_change_history(self, limit: Optional[int] = None, key_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get configuration change history."""
        return self.change_notifier.get_change_history(limit, key_filter)
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        return self.cache_manager.get_statistics()
    
    def clear_cache(self) -> int:
        """Clear all cached configuration values."""
        return self.cache_manager.clear()
    
    
    # Legacy cache methods for backward compatibility
    def _get_from_cache(self, key: str) -> Any:
        """Legacy method - use cache_manager.get() instead."""
        return self.cache_manager.get(key)
    
    def _cache_value(self, key: str, value: Any) -> None:
        """Legacy method - use cache_manager.set() instead."""
        self.cache_manager.set(key, value)
    
    def _invalidate_cache(self, key: str) -> None:
        """Legacy method - use cache_manager.invalidate() instead."""
        self.cache_manager.invalidate(key)