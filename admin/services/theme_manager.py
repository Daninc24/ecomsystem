"""
Theme Manager Service
Handles theme customization, live preview, and theme management operations
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from bson import ObjectId

from ..models.theme import ThemeConfig, ThemeBackup
from ..models.audit import ActivityLog
from .base_service import BaseService
from .css_generator import CSSGenerator
from .asset_manager import AssetManager
from .responsive_validator import ResponsiveValidator


class ThemeManager(BaseService):
    """Manages theme customization with live preview capabilities."""
    
    def __init__(self, db, user_id: Optional[ObjectId] = None):
        self.user_id = user_id
        # Initialize BaseService with just the db
        super().__init__(db)
        self.css_generator = CSSGenerator()
        self.asset_manager = AssetManager(db, user_id)
        self.responsive_validator = ResponsiveValidator()
        # Override collection references since we use multiple collections
        self.collection = db.theme_configs
        self.backup_collection = db.theme_backups
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'theme_configs'
    
    def get_active_theme(self) -> Optional[ThemeConfig]:
        """Get the currently active theme configuration."""
        theme_data = self.collection.find_one({'is_active': True})
        if theme_data:
            return ThemeConfig(**theme_data)
        return None
    
    def get_theme_by_id(self, theme_id: ObjectId) -> Optional[ThemeConfig]:
        """Get a theme configuration by ID."""
        theme_data = self.collection.find_one({'_id': theme_id})
        if theme_data:
            return ThemeConfig(**theme_data)
        return None
    
    def get_theme_by_name(self, name: str) -> Optional[ThemeConfig]:
        """Get a theme configuration by name."""
        theme_data = self.collection.find_one({'name': name})
        if theme_data:
            return ThemeConfig(**theme_data)
        return None
    
    def create_theme(self, name: str, description: str = "", 
                    settings: Optional[Dict[str, Any]] = None) -> ThemeConfig:
        """Create a new theme configuration."""
        if self.get_theme_by_name(name):
            raise ValueError(f"Theme with name '{name}' already exists")
        
        theme_config = ThemeConfig(
            name=name,
            description=description,
            settings=settings or self._get_default_theme_settings(),
            is_active=False,
            is_default=False,
            version="1.0.0",
            created_by=self.user_id,
            updated_by=self.user_id
        )
        
        # Generate initial CSS
        theme_config.css_generated = self.css_generator.generate_css(theme_config.settings)
        
        # Save to database
        result = self.collection.insert_one(theme_config.to_dict())
        theme_config.id = result.inserted_id
        
        # Log the action
        self._log_activity("theme_created", "theme", str(theme_config.id), {
            'theme_name': name,
            'description': description
        })
        
        return theme_config
    
    def update_theme_setting(self, theme_id: ObjectId, property_path: str, 
                           value: Any) -> ThemeConfig:
        """Update a specific theme setting and regenerate CSS."""
        theme = self.get_theme_by_id(theme_id)
        if not theme:
            raise ValueError(f"Theme with ID {theme_id} not found")
        
        # Create backup before making changes
        backup = self.backup_theme(theme_id, backup_type="automatic", 
                                 description=f"Auto backup before updating {property_path}")
        
        # Update the setting
        old_value = theme.get_setting(property_path)
        theme.set_setting(property_path, value)
        
        # Validate responsive design if needed
        if self._affects_responsive_design(property_path):
            validation_result = self.responsive_validator.validate_setting(
                property_path, value, theme.settings
            )
            if not validation_result.is_valid:
                raise ValueError(f"Setting violates responsive design: {validation_result.error}")
        
        # Regenerate CSS
        theme.css_generated = self.css_generator.generate_css(theme.settings)
        theme.updated_at = datetime.utcnow()
        theme.updated_by = self.user_id
        
        # Save to database
        self.collection.update_one(
            {'_id': theme_id},
            {'$set': theme.to_dict()}
        )
        
        # Log the action
        self._log_activity("theme_setting_updated", "theme", str(theme_id), {
            'property_path': property_path,
            'old_value': old_value,
            'new_value': value,
            'backup_id': str(backup.id)
        })
        
        return theme
    
    def apply_theme(self, theme_id: ObjectId) -> bool:
        """Apply a theme as the active theme."""
        theme = self.get_theme_by_id(theme_id)
        if not theme:
            raise ValueError(f"Theme with ID {theme_id} not found")
        
        # Deactivate current active theme
        current_active = self.get_active_theme()
        if current_active:
            self.collection.update_one(
                {'_id': current_active.id},
                {'$set': {'is_active': False, 'updated_at': datetime.utcnow()}}
            )
        
        # Activate the new theme
        self.collection.update_one(
            {'_id': theme_id},
            {'$set': {
                'is_active': True,
                'updated_at': datetime.utcnow(),
                'updated_by': self.user_id
            }}
        )
        
        # Write CSS to static files
        self._write_theme_css(theme.css_generated)
        
        # Log the action
        self._log_activity("theme_applied", "theme", str(theme_id), {
            'theme_name': theme.name,
            'previous_theme': str(current_active.id) if current_active else None
        })
        
        return True
    
    def backup_theme(self, theme_id: ObjectId, backup_type: str = "manual",
                    description: str = "") -> ThemeBackup:
        """Create a backup of a theme configuration."""
        theme = self.get_theme_by_id(theme_id)
        if not theme:
            raise ValueError(f"Theme with ID {theme_id} not found")
        
        backup_name = f"{theme.name}_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        backup = ThemeBackup(
            theme_id=theme_id,
            backup_name=backup_name,
            settings_snapshot=theme.settings.copy(),
            css_snapshot=theme.css_generated,
            backup_type=backup_type,
            description=description,
            file_size=len(json.dumps(theme.settings).encode('utf-8')),
            created_by=self.user_id
        )
        
        # Save backup to database
        result = self.backup_collection.insert_one(backup.to_dict())
        backup.id = result.inserted_id
        
        # Update theme with backup reference
        self.collection.update_one(
            {'_id': theme_id},
            {'$set': {'backup_id': backup.id}}
        )
        
        # Log the action
        self._log_activity("theme_backup_created", "theme_backup", str(backup.id), {
            'theme_id': str(theme_id),
            'backup_type': backup_type,
            'backup_name': backup_name
        })
        
        return backup
    
    def restore_theme(self, backup_id: ObjectId) -> ThemeConfig:
        """Restore a theme from a backup."""
        backup_data = self.backup_collection.find_one({'_id': backup_id})
        if not backup_data:
            raise ValueError(f"Backup with ID {backup_id} not found")
        
        backup = ThemeBackup(**backup_data)
        theme = self.get_theme_by_id(backup.theme_id)
        if not theme:
            raise ValueError(f"Original theme with ID {backup.theme_id} not found")
        
        # Create a backup of current state before restoring
        current_backup = self.backup_theme(
            backup.theme_id, 
            backup_type="automatic",
            description="Auto backup before restoration"
        )
        
        # Restore the theme settings
        restore_data = backup.restore_data()
        theme.settings = restore_data['settings']
        theme.css_generated = restore_data['css_generated']
        theme.updated_at = datetime.utcnow()
        theme.updated_by = self.user_id
        
        # Save restored theme
        self.collection.update_one(
            {'_id': backup.theme_id},
            {'$set': theme.to_dict()}
        )
        
        # If this was the active theme, update CSS files
        if theme.is_active:
            self._write_theme_css(theme.css_generated)
        
        # Log the action
        self._log_activity("theme_restored", "theme", str(theme.id), {
            'backup_id': str(backup_id),
            'backup_name': backup.backup_name,
            'current_backup_id': str(current_backup.id)
        })
        
        return theme
    
    def generate_preview_css(self, theme_id: ObjectId, 
                           temporary_settings: Optional[Dict[str, Any]] = None) -> str:
        """Generate CSS for live preview without saving changes."""
        theme = self.get_theme_by_id(theme_id)
        if not theme:
            raise ValueError(f"Theme with ID {theme_id} not found")
        
        # Merge temporary settings with existing settings
        preview_settings = theme.settings.copy()
        if temporary_settings:
            self._deep_merge_settings(preview_settings, temporary_settings)
        
        # Generate CSS for preview
        return self.css_generator.generate_css(preview_settings)
    
    def validate_theme_settings(self, settings: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate theme settings for correctness and responsive design."""
        errors = []
        
        # Validate required settings
        required_sections = ['colors', 'typography', 'layout', 'spacing']
        for section in required_sections:
            if section not in settings:
                errors.append(f"Missing required section: {section}")
        
        # Validate color values
        if 'colors' in settings:
            color_errors = self._validate_colors(settings['colors'])
            errors.extend(color_errors)
        
        # Validate typography
        if 'typography' in settings:
            typography_errors = self._validate_typography(settings['typography'])
            errors.extend(typography_errors)
        
        # Validate responsive design
        responsive_result = self.responsive_validator.validate_theme_settings(settings)
        if not responsive_result.is_valid:
            errors.append(f"Responsive design validation failed: {responsive_result.error}")
        
        return len(errors) == 0, errors
    
    def get_theme_list(self) -> List[Dict[str, Any]]:
        """Get a list of all themes with basic information."""
        themes = []
        for theme_data in self.collection.find({}, {
            'name': 1, 'description': 1, 'is_active': 1, 'is_default': 1,
            'version': 1, 'updated_at': 1, 'created_at': 1
        }):
            themes.append({
                'id': str(theme_data['_id']),
                'name': theme_data['name'],
                'description': theme_data.get('description', ''),
                'is_active': theme_data.get('is_active', False),
                'is_default': theme_data.get('is_default', False),
                'version': theme_data.get('version', '1.0.0'),
                'updated_at': theme_data.get('updated_at'),
                'created_at': theme_data.get('created_at')
            })
        return themes
    
    def delete_theme(self, theme_id: ObjectId) -> bool:
        """Delete a theme configuration (cannot delete active or default themes)."""
        theme = self.get_theme_by_id(theme_id)
        if not theme:
            raise ValueError(f"Theme with ID {theme_id} not found")
        
        if theme.is_active:
            raise ValueError("Cannot delete the active theme")
        
        if theme.is_default:
            raise ValueError("Cannot delete the default theme")
        
        # Delete associated backups
        self.backup_collection.delete_many({'theme_id': theme_id})
        
        # Delete the theme
        result = self.collection.delete_one({'_id': theme_id})
        
        # Log the action
        self._log_activity("theme_deleted", "theme", str(theme_id), {
            'theme_name': theme.name
        })
        
        return result.deleted_count > 0
    
    def _get_default_theme_settings(self) -> Dict[str, Any]:
        """Get default theme settings structure."""
        return {
            'colors': {
                'primary': '#007bff',
                'secondary': '#6c757d',
                'success': '#28a745',
                'danger': '#dc3545',
                'warning': '#ffc107',
                'info': '#17a2b8',
                'light': '#f8f9fa',
                'dark': '#343a40',
                'background': '#ffffff',
                'text': '#212529',
                'link': '#007bff',
                'border': '#dee2e6'
            },
            'typography': {
                'font_family_primary': 'system-ui, -apple-system, sans-serif',
                'font_family_secondary': 'Georgia, serif',
                'font_size_base': '16px',
                'font_size_small': '14px',
                'font_size_large': '18px',
                'font_weight_normal': '400',
                'font_weight_bold': '700',
                'line_height_base': '1.5',
                'letter_spacing': '0'
            },
            'layout': {
                'container_max_width': '1200px',
                'grid_columns': '12',
                'grid_gutter': '30px',
                'header_height': '80px',
                'footer_height': 'auto',
                'sidebar_width': '250px'
            },
            'spacing': {
                'padding_small': '8px',
                'padding_medium': '16px',
                'padding_large': '24px',
                'margin_small': '8px',
                'margin_medium': '16px',
                'margin_large': '24px'
            },
            'borders': {
                'radius_small': '4px',
                'radius_medium': '8px',
                'radius_large': '12px',
                'width_thin': '1px',
                'width_medium': '2px',
                'width_thick': '4px'
            },
            'shadows': {
                'small': '0 1px 3px rgba(0,0,0,0.12)',
                'medium': '0 4px 6px rgba(0,0,0,0.1)',
                'large': '0 10px 25px rgba(0,0,0,0.15)'
            }
        }
    
    def _affects_responsive_design(self, property_path: str) -> bool:
        """Check if a property affects responsive design."""
        responsive_properties = [
            'layout.container_max_width',
            'layout.grid_columns',
            'layout.grid_gutter',
            'typography.font_size_base',
            'spacing.padding_medium',
            'spacing.margin_medium'
        ]
        return property_path in responsive_properties
    
    def _validate_colors(self, colors: Dict[str, Any]) -> List[str]:
        """Validate color values."""
        errors = []
        color_pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
        
        import re
        for key, value in colors.items():
            if isinstance(value, str) and not re.match(color_pattern, value):
                if not value.startswith('rgb') and not value.startswith('hsl'):
                    errors.append(f"Invalid color format for {key}: {value}")
        
        return errors
    
    def _validate_typography(self, typography: Dict[str, Any]) -> List[str]:
        """Validate typography settings."""
        errors = []
        
        # Validate font sizes
        size_keys = ['font_size_base', 'font_size_small', 'font_size_large']
        for key in size_keys:
            if key in typography:
                value = typography[key]
                if isinstance(value, str) and not (value.endswith('px') or value.endswith('rem') or value.endswith('em')):
                    errors.append(f"Invalid font size unit for {key}: {value}")
        
        return errors
    
    def _deep_merge_settings(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Deep merge source settings into target settings."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge_settings(target[key], value)
            else:
                target[key] = value
    
    def _write_theme_css(self, css_content: str) -> None:
        """Write generated CSS to static files."""
        css_file_path = os.path.join('static', 'css', 'dynamic-styles.css')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(css_file_path), exist_ok=True)
        
        # Write CSS content
        with open(css_file_path, 'w', encoding='utf-8') as f:
            f.write(css_content)
    
    def _log_activity(self, action: str, resource_type: str, resource_id: str, 
                     details: Dict[str, Any]) -> None:
        """Log theme management activity."""
        if hasattr(self.db, 'activity_logs'):
            activity_log = ActivityLog(
                user_id=self.user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                ip_address="127.0.0.1",  # This should come from request context
                user_agent="Admin System",  # This should come from request context
                success=True,
                severity="info"
            )
            self.db.activity_logs.insert_one(activity_log.to_dict())