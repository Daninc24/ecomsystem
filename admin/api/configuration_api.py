"""
Configuration Management API endpoints - SQLite version
"""

from flask import Blueprint, request, jsonify, current_app
from models_sqlite import db

configuration_bp = Blueprint('admin_configuration', __name__, url_prefix='/configuration')


@configuration_bp.route('/', methods=['GET'])
def configuration_info():
    """Get configuration API information."""
    return jsonify({
        'success': True,
        'data': {
            'name': 'Configuration Management API',
            'version': '2.0.0',
            'endpoints': {
                'settings': '/api/admin/configuration/settings',
                'setting': '/api/admin/configuration/settings/<key>',
                'update_setting': '/api/admin/configuration/settings/<key> (PUT)'
            }
        }
    })


@configuration_bp.route('/dashboard-widgets', methods=['GET'])
def get_dashboard_widgets():
    """Get dashboard widget configuration."""
    try:
        # Return default widget configuration
        widgets = [
            {
                'id': 'stats',
                'type': 'stats',
                'title': 'Statistics',
                'position': {'x': 0, 'y': 0, 'w': 6, 'h': 2}
            },
            {
                'id': 'recent_orders',
                'type': 'orders',
                'title': 'Recent Orders',
                'position': {'x': 6, 'y': 0, 'w': 6, 'h': 4}
            },
            {
                'id': 'analytics_chart',
                'type': 'chart',
                'title': 'Analytics',
                'position': {'x': 0, 'y': 2, 'w': 6, 'h': 4}
            }
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'widgets': widgets
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@configuration_bp.route('/dashboard-layout', methods=['POST'])
def update_dashboard_layout():
    """Update dashboard widget layout."""
    try:
        data = request.get_json()
        widget_id = data.get('widget_id')
        from_index = data.get('from_index')
        to_index = data.get('to_index')
        
        # For now, just return success
        # In a real implementation, you'd save the layout
        
        return jsonify({
            'success': True,
            'message': 'Dashboard layout updated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@configuration_bp.route('/settings', methods=['GET'])
def get_all_settings():
    """Get all configuration settings."""
    try:
        config_manager = current_app.config_manager
        settings = config_manager.get_all_settings()
        
        return jsonify({
            'success': True,
            'data': settings
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@configuration_bp.route('/settings/<key>', methods=['GET'])
def get_setting(key):
    """Get a specific configuration setting."""
    try:
        config_manager = current_app.config_manager
        value = config_manager.get_setting(key)
        
        if value is not None:
            return jsonify({
                'success': True,
                'data': {
                    'key': key,
                    'value': value
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Setting not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@configuration_bp.route('/settings/<key>', methods=['PUT'])
def update_setting(key):
    """Update a configuration setting."""
    try:
        data = request.get_json()
        if not data or 'value' not in data:
            return jsonify({
                'success': False,
                'error': 'Value is required'
            }), 400
        
        config_manager = current_app.config_manager
        success = config_manager.update_setting(key, data['value'])
        
        if success:
            return jsonify({
                'success': True,
                'data': {
                    'key': key,
                    'value': data['value']
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update setting'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500