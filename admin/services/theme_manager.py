"""
Theme Management Service for SQLite
Handles theme customization and CSS generation with advanced features
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from models_sqlite import AdminSetting, ActivityLog, db
import json
import os
import hashlib


class ThemeManager:
    """Advanced service for managing themes and visual customization."""
    
    def __init__(self, database):
        self.db = database
        self.theme_cache = {}
        self.css_cache = {}
    
    def get_active_theme(self) -> Dict[str, Any]:
        """Get the currently active theme with all settings."""
        theme_setting = AdminSetting.query.filter_by(key='active_theme').first()
        theme_id = theme_setting.get_value() if theme_setting else 'default'
        
        if theme_id in self.theme_cache:
            return self.theme_cache[theme_id]
        
        # Load theme configuration
        theme_config = self._load_theme_config(theme_id)
        self.theme_cache[theme_id] = theme_config
        
        return theme_config
    
    def list_themes(self) -> List[Dict[str, Any]]:
        """List all available themes."""
        themes = [
            {
                'id': 'default',
                'name': 'MarketHub Default',
                'description': 'Clean and modern e-commerce theme',
                'preview_image': '/static/images/themes/default-preview.jpg',
                'is_active': True,
                'settings': self._get_default_theme_settings()
            },
            {
                'id': 'dark',
                'name': 'Dark Mode',
                'description': 'Dark theme for better night viewing',
                'preview_image': '/static/images/themes/dark-preview.jpg',
                'is_active': False,
                'settings': self._get_dark_theme_settings()
            },
            {
                'id': 'minimal',
                'name': 'Minimal',
                'description': 'Clean and minimal design',
                'preview_image': '/static/images/themes/minimal-preview.jpg',
                'is_active': False,
                'settings': self._get_minimal_theme_settings()
            }
        ]
        
        # Mark the active theme
        active_theme_id = self.get_active_theme()['id']
        for theme in themes:
            theme['is_active'] = theme['id'] == active_theme_id
        
        return themes
    
    def update_theme_setting(self, property: str, value: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Update a theme setting with validation."""
        try:
            # Validate the property and value
            validation = self._validate_theme_property(property, value)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': validation['error']
                }
            
            # Get current theme settings
            theme = self.get_active_theme()
            old_value = theme['settings'].get(property)
            
            # Update the setting
            setting_key = f'theme_{property}'
            setting = AdminSetting.query.filter_by(key=setting_key).first()
            
            if setting:
                setting.set_value(value)
                setting.updated_at = datetime.now(timezone.utc)
                if user_id:
                    setting.updated_by = user_id
            else:
                setting = AdminSetting(
                    key=setting_key,
                    category='theme',
                    description=f'Theme setting: {property}',
                    data_type='string',
                    updated_by=user_id
                )
                setting.set_value(value)
                db.session.add(setting)
            
            db.session.commit()
            
            # Clear caches
            self.theme_cache.clear()
            self.css_cache.clear()
            
            # Log the change
            self._log_theme_change(property, old_value, value, user_id)
            
            # Generate new CSS
            css_result = self.generate_css()
            
            return {
                'success': True,
                'property': property,
                'value': value,
                'old_value': old_value,
                'css_generated': css_result['success']
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_css(self, theme_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate CSS from theme configuration."""
        try:
            if not theme_config:
                theme_config = self.get_active_theme()
            
            # Create CSS hash for caching
            config_hash = hashlib.md5(json.dumps(theme_config, sort_keys=True).encode()).hexdigest()
            
            if config_hash in self.css_cache:
                return {
                    'success': True,
                    'css': self.css_cache[config_hash],
                    'cached': True
                }
            
            settings = theme_config['settings']
            
            # Generate CSS variables
            css_variables = self._generate_css_variables(settings)
            
            # Generate component styles
            component_styles = self._generate_component_styles(settings)
            
            # Generate responsive styles
            responsive_styles = self._generate_responsive_styles(settings)
            
            # Combine all CSS
            css_content = f"""
/* Generated Theme CSS - {datetime.now().isoformat()} */
:root {{
{css_variables}
}}

/* Component Styles */
{component_styles}

/* Responsive Styles */
{responsive_styles}

/* Custom CSS */
{settings.get('custom_css', '')}
"""
            
            # Cache the generated CSS
            self.css_cache[config_hash] = css_content
            
            # Save CSS to file
            css_file_path = os.path.join('static', 'css', 'theme-generated.css')
            os.makedirs(os.path.dirname(css_file_path), exist_ok=True)
            
            with open(css_file_path, 'w') as f:
                f.write(css_content)
            
            return {
                'success': True,
                'css': css_content,
                'file_path': css_file_path,
                'cached': False
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def preview_theme(self, theme_id: str, custom_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a preview of a theme with optional custom settings."""
        try:
            # Load base theme
            theme_config = self._load_theme_config(theme_id)
            
            # Apply custom settings if provided
            if custom_settings:
                theme_config['settings'].update(custom_settings)
            
            # Generate preview CSS
            css_result = self.generate_css(theme_config)
            
            if css_result['success']:
                return {
                    'success': True,
                    'theme_id': theme_id,
                    'css': css_result['css'],
                    'preview_url': f'/theme-preview/{theme_id}'
                }
            else:
                return css_result
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def activate_theme(self, theme_id: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Activate a theme."""
        try:
            # Validate theme exists
            available_themes = [theme['id'] for theme in self.list_themes()]
            if theme_id not in available_themes:
                return {
                    'success': False,
                    'error': 'Theme not found'
                }
            
            # Update active theme setting
            setting = AdminSetting.query.filter_by(key='active_theme').first()
            old_theme = setting.get_value() if setting else 'default'
            
            if setting:
                setting.set_value(theme_id)
                setting.updated_at = datetime.now(timezone.utc)
                if user_id:
                    setting.updated_by = user_id
            else:
                setting = AdminSetting(
                    key='active_theme',
                    category='theme',
                    description='Currently active theme',
                    data_type='string',
                    updated_by=user_id
                )
                setting.set_value(theme_id)
                db.session.add(setting)
            
            db.session.commit()
            
            # Clear caches
            self.theme_cache.clear()
            self.css_cache.clear()
            
            # Generate CSS for new theme
            css_result = self.generate_css()
            
            # Log theme activation
            self._log_theme_change('active_theme', old_theme, theme_id, user_id)
            
            return {
                'success': True,
                'theme_id': theme_id,
                'old_theme': old_theme,
                'css_generated': css_result['success']
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def export_theme(self, theme_id: Optional[str] = None) -> Dict[str, Any]:
        """Export theme configuration."""
        try:
            if not theme_id:
                theme_config = self.get_active_theme()
            else:
                theme_config = self._load_theme_config(theme_id)
            
            export_data = {
                'theme': theme_config,
                'exported_at': datetime.now(timezone.utc).isoformat(),
                'version': '1.0'
            }
            
            return {
                'success': True,
                'data': json.dumps(export_data, indent=2)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def import_theme(self, theme_data: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Import theme configuration."""
        try:
            import_data = json.loads(theme_data)
            theme_config = import_data.get('theme', {})
            
            if not theme_config or 'settings' not in theme_config:
                return {
                    'success': False,
                    'error': 'Invalid theme data format'
                }
            
            # Import theme settings
            imported_count = 0
            errors = []
            
            for property, value in theme_config['settings'].items():
                result = self.update_theme_setting(property, value, user_id)
                if result['success']:
                    imported_count += 1
                else:
                    errors.append(f"{property}: {result['error']}")
            
            return {
                'success': True,
                'imported_settings': imported_count,
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
    
    def _load_theme_config(self, theme_id: str) -> Dict[str, Any]:
        """Load theme configuration from database and defaults."""
        if theme_id == 'default':
            base_settings = self._get_default_theme_settings()
        elif theme_id == 'dark':
            base_settings = self._get_dark_theme_settings()
        elif theme_id == 'minimal':
            base_settings = self._get_minimal_theme_settings()
        else:
            base_settings = self._get_default_theme_settings()
        
        # Override with database settings
        theme_settings = AdminSetting.query.filter(AdminSetting.key.like('theme_%')).all()
        for setting in theme_settings:
            property_name = setting.key.replace('theme_', '')
            base_settings[property_name] = setting.get_value()
        
        return {
            'id': theme_id,
            'name': base_settings.get('name', 'Custom Theme'),
            'settings': base_settings,
            'is_active': True
        }
    
    def _get_default_theme_settings(self) -> Dict[str, Any]:
        """Get default theme settings."""
        return {
            'name': 'MarketHub Default',
            'primary_color': '#ff4747',
            'secondary_color': '#ff6b35',
            'accent_color': '#007bff',
            'background_color': '#ffffff',
            'text_color': '#333333',
            'link_color': '#007bff',
            'border_color': '#e5e7eb',
            'success_color': '#10b981',
            'warning_color': '#f59e0b',
            'error_color': '#ef4444',
            'font_family': 'Inter, system-ui, sans-serif',
            'font_size_base': '16px',
            'border_radius': '0.5rem',
            'box_shadow': '0 1px 3px rgba(0,0,0,0.1)',
            'header_height': '80px',
            'footer_background': '#1f2937',
            'custom_css': ''
        }
    
    def _get_dark_theme_settings(self) -> Dict[str, Any]:
        """Get dark theme settings."""
        return {
            'name': 'Dark Mode',
            'primary_color': '#ff6b6b',
            'secondary_color': '#4ecdc4',
            'accent_color': '#45b7d1',
            'background_color': '#1a1a1a',
            'text_color': '#ffffff',
            'link_color': '#45b7d1',
            'border_color': '#333333',
            'success_color': '#51cf66',
            'warning_color': '#ffd43b',
            'error_color': '#ff6b6b',
            'font_family': 'Inter, system-ui, sans-serif',
            'font_size_base': '16px',
            'border_radius': '0.5rem',
            'box_shadow': '0 1px 3px rgba(255,255,255,0.1)',
            'header_height': '80px',
            'footer_background': '#000000',
            'custom_css': ''
        }
    
    def _get_minimal_theme_settings(self) -> Dict[str, Any]:
        """Get minimal theme settings."""
        return {
            'name': 'Minimal',
            'primary_color': '#000000',
            'secondary_color': '#666666',
            'accent_color': '#333333',
            'background_color': '#ffffff',
            'text_color': '#000000',
            'link_color': '#333333',
            'border_color': '#cccccc',
            'success_color': '#28a745',
            'warning_color': '#ffc107',
            'error_color': '#dc3545',
            'font_family': 'Georgia, serif',
            'font_size_base': '16px',
            'border_radius': '0',
            'box_shadow': 'none',
            'header_height': '60px',
            'footer_background': '#f8f9fa',
            'custom_css': ''
        }
    
    def _validate_theme_property(self, property: str, value: str) -> Dict[str, Any]:
        """Validate theme property and value."""
        # Color validation
        color_properties = [
            'primary_color', 'secondary_color', 'accent_color', 'background_color',
            'text_color', 'link_color', 'border_color', 'success_color',
            'warning_color', 'error_color', 'footer_background'
        ]
        
        if property in color_properties:
            if not self._is_valid_color(value):
                return {
                    'valid': False,
                    'error': 'Invalid color format. Use hex (#ffffff) or rgb(255,255,255)'
                }
        
        # Size validation
        size_properties = ['font_size_base', 'header_height', 'border_radius']
        if property in size_properties:
            if not self._is_valid_size(value):
                return {
                    'valid': False,
                    'error': 'Invalid size format. Use px, rem, em, or %'
                }
        
        return {'valid': True}
    
    def _is_valid_color(self, color: str) -> bool:
        """Validate color format."""
        import re
        # Hex color
        if re.match(r'^#[0-9a-fA-F]{6}$', color):
            return True
        # RGB color
        if re.match(r'^rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)$', color):
            return True
        # RGBA color
        if re.match(r'^rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d.]+\s*\)$', color):
            return True
        return False
    
    def _is_valid_size(self, size: str) -> bool:
        """Validate size format."""
        import re
        return bool(re.match(r'^\d+(\.\d+)?(px|rem|em|%|vh|vw)$', size))
    
    def _generate_css_variables(self, settings: Dict[str, Any]) -> str:
        """Generate CSS custom properties."""
        variables = []
        for key, value in settings.items():
            if key != 'custom_css' and key != 'name':
                css_var = key.replace('_', '-')
                variables.append(f"  --{css_var}: {value};")
        return '\n'.join(variables)
    
    def _generate_component_styles(self, settings: Dict[str, Any]) -> str:
        """Generate component-specific styles."""
        return f"""
/* Header Styles */
.header {{
    height: var(--header-height);
    background-color: var(--background-color);
    border-bottom: 1px solid var(--border-color);
}}

/* Button Styles */
.btn-primary {{
    background-color: var(--primary-color);
    border-color: var(--primary-color);
    color: white;
    border-radius: var(--border-radius);
    box-shadow: var(--box-shadow);
}}

.btn-secondary {{
    background-color: var(--secondary-color);
    border-color: var(--secondary-color);
    color: white;
    border-radius: var(--border-radius);
}}

/* Card Styles */
.card {{
    background-color: var(--background-color);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    box-shadow: var(--box-shadow);
}}

/* Footer Styles */
.footer {{
    background-color: var(--footer-background);
    color: var(--text-color);
}}

/* Typography */
body {{
    font-family: var(--font-family);
    font-size: var(--font-size-base);
    color: var(--text-color);
    background-color: var(--background-color);
}}

a {{
    color: var(--link-color);
}}

/* Status Colors */
.text-success {{ color: var(--success-color); }}
.text-warning {{ color: var(--warning-color); }}
.text-error {{ color: var(--error-color); }}
"""
    
    def _generate_responsive_styles(self, settings: Dict[str, Any]) -> str:
        """Generate responsive styles."""
        return """
/* Responsive Styles */
@media (max-width: 768px) {
    .header {
        height: calc(var(--header-height) * 0.8);
    }
    
    body {
        font-size: calc(var(--font-size-base) * 0.9);
    }
}

@media (max-width: 480px) {
    .header {
        height: calc(var(--header-height) * 0.7);
    }
    
    body {
        font-size: calc(var(--font-size-base) * 0.85);
    }
}
"""
    
    def _log_theme_change(self, property: str, old_value: Any, new_value: Any, user_id: Optional[int]):
        """Log theme changes."""
        try:
            log = ActivityLog(
                user_id=user_id,
                action='theme_update',
                resource_type='theme',
                resource_id=property,
                success=True
            )
            log.set_details({
                'property': property,
                'old_value': old_value,
                'new_value': new_value
            })
            db.session.add(log)
            db.session.commit()
        except Exception:
            pass