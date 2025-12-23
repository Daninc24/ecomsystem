"""
Configuration Management API endpoints
"""

from flask import Blueprint, request, jsonify
from .base_api import admin_api_required, validate_json_request, handle_api_errors, success_response, error_response, get_current_user_id

configuration_bp = Blueprint('admin_configuration', __name__, url_prefix='/admin/api/configuration')


@configuration_bp.route('/settings', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_all_settings():
    """Get all configuration settings."""
    from ..services.configuration_manager import ConfigurationManager
    from simple_mongo_mock import mock_mongo
    
    config_manager = ConfigurationManager(mock_mongo.db)
    
    category = request.args.get('category')
    settings = config_manager.get_all_settings(category)
    
    return jsonify(success_response(settings))


@configuration_bp.route('/settings/<key>', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_setting(key):
    """Get a specific configuration setting."""
    from ..services.configuration_manager import ConfigurationManager
    from simple_mongo_mock import mock_mongo
    
    config_manager = ConfigurationManager(mock_mongo.db)
    value = config_manager.get_setting(key)
    
    if value is None:
        return error_response(f"Setting '{key}' not found", 'SETTING_NOT_FOUND', 404)
    
    return jsonify(success_response({'key': key, 'value': value}))


@configuration_bp.route('/settings/<key>', methods=['PUT'])
@admin_api_required
@validate_json_request(['value'])
@handle_api_errors
def update_setting(key):
    """Update a configuration setting."""
    from ..services.configuration_manager import ConfigurationManager
    from simple_mongo_mock import mock_mongo
    
    config_manager = ConfigurationManager(mock_mongo.db)
    data = request.get_json()
    user_id = get_current_user_id()
    
    try:
        success = config_manager.update_setting(key, data['value'], user_id)
        if success:
            return jsonify(success_response(message=f"Setting '{key}' updated successfully"))
        else:
            return error_response(f"Setting '{key}' not found", 'SETTING_NOT_FOUND', 404)
    except ValueError as e:
        return error_response(str(e), 'VALIDATION_ERROR', 400)


@configuration_bp.route('/settings', methods=['POST'])
@admin_api_required
@validate_json_request(['key', 'value'])
@handle_api_errors
def create_setting():
    """Create a new configuration setting."""
    from ..services.configuration_manager import ConfigurationManager
    from simple_mongo_mock import mock_mongo
    
    config_manager = ConfigurationManager(mock_mongo.db)
    data = request.get_json()
    user_id = get_current_user_id()
    
    try:
        setting_id = config_manager.create_setting(
            key=data['key'],
            value=data['value'],
            category=data.get('category', 'general'),
            description=data.get('description', ''),
            validation_rules=data.get('validation_rules', {}),
            is_sensitive=data.get('is_sensitive', False),
            user_id=user_id
        )
        
        return jsonify(success_response(
            {'id': str(setting_id)},
            f"Setting '{data['key']}' created successfully"
        )), 201
    
    except ValueError as e:
        return error_response(str(e), 'VALIDATION_ERROR', 400)


@configuration_bp.route('/settings/<key>/validate', methods=['POST'])
@admin_api_required
@validate_json_request(['value'])
@handle_api_errors
def validate_setting(key):
    """Validate a configuration setting value."""
    from ..services.configuration_manager import ConfigurationManager
    from simple_mongo_mock import mock_mongo
    
    config_manager = ConfigurationManager(mock_mongo.db)
    data = request.get_json()
    
    validation_result = config_manager.validate_setting(key, data['value'])
    
    return jsonify(success_response({
        'is_valid': validation_result.is_valid,
        'error_message': validation_result.error_message
    }))


@configuration_bp.route('/cache/clear', methods=['POST'])
@admin_api_required
@handle_api_errors
def clear_cache():
    """Clear the configuration cache."""
    from ..services.configuration_manager import ConfigurationManager
    from simple_mongo_mock import mock_mongo
    
    config_manager = ConfigurationManager(mock_mongo.db)
    cleared_count = config_manager.clear_cache()
    
    return jsonify(success_response(
        {'cleared_count': cleared_count},
        f"Cleared {cleared_count} cached entries"
    ))