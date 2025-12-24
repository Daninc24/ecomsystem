"""
Configuration Management Service for SQLite
Handles real-time site settings and configuration changes with advanced features
"""

from typing import Any, Dict, Optional, List
from datetime import datetime, timezone
from models_sqlite import AdminSetting, ActivityLog, db
import json


class ConfigurationManager:
    """Advanced service for managing configuration settings with real-time updates."""
    
    def __init__(self, database):
        self.db = database
        self._cache = {}
        self._cache_timestamp = None
    
    def get_setting(self, key: str, use_cache: bool = True) -> Any:
        """Get a configuration setting value with caching."""
        if use_cache and self._is_cache_valid():
            return self._cache.get(key)
        
        setting = AdminSetting.query.filter_by(key=key).first()
        if setting:
            value = setting.get_value()
            self._cache[key] = value
            return value
        return None
    
    def update_setting(self, key: str, value: Any, user_id: Optional[int] = None, 
                      category: str = 'general', description: str = None) -> Dict[str, Any]:
        """Update a configuration setting with validation and logging."""
        try:
            setting = AdminSetting.query.filter_by(key=key).first()
            old_value = None
            
            if setting:
                # Update existing setting
                old_value = setting.get_value()
                setting.set_value(value)
                setting.updated_at = datetime.now(timezone.utc)
                if user_id:
                    setting.updated_by = user_id
                if description:
                    setting.description = description
            else:
                # Create new setting
                setting = AdminSetting(
                    key=key,
                    category=category,
                    description=description or f'Setting for {key}',
                    data_type=self._detect_data_type(value),
                    updated_by=user_id
                )
                setting.set_value(value)
                db.session.add(setting)
            
            db.session.commit()
            
            # Clear cache
            self._cache.pop(key, None)
            
            # Log the change
            self._log_setting_change(key, old_value, value, user_id)
            
            # Broadcast change to connected clients (if WebSocket is implemented)
            self._broadcast_setting_change(key, value)
            
            return {
                'success': True,
                'key': key,
                'value': value,
                'old_value': old_value,
                'requires_restart': setting.requires_restart
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_all_settings(self, category: str = None) -> Dict[str, Any]:
        """Get all configuration settings, optionally filtered by category."""
        query = AdminSetting.query
        if category:
            query = query.filter_by(category=category)
        
        settings = {}
        for setting in query.all():
            settings[setting.key] = {
                'value': setting.get_value(),
                'category': setting.category,
                'description': setting.description,
                'data_type': setting.data_type,
                'is_sensitive': setting.is_sensitive,
                'requires_restart': setting.requires_restart,
                'updated_at': setting.updated_at.isoformat() if setting.updated_at else None
            }
        return settings
    
    def get_settings_by_category(self, category: str) -> Dict[str, Any]:
        """Get settings by category with metadata."""
        settings = {}
        for setting in AdminSetting.query.filter_by(category=category).all():
            settings[setting.key] = {
                'value': setting.get_value(),
                'description': setting.description,
                'data_type': setting.data_type,
                'is_sensitive': setting.is_sensitive
            }
        return settings
    
    def delete_setting(self, key: str, user_id: Optional[int] = None) -> bool:
        """Delete a configuration setting with logging."""
        try:
            setting = AdminSetting.query.filter_by(key=key).first()
            if setting:
                old_value = setting.get_value()
                db.session.delete(setting)
                db.session.commit()
                
                # Clear cache
                self._cache.pop(key, None)
                
                # Log the deletion
                self._log_setting_change(key, old_value, None, user_id, action='delete')
                
                return True
            return False
        except Exception as e:
            db.session.rollback()
            return False
    
    def validate_setting(self, key: str, value: Any) -> Dict[str, Any]:
        """Validate a setting value before saving."""
        validation_rules = {
            'site_name': {'type': str, 'min_length': 1, 'max_length': 100},
            'contact_email': {'type': str, 'pattern': r'^[^@]+@[^@]+\.[^@]+$'},
            'products_per_page': {'type': int, 'min': 1, 'max': 100},
            'max_file_size': {'type': int, 'min': 1024, 'max': 50 * 1024 * 1024}  # 50MB
        }
        
        if key not in validation_rules:
            return {'valid': True}
        
        rules = validation_rules[key]
        
        # Type validation
        if 'type' in rules and not isinstance(value, rules['type']):
            return {'valid': False, 'error': f'Value must be of type {rules["type"].__name__}'}
        
        # String validations
        if isinstance(value, str):
            if 'min_length' in rules and len(value) < rules['min_length']:
                return {'valid': False, 'error': f'Value must be at least {rules["min_length"]} characters'}
            if 'max_length' in rules and len(value) > rules['max_length']:
                return {'valid': False, 'error': f'Value must be at most {rules["max_length"]} characters'}
            if 'pattern' in rules:
                import re
                if not re.match(rules['pattern'], value):
                    return {'valid': False, 'error': 'Value format is invalid'}
        
        # Numeric validations
        if isinstance(value, (int, float)):
            if 'min' in rules and value < rules['min']:
                return {'valid': False, 'error': f'Value must be at least {rules["min"]}'}
            if 'max' in rules and value > rules['max']:
                return {'valid': False, 'error': f'Value must be at most {rules["max"]}'}
        
        return {'valid': True}
    
    def export_settings(self, category: str = None) -> str:
        """Export settings to JSON format."""
        settings = self.get_all_settings(category)
        return json.dumps(settings, indent=2, default=str)
    
    def import_settings(self, settings_json: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Import settings from JSON format."""
        try:
            settings = json.loads(settings_json)
            imported = 0
            errors = []
            
            for key, setting_data in settings.items():
                if isinstance(setting_data, dict) and 'value' in setting_data:
                    value = setting_data['value']
                    category = setting_data.get('category', 'general')
                    description = setting_data.get('description')
                else:
                    value = setting_data
                    category = 'general'
                    description = None
                
                # Validate setting
                validation = self.validate_setting(key, value)
                if not validation['valid']:
                    errors.append(f"{key}: {validation['error']}")
                    continue
                
                # Update setting
                result = self.update_setting(key, value, user_id, category, description)
                if result['success']:
                    imported += 1
                else:
                    errors.append(f"{key}: {result['error']}")
            
            return {
                'success': True,
                'imported': imported,
                'errors': errors
            }
            
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'Invalid JSON format: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _detect_data_type(self, value: Any) -> str:
        """Detect the data type of a value."""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'number'
        elif isinstance(value, float):
            return 'number'
        elif isinstance(value, (dict, list)):
            return 'json'
        else:
            return 'string'
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid (5 minutes)."""
        if not self._cache_timestamp:
            return False
        return (datetime.now(timezone.utc) - self._cache_timestamp).seconds < 300
    
    def _log_setting_change(self, key: str, old_value: Any, new_value: Any, 
                           user_id: Optional[int], action: str = 'update'):
        """Log setting changes for audit trail."""
        try:
            log = ActivityLog(
                user_id=user_id,
                action=f'setting_{action}',
                resource_type='admin_setting',
                resource_id=key,
                success=True
            )
            log.set_details({
                'key': key,
                'old_value': old_value,
                'new_value': new_value,
                'action': action
            })
            db.session.add(log)
            db.session.commit()
        except Exception:
            pass  # Don't fail the main operation if logging fails
    
    def _broadcast_setting_change(self, key: str, value: Any):
        """Broadcast setting changes to connected clients (placeholder for WebSocket)."""
        # This would integrate with WebSocket or Server-Sent Events
        # For now, it's a placeholder for future real-time functionality
        pass