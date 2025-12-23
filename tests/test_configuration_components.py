"""
Integration tests for configuration management components
Tests the interaction between ConfigurationManager, SettingsValidator, ChangeNotifier, and ConfigurationCache
"""

import pytest
from datetime import datetime, timedelta
from bson import ObjectId
from admin.services import (
    ConfigurationManager, 
    SettingsValidator, 
    ChangeNotifier, 
    ConfigurationCache,
    ValidationResult
)
from simple_mongo_mock import mock_mongo
import os
import shutil


def get_clean_mongo_db():
    """Get a clean MongoDB mock instance."""
    db_path = "mock_db/ecommerce"
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    os.makedirs(db_path, exist_ok=True)
    return mock_mongo.db


class TestConfigurationComponents:
    """Test the integration of all configuration management components."""
    
    def test_settings_validator_standalone(self):
        """Test SettingsValidator as a standalone component."""
        validator = SettingsValidator()
        
        # Test type validation
        result = validator.validate_value("test", {'type': 'string'})
        assert result.is_valid
        
        result = validator.validate_value(123, {'type': 'string'})
        assert not result.is_valid
        assert "Expected string" in result.error_message
        
        # Test range validation
        result = validator.validate_value(50, {'type': 'number', 'min': 0, 'max': 100})
        assert result.is_valid
        
        result = validator.validate_value(150, {'type': 'number', 'min': 0, 'max': 100})
        assert not result.is_valid
        assert "above maximum" in result.error_message
    
    def test_change_notifier_standalone(self):
        """Test ChangeNotifier as a standalone component."""
        notifier = ChangeNotifier()
        
        # Track notifications
        notifications = []
        
        def listener(event):
            notifications.append(event)
        
        # Register listener
        notifier.register_listener("test_listener", listener)
        
        # Broadcast change
        results = notifier.broadcast_change("test_key", "old_value", "new_value")
        
        assert len(notifications) == 1
        assert notifications[0].key == "test_key"
        assert notifications[0].old_value == "old_value"
        assert notifications[0].new_value == "new_value"
        
        # Test listener filtering
        filtered_notifications = []
        
        def filtered_listener(event):
            filtered_notifications.append(event)
        
        notifier.register_listener("filtered_listener", filtered_listener, filter_keys=["specific_key"])
        
        # This should not trigger the filtered listener
        notifier.broadcast_change("other_key", "old", "new")
        assert len(filtered_notifications) == 0
        
        # This should trigger the filtered listener
        notifier.broadcast_change("specific_key", "old", "new")
        assert len(filtered_notifications) == 1
    
    def test_configuration_cache_standalone(self):
        """Test ConfigurationCache as a standalone component."""
        mongo_db = get_clean_mongo_db()
        cache = ConfigurationCache(mongo_db)
        
        # Test basic caching
        cache.set("test_key", "test_value")
        value = cache.get("test_key")
        assert value == "test_value"
        
        # Test cache miss
        missing_value = cache.get("nonexistent_key")
        assert missing_value is None
        
        # Test cache invalidation
        cache.invalidate("test_key")
        invalidated_value = cache.get("test_key")
        assert invalidated_value is None
        
        # Test cache statistics
        stats = cache.get_statistics()
        assert 'total_hits' in stats
        assert 'total_misses' in stats
        assert 'hit_rate_percent' in stats
    
    def test_configuration_manager_integration(self):
        """Test that ConfigurationManager properly integrates all components."""
        mongo_db = get_clean_mongo_db()
        config_manager = ConfigurationManager(mongo_db)
        user_id = ObjectId()
        
        # Create a setting
        setting_id = config_manager.create_setting(
            key="integration_test",
            value="initial_value",
            category="test",
            description="Integration test setting",
            validation_rules={'type': 'string', 'min_length': 1, 'max_length': 100},
            user_id=user_id
        )
        
        # Test that all components are working together
        
        # 1. Validator should be used for validation
        try:
            config_manager.update_setting("integration_test", 123, user_id)  # Invalid type
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Expected string" in str(e)
        
        # 2. Cache should be working
        value1 = config_manager.get_setting("integration_test", use_cache=True)
        value2 = config_manager.get_setting("integration_test", use_cache=True)
        assert value1 == value2 == "initial_value"
        
        # 3. Change notifier should be working
        notifications = []
        
        def change_listener(event):
            notifications.append(event)
        
        config_manager.register_change_listener(change_listener)
        
        # Update the setting
        success = config_manager.update_setting("integration_test", "updated_value", user_id)
        assert success
        
        # Check that change was notified
        assert len(notifications) == 1
        assert notifications[0]['key'] == "integration_test"
        assert notifications[0]['old_value'] == "initial_value"
        assert notifications[0]['new_value'] == "updated_value"
        
        # 4. Cache should be invalidated and updated
        cached_value = config_manager.get_setting("integration_test", use_cache=True)
        assert cached_value == "updated_value"
        
        # 5. Advanced change notifier features should work
        advanced_notifications = []
        
        def advanced_listener(event):
            advanced_notifications.append(event)
        
        config_manager.register_change_listener_advanced(
            "advanced_listener", 
            advanced_listener, 
            filter_keys=["integration_test"],
            priority=10
        )
        
        # Update again
        config_manager.update_setting("integration_test", "final_value", user_id)
        
        # Should have received notification through advanced listener
        assert len(advanced_notifications) == 1
        assert advanced_notifications[0].key == "integration_test"
        assert advanced_notifications[0].new_value == "final_value"
        
        # 6. Cache statistics should be available
        cache_stats = config_manager.get_cache_statistics()
        assert cache_stats['total_hits'] > 0
        
        # 7. Change history should be available
        history = config_manager.get_change_history(limit=10)
        assert len(history) >= 2  # At least 2 changes made
        
    def test_custom_validation_rules(self):
        """Test custom validation rules through the validator."""
        mongo_db = get_clean_mongo_db()
        config_manager = ConfigurationManager(mongo_db)
        user_id = ObjectId()
        
        # Register a custom validator
        def email_validator(value):
            if '@' not in value:
                return ValidationResult(False, "Must be a valid email address")
            return ValidationResult(True)
        
        config_manager.validator.register_custom_validator("email_setting", email_validator)
        
        # Create setting with custom validation
        setting_id = config_manager.create_setting(
            key="email_setting",
            value="test@example.com",
            category="contact",
            description="Email address setting",
            validation_rules={'type': 'string'},
            user_id=user_id
        )
        
        # Valid email should work
        success = config_manager.update_setting("email_setting", "new@example.com", user_id)
        assert success
        
        # Invalid email should fail
        try:
            config_manager.update_setting("email_setting", "invalid_email", user_id)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "valid email address" in str(e)