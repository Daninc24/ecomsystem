"""
Theme Management API endpoints for Dynamic Admin System
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models_sqlite import AdminSetting, db
from datetime import datetime, timezone
import functools
import json

theme_bp = Blueprint('theme_api', __name__, url_prefix='/theme')


def admin_required(f):
    """Decorator to require admin role."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_role('admin'):
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403
        return f(*args, **kwargs)
    return decorated_function


@theme_bp.route('/info', methods=['GET'])
def theme_info():
    """Get theme API information."""
    return jsonify({
        'success': True,
        'data': {
            'name': 'Theme Management API',
            'version': '2.0.0',
            'endpoints': {
                'active': '/api/admin/theme/active',
                'list': '/api/admin/theme/list',
                'create': '/api/admin/theme/create (POST)',
                'setting': '/api/admin/theme/setting (PUT)',
                'generate_css': '/api/admin/theme/generate-css (POST)',
                'activate': '/api/admin/theme/activate (POST)',
                'preview': '/api/admin/theme/preview (POST)',
                'export': '/api/admin/theme/export',
                'import': '/api/admin/theme/import (POST)'
            }
        }
    })


@theme_bp.route('/current', methods=['GET'])
def get_current_theme():
    """Get the currently active theme (alias for /active)."""
    try:
        theme_manager = current_app.theme_manager
        theme = theme_manager.get_active_theme()
        
        return jsonify({
            'success': True,
            'data': {
                'theme': theme
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@theme_bp.route('/active', methods=['GET'])
def get_active_theme():
    """Get the currently active theme."""
    try:
        theme_manager = current_app.theme_manager
        theme = theme_manager.get_active_theme()
        
        return jsonify({
            'success': True,
            'data': theme
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@theme_bp.route('/list', methods=['GET'])
def list_themes():
    """List all available themes."""
    try:
        theme_manager = current_app.theme_manager
        themes = theme_manager.list_themes()
        
        return jsonify({
            'success': True,
            'data': themes
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@theme_bp.route('/setting', methods=['PUT'])
@login_required
@admin_required
def update_theme_setting():
    """Update a theme setting."""
    try:
        data = request.get_json()
        if not data or 'property' not in data or 'value' not in data:
            return jsonify({
                'success': False,
                'error': 'Property and value are required'
            }), 400
        
        theme_manager = current_app.theme_manager
        result = theme_manager.update_theme_setting(
            data['property'], 
            data['value'], 
            current_user.id
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@theme_bp.route('/generate-css', methods=['POST'])
@login_required
@admin_required
def generate_css():
    """Generate CSS from current theme configuration."""
    try:
        theme_manager = current_app.theme_manager
        result = theme_manager.generate_css()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@theme_bp.route('/preview', methods=['POST'])
@login_required
@admin_required
def preview_theme():
    """Generate a preview of a theme with custom settings."""
    try:
        data = request.get_json()
        theme_id = data.get('theme_id', 'default')
        custom_settings = data.get('settings', {})
        
        theme_manager = current_app.theme_manager
        result = theme_manager.preview_theme(theme_id, custom_settings)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@theme_bp.route('/activate', methods=['POST'])
@login_required
@admin_required
def activate_theme():
    """Activate a theme."""
    try:
        data = request.get_json()
        if not data or 'theme_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Theme ID is required'
            }), 400
        
        theme_manager = current_app.theme_manager
        result = theme_manager.activate_theme(data['theme_id'], current_user.id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@theme_bp.route('/export', methods=['GET'])
@login_required
@admin_required
def export_theme():
    """Export theme configuration."""
    try:
        theme_id = request.args.get('theme_id')
        
        theme_manager = current_app.theme_manager
        result = theme_manager.export_theme(theme_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['data']
            })
        else:
            return jsonify(result), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@theme_bp.route('/create', methods=['POST'])
@login_required
@admin_required
def create_theme():
    """Create a new custom theme."""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({
                'success': False,
                'error': 'Theme name is required'
            }), 400
        
        theme_name = data['name']
        theme_id = theme_name.lower().replace(' ', '_').replace('-', '_')
        
        # Get base settings (default or from another theme)
        base_theme = data.get('base_theme', 'default')
        theme_manager = current_app.theme_manager
        
        if base_theme == 'default':
            base_settings = theme_manager._get_default_theme_settings()
        elif base_theme == 'dark':
            base_settings = theme_manager._get_dark_theme_settings()
        elif base_theme == 'minimal':
            base_settings = theme_manager._get_minimal_theme_settings()
        else:
            base_settings = theme_manager._get_default_theme_settings()
        
        # Override with custom settings
        custom_settings = data.get('settings', {})
        base_settings.update(custom_settings)
        base_settings['name'] = theme_name
        
        # Save theme settings to database
        saved_count = 0
        errors = []
        
        for property, value in base_settings.items():
            if property != 'name':  # Skip name as it's not a CSS property
                setting_key = f'theme_{theme_id}_{property}'
                
                # Validate the property
                validation = theme_manager._validate_theme_property(property, str(value))
                if not validation['valid']:
                    errors.append(f"{property}: {validation['error']}")
                    continue
                
                # Save setting
                setting = AdminSetting.query.filter_by(key=setting_key).first()
                if setting:
                    setting.set_value(str(value))
                    setting.updated_at = datetime.now(timezone.utc)
                    setting.updated_by = current_user.id
                else:
                    setting = AdminSetting(
                        key=setting_key,
                        category='theme',
                        description=f'Custom theme {theme_name} - {property}',
                        data_type='string',
                        updated_by=current_user.id
                    )
                    setting.set_value(str(value))
                    db.session.add(setting)
                
                saved_count += 1
        
        # Save theme metadata
        theme_meta_setting = AdminSetting(
            key=f'theme_{theme_id}_meta',
            category='theme',
            description=f'Metadata for custom theme: {theme_name}',
            data_type='json',
            updated_by=current_user.id
        )
        theme_meta_setting.set_value(json.dumps({
            'name': theme_name,
            'id': theme_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'created_by': current_user.id,
            'base_theme': base_theme,
            'is_custom': True
        }))
        db.session.add(theme_meta_setting)
        
        db.session.commit()
        
        # Generate preview CSS
        theme_config = {
            'id': theme_id,
            'name': theme_name,
            'settings': base_settings,
            'is_active': False
        }
        
        css_result = theme_manager.generate_css(theme_config)
        
        return jsonify({
            'success': True,
            'data': {
                'theme': {
                    'id': theme_id,
                    'name': theme_name,
                    'base_theme': base_theme,
                    'settings_saved': saved_count,
                    'errors': errors,
                    'is_custom': True
                }
            },
            'message': f'Custom theme "{theme_name}" created successfully',
            'css_generated': css_result['success']
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@theme_bp.route('/import', methods=['POST'])
@login_required
@admin_required
def import_theme():
    """Import theme configuration."""
    try:
        data = request.get_json()
        if not data or 'theme_data' not in data:
            return jsonify({
                'success': False,
                'error': 'Theme data is required'
            }), 400
        
        theme_manager = current_app.theme_manager
        result = theme_manager.import_theme(data['theme_data'], current_user.id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500