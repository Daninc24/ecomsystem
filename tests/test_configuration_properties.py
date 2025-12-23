"""
Property-based tests for configuration management
**Feature: dynamic-admin-system, Property 1: Real-time Configuration Propagation**
**Validates: Requirements 1.2, 1.3, 1.4**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime
from bson import ObjectId
from admin.services.configuration_manager import ConfigurationManager
from simple_mongo_mock import mock_mongo
import os
import shutil


# Generators for property-based testing
@st.composite
def valid_setting_key(draw):
    """Generate valid setting keys."""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_'),
        min_size=1,
        max_size=50
    ).filter(lambda x: x and not x.startswith('_') and not x.endswith('_')))


@st.composite
def valid_setting_value(draw):
    """Generate valid setting values of various types."""
    return draw(st.one_of(
        st.text(min_size=0, max_size=1000),
        st.integers(min_value=-1000000, max_value=1000000),
        st.floats(min_value=-1000000.0, max_value=1000000.0, allow_nan=False, allow_infinity=False),
        st.booleans(),
        st.lists(st.text(min_size=0, max_size=100), min_size=0, max_size=10)
    ))


@st.composite
def configuration_setting(draw):
    """Generate a complete configuration setting."""
    key = draw(valid_setting_key())
    value = draw(valid_setting_value())
    category = draw(st.sampled_from(['general', 'appearance', 'security', 'performance', 'integration']))
    description = draw(st.text(min_size=0, max_size=200))
    
    # Generate appropriate validation rules based on value type
    validation_rules = {}
    if isinstance(value, str):
        validation_rules = {
            'type': 'string',
            'min_length': 0,
            'max_length': 1000
        }
    elif isinstance(value, (int, float)):
        validation_rules = {
            'type': 'number',
            'min': -1000000,
            'max': 1000000
        }
    elif isinstance(value, bool):
        validation_rules = {'type': 'boolean'}
    
    return {
        'key': key,
        'value': value,
        'category': category,
        'description': description,
        'validation_rules': validation_rules,
        'is_sensitive': draw(st.booleans()),
        'requires_restart': False
    }


def get_clean_mongo_db():
    """Get a clean MongoDB mock instance."""
    # Clear all collections by deleting their files
    db_path = "mock_db/ecommerce"
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    
    # Recreate the database directory
    os.makedirs(db_path, exist_ok=True)
    
    return mock_mongo.db


class TestConfigurationPropagation:
    """Property-based tests for real-time configuration propagation."""
    
    @given(setting=configuration_setting())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_configuration_propagation_property(self, setting):
        """
        **Feature: dynamic-admin-system, Property 1: Real-time Configuration Propagation**
        **Validates: Requirements 1.2, 1.3, 1.4**
        
        Property: For any configuration change, all components that depend on that 
        configuration should reflect the new value immediately without requiring system restart.
        
        This test verifies that:
        1. Configuration changes are immediately available through get_setting
        2. Change listeners are notified of the update
        3. Cache is properly invalidated and updated
        4. The change propagates without requiring restart
        """
        mongo_db = get_clean_mongo_db()
        config_manager = ConfigurationManager(mongo_db)
        user_id = ObjectId()
        
        # Create the initial setting
        setting_id = config_manager.create_setting(
            key=setting['key'],
            value=setting['value'],
            category=setting['category'],
            description=setting['description'],
            validation_rules=setting['validation_rules'],
            is_sensitive=setting['is_sensitive'],
            user_id=user_id
        )
        
        # Verify initial value is retrievable
        initial_value = config_manager.get_setting(setting['key'])
        assert initial_value == setting['value'], "Initial setting value should be retrievable"
        
        # Generate a new value of the same type
        if isinstance(setting['value'], str):
            new_value = "updated_" + str(setting['value'])[:990]  # Keep within validation limits
        elif isinstance(setting['value'], (int, float)):
            new_value = setting['value'] + 1 if setting['value'] < 999999 else setting['value'] - 1
        elif isinstance(setting['value'], bool):
            new_value = not setting['value']
        elif isinstance(setting['value'], list):
            new_value = setting['value'] + ['new_item'] if len(setting['value']) < 9 else setting['value'][:-1]
        else:
            new_value = setting['value']  # Fallback for other types
        
        # Track change notifications
        change_notifications = []
        
        def change_listener(change_event):
            change_notifications.append(change_event)
        
        config_manager.register_change_listener(change_listener)
        
        # Update the setting
        update_success = config_manager.update_setting(setting['key'], new_value, user_id)
        assert update_success, "Setting update should succeed"
        
        # Property 1: Immediate availability - the new value should be immediately available
        retrieved_value = config_manager.get_setting(setting['key'], use_cache=False)
        assert retrieved_value == new_value, "Updated value should be immediately available without cache"
        
        # Property 2: Cache invalidation - cached value should also reflect the change
        cached_value = config_manager.get_setting(setting['key'], use_cache=True)
        assert cached_value == new_value, "Updated value should be available through cache"
        
        # Property 3: Change notification - listeners should be notified
        assert len(change_notifications) == 1, "Exactly one change notification should be sent"
        
        change_event = change_notifications[0]
        assert change_event['key'] == setting['key'], "Change notification should contain correct key"
        assert change_event['old_value'] == setting['value'], "Change notification should contain old value"
        assert change_event['new_value'] == new_value, "Change notification should contain new value"
        assert 'timestamp' in change_event, "Change notification should contain timestamp"
        
        # Property 4: Persistence - the change should persist across manager instances
        new_config_manager = ConfigurationManager(mongo_db)
        persisted_value = new_config_manager.get_setting(setting['key'])
        assert persisted_value == new_value, "Updated value should persist across manager instances"
        
        # Property 5: No restart required - all operations should complete without restart
        # This is implicitly tested by the fact that all assertions pass in a single test run
        
    @given(settings_list=st.lists(configuration_setting(), min_size=2, max_size=5))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_multiple_configuration_propagation(self, settings_list):
        """
        Test that multiple configuration changes propagate correctly.
        
        This ensures that batch updates or rapid successive updates all propagate properly.
        """
        mongo_db = get_clean_mongo_db()
        config_manager = ConfigurationManager(mongo_db)
        user_id = ObjectId()
        
        # Ensure unique keys
        unique_settings = []
        seen_keys = set()
        for setting in settings_list:
            if setting['key'] not in seen_keys:
                unique_settings.append(setting)
                seen_keys.add(setting['key'])
        
        if len(unique_settings) < 2:
            return  # Skip if we don't have enough unique settings
        
        # Create all settings
        for setting in unique_settings:
            config_manager.create_setting(
                key=setting['key'],
                value=setting['value'],
                category=setting['category'],
                description=setting['description'],
                validation_rules=setting['validation_rules'],
                is_sensitive=setting['is_sensitive'],
                user_id=user_id
            )
        
        # Track all changes
        all_changes = []
        
        def change_listener(change_event):
            all_changes.append(change_event)
        
        config_manager.register_change_listener(change_listener)
        
        # Update all settings with new values
        updated_values = {}
        for setting in unique_settings:
            if isinstance(setting['value'], str):
                new_value = "batch_" + str(setting['value'])[:990]
            elif isinstance(setting['value'], (int, float)):
                new_value = setting['value'] + 100 if setting['value'] < 999900 else setting['value'] - 100
            elif isinstance(setting['value'], bool):
                new_value = not setting['value']
            elif isinstance(setting['value'], list):
                new_value = ['batch'] + setting['value'][:9]
            else:
                new_value = setting['value']
            
            updated_values[setting['key']] = new_value
            config_manager.update_setting(setting['key'], new_value, user_id)
        
        # Verify all changes propagated
        for setting in unique_settings:
            key = setting['key']
            expected_value = updated_values[key]
            
            # Check immediate availability
            actual_value = config_manager.get_setting(key)
            assert actual_value == expected_value, f"Setting {key} should have updated value {expected_value}"
        
        # Verify all change notifications were sent
        assert len(all_changes) == len(unique_settings), "Should receive one notification per setting update"
        
        # Verify each change notification is correct
        change_by_key = {change['key']: change for change in all_changes}
        for setting in unique_settings:
            key = setting['key']
            assert key in change_by_key, f"Should have change notification for {key}"
            
            change = change_by_key[key]
            assert change['old_value'] == setting['value'], f"Old value should match for {key}"
            assert change['new_value'] == updated_values[key], f"New value should match for {key}"


class TestConfigurationValidation:
    """Property-based tests for configuration validation consistency."""
    
    @given(setting=configuration_setting())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_configuration_validation_consistency_property(self, setting):
        """
        **Feature: dynamic-admin-system, Property 2: Configuration Validation Consistency**
        **Validates: Requirements 1.5**
        
        Property: For any configuration setting, invalid inputs should be rejected with 
        clear error messages, and valid inputs should be accepted and applied correctly.
        
        This test verifies that:
        1. Valid values that conform to validation rules are accepted
        2. Invalid values that violate validation rules are rejected
        3. Error messages are clear and descriptive
        4. Validation is consistent across multiple attempts
        """
        mongo_db = get_clean_mongo_db()
        config_manager = ConfigurationManager(mongo_db)
        user_id = ObjectId()
        
        # Create the setting
        setting_id = config_manager.create_setting(
            key=setting['key'],
            value=setting['value'],
            category=setting['category'],
            description=setting['description'],
            validation_rules=setting['validation_rules'],
            is_sensitive=setting['is_sensitive'],
            user_id=user_id
        )
        
        # Property 1: Valid values should be accepted
        validation_result = config_manager.validate_setting(setting['key'], setting['value'])
        assert validation_result.is_valid, f"Original valid value should pass validation: {validation_result.error_message}"
        
        # Test updating with the same valid value
        update_success = config_manager.update_setting(setting['key'], setting['value'], user_id)
        assert update_success, "Updating with valid value should succeed"
        
        # Property 2: Invalid values should be rejected with clear error messages
        validation_rules = setting['validation_rules']
        
        if validation_rules.get('type') == 'string':
            # Test invalid type
            invalid_type_result = config_manager.validate_setting(setting['key'], 123)
            assert not invalid_type_result.is_valid, "Non-string value should be rejected for string setting"
            assert "Expected string" in invalid_type_result.error_message, "Error message should mention expected type"
            
            # Test length violations if rules exist
            if 'min_length' in validation_rules and validation_rules['min_length'] > 0:
                short_string = 'x' * (validation_rules['min_length'] - 1)
                short_result = config_manager.validate_setting(setting['key'], short_string)
                assert not short_result.is_valid, "String shorter than min_length should be rejected"
                assert "below minimum" in short_result.error_message, "Error message should mention minimum length"
            
            if 'max_length' in validation_rules:
                long_string = 'x' * (validation_rules['max_length'] + 1)
                long_result = config_manager.validate_setting(setting['key'], long_string)
                assert not long_result.is_valid, "String longer than max_length should be rejected"
                assert "above maximum" in long_result.error_message, "Error message should mention maximum length"
        
        elif validation_rules.get('type') == 'number':
            # Test invalid type
            invalid_type_result = config_manager.validate_setting(setting['key'], "not_a_number")
            assert not invalid_type_result.is_valid, "Non-number value should be rejected for number setting"
            assert "Expected number" in invalid_type_result.error_message, "Error message should mention expected type"
            
            # Test range violations if rules exist
            if 'min' in validation_rules:
                below_min = validation_rules['min'] - 1
                min_result = config_manager.validate_setting(setting['key'], below_min)
                assert not min_result.is_valid, "Number below minimum should be rejected"
                assert "below minimum" in min_result.error_message, "Error message should mention minimum value"
            
            if 'max' in validation_rules:
                above_max = validation_rules['max'] + 1
                max_result = config_manager.validate_setting(setting['key'], above_max)
                assert not max_result.is_valid, "Number above maximum should be rejected"
                assert "above maximum" in max_result.error_message, "Error message should mention maximum value"
        
        elif validation_rules.get('type') == 'boolean':
            # Test invalid type
            invalid_type_result = config_manager.validate_setting(setting['key'], "not_a_boolean")
            assert not invalid_type_result.is_valid, "Non-boolean value should be rejected for boolean setting"
            assert "Expected boolean" in invalid_type_result.error_message, "Error message should mention expected type"
        
        # Test allowed values constraint if present
        if 'allowed_values' in validation_rules:
            allowed_values = validation_rules['allowed_values']
            if allowed_values:  # Only test if there are allowed values
                # Generate a value that's not in the allowed list
                if isinstance(setting['value'], str):
                    invalid_value = "definitely_not_in_allowed_values_" + str(len(allowed_values))
                elif isinstance(setting['value'], (int, float)):
                    invalid_value = max(allowed_values) + 999 if allowed_values else 999999
                else:
                    invalid_value = "invalid"
                
                if invalid_value not in allowed_values:
                    allowed_result = config_manager.validate_setting(setting['key'], invalid_value)
                    assert not allowed_result.is_valid, "Value not in allowed_values should be rejected"
                    assert "not in allowed values" in allowed_result.error_message, "Error message should mention allowed values"
        
        # Property 3: Validation should be consistent across multiple attempts
        for _ in range(3):
            consistent_result = config_manager.validate_setting(setting['key'], setting['value'])
            assert consistent_result.is_valid, "Validation should be consistent across multiple attempts"
        
        # Property 4: Invalid updates should be rejected and not change the setting
        original_value = config_manager.get_setting(setting['key'])
        
        # Try to update with an invalid value (wrong type)
        if validation_rules.get('type') == 'string':
            invalid_update_value = 12345
        elif validation_rules.get('type') == 'number':
            invalid_update_value = "not_a_number"
        elif validation_rules.get('type') == 'boolean':
            invalid_update_value = "not_a_boolean"
        else:
            invalid_update_value = None  # Skip this test for other types
        
        if invalid_update_value is not None:
            try:
                config_manager.update_setting(setting['key'], invalid_update_value, user_id)
                assert False, "Update with invalid value should raise ValueError"
            except ValueError as e:
                assert str(e), "ValueError should have a descriptive message"
            
            # Verify the setting value didn't change
            unchanged_value = config_manager.get_setting(setting['key'])
            assert unchanged_value == original_value, "Setting value should not change after failed validation"
    
    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_nonexistent_setting_validation(self, nonexistent_key):
        """
        Test that validation of non-existent settings is handled properly.
        """
        mongo_db = get_clean_mongo_db()
        config_manager = ConfigurationManager(mongo_db)
        
        # Ensure the key doesn't exist by using a unique prefix
        unique_key = f"nonexistent_{nonexistent_key}_{datetime.utcnow().timestamp()}"
        
        # Validation of non-existent setting should fail
        result = config_manager.validate_setting(unique_key, "any_value")
        assert not result.is_valid, "Validation of non-existent setting should fail"
        assert "not found" in result.error_message, "Error message should indicate setting not found"