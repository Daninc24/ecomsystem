"""
Theme customization models
"""

from datetime import datetime
from typing import Any, Dict, Optional, List
from bson import ObjectId
from .base import BaseModel


class ThemeConfig(BaseModel):
    """Model for theme configuration settings."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name: str = kwargs.get('name', '')
        self.description: str = kwargs.get('description', '')
        self.settings: Dict[str, Any] = kwargs.get('settings', {})
        self.css_generated: str = kwargs.get('css_generated', '')
        self.is_active: bool = kwargs.get('is_active', False)
        self.is_default: bool = kwargs.get('is_default', False)
        self.backup_id: Optional[ObjectId] = kwargs.get('backup_id')
        self.version: str = kwargs.get('version', '1.0.0')
        self.preview_url: str = kwargs.get('preview_url', '')
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific theme setting."""
        keys = key.split('.')
        value = self.settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set a specific theme setting."""
        keys = key.split('.')
        current = self.settings
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Set the final value
        current[keys[-1]] = value
        self.updated_at = datetime.utcnow()
    
    def get_color_palette(self) -> Dict[str, str]:
        """Get the color palette from theme settings."""
        return self.get_setting('colors', {})
    
    def get_typography(self) -> Dict[str, Any]:
        """Get typography settings from theme."""
        return self.get_setting('typography', {})


class ThemeBackup(BaseModel):
    """Model for theme backups."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.theme_id: ObjectId = kwargs.get('theme_id')
        self.backup_name: str = kwargs.get('backup_name', '')
        self.settings_snapshot: Dict[str, Any] = kwargs.get('settings_snapshot', {})
        self.css_snapshot: str = kwargs.get('css_snapshot', '')
        self.backup_type: str = kwargs.get('backup_type', 'manual')  # manual, automatic, pre_update
        self.description: str = kwargs.get('description', '')
        self.file_size: int = kwargs.get('file_size', 0)
    
    def restore_data(self) -> Dict[str, Any]:
        """Get the data needed to restore this backup."""
        return {
            'settings': self.settings_snapshot,
            'css_generated': self.css_snapshot,
            'restored_from_backup': str(self.id),
            'restored_at': datetime.utcnow()
        }