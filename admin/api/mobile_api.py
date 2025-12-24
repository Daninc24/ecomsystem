"""
Mobile Admin API Endpoints
Provides REST API endpoints for mobile admin interface functionality
"""

from flask import Blueprint, request, jsonify, session
from bson import ObjectId
from datetime import datetime
from typing import Dict, Any, List

from .base_api import admin_api_required, validate_json_request, handle_api_errors, success_response, error_response, get_current_user_id
from ..services.mobile_interface_manager import MobileInterfaceManager
from ..services.mobile_content_editor import MobileContentEditor
from ..database.collections import get_admin_db


mobile_api = Blueprint('mobile_api', __name__, url_prefix='/api/admin/mobile')


@mobile_api.route('/dashboard/config', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_mobile_dashboard_config():
    """Get mobile dashboard configuration for current user."""
    user_id = get_current_user_id()
    if not user_id:
        return error_response('User not authenticated', 'AUTH_ERROR', 401)
    
    db = get_admin_db()
    mobile_manager = MobileInterfaceManager(db)
    
    config = mobile_manager.get_mobile_dashboard_config(user_id)
    return jsonify(success_response(config))


@mobile_api.route('/dashboard/config', methods=['POST'])
@admin_api_required
@validate_json_request(['layout', 'widgets'])
@handle_api_errors
def update_mobile_dashboard_config():
    """Update mobile dashboard configuration for current user."""
    user_id = get_current_user_id()
    if not user_id:
        return error_response('User not authenticated', 'AUTH_ERROR', 401)
    
    data = request.get_json()
    
    db = get_admin_db()
    mobile_manager = MobileInterfaceManager(db)
    
    success = mobile_manager.update_mobile_dashboard_config(user_id, data)
    
    if success:
        return jsonify(success_response(message='Dashboard configuration updated'))
    else:
        return error_response('Failed to update dashboard configuration', 'UPDATE_ERROR')


@mobile_api.route('/touch-settings', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_touch_settings():
    """Get touch interface settings."""
    db = get_admin_db()
    mobile_manager = MobileInterfaceManager(db)
    
    settings = mobile_manager.get_touch_interface_settings()
    return jsonify(success_response(settings))


@mobile_api.route('/layout/<screen_size>', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_mobile_layout(screen_size: str):
    """Get mobile layout configuration for specific screen size."""
    if screen_size not in ['small', 'medium', 'large']:
        return error_response('Invalid screen size', 'INVALID_SCREEN_SIZE')
    
    db = get_admin_db()
    mobile_manager = MobileInterfaceManager(db)
    
    layout = mobile_manager.get_mobile_layout_config(screen_size)
    return jsonify(success_response(layout))


@mobile_api.route('/notifications', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_mobile_notifications():
    """Get mobile notifications for current user."""
    user_id = get_current_user_id()
    if not user_id:
        return error_response('User not authenticated', 'AUTH_ERROR', 401)
    
    limit = request.args.get('limit', 20, type=int)
    
    db = get_admin_db()
    mobile_manager = MobileInterfaceManager(db)
    
    notifications = mobile_manager.get_mobile_notifications(user_id, limit)
    
    # Convert ObjectId to string for JSON serialization
    for notification in notifications:
        notification['_id'] = str(notification['_id'])
        notification['user_id'] = str(notification['user_id'])
    
    return jsonify(success_response(notifications))


@mobile_api.route('/notifications', methods=['POST'])
@admin_api_required
@validate_json_request(['title', 'message'])
@handle_api_errors
def create_mobile_notification():
    """Create a new mobile notification."""
    user_id = get_current_user_id()
    if not user_id:
        return error_response('User not authenticated', 'AUTH_ERROR', 401)
    
    data = request.get_json()
    
    db = get_admin_db()
    mobile_manager = MobileInterfaceManager(db)
    
    notification_id = mobile_manager.create_push_notification(user_id, data)
    
    return jsonify(success_response({
        'notification_id': str(notification_id)
    }, 'Notification created successfully'))


@mobile_api.route('/notifications/<notification_id>/read', methods=['POST'])
@admin_api_required
@handle_api_errors
def mark_notification_read(notification_id: str):
    """Mark a notification as read."""
    user_id = get_current_user_id()
    if not user_id:
        return error_response('User not authenticated', 'AUTH_ERROR', 401)
    
    try:
        notification_obj_id = ObjectId(notification_id)
    except:
        return error_response('Invalid notification ID', 'INVALID_ID')
    
    db = get_admin_db()
    mobile_manager = MobileInterfaceManager(db)
    
    success = mobile_manager.mark_notification_read(notification_obj_id, user_id)
    
    if success:
        return jsonify(success_response(message='Notification marked as read'))
    else:
        return error_response('Failed to mark notification as read', 'UPDATE_ERROR')


@mobile_api.route('/quick-actions', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_mobile_quick_actions():
    """Get quick actions for mobile interface."""
    user_role = session.get('user_role', 'admin')
    
    db = get_admin_db()
    mobile_manager = MobileInterfaceManager(db)
    
    actions = mobile_manager.get_mobile_quick_actions(user_role)
    return jsonify(success_response(actions))


@mobile_api.route('/content/optimize', methods=['POST'])
@admin_api_required
@validate_json_request(['content', 'screen_size'])
@handle_api_errors
def optimize_content_for_mobile():
    """Optimize content for mobile display."""
    data = request.get_json()
    content = data['content']
    screen_size = data['screen_size']
    
    db = get_admin_db()
    mobile_manager = MobileInterfaceManager(db)
    
    optimized = mobile_manager.optimize_content_for_mobile(content, screen_size)
    return jsonify(success_response(optimized))


@mobile_api.route('/validate-compatibility', methods=['POST'])
@admin_api_required
@validate_json_request(['component_config'])
@handle_api_errors
def validate_mobile_compatibility():
    """Validate component configuration for mobile compatibility."""
    data = request.get_json()
    component_config = data['component_config']
    
    db = get_admin_db()
    mobile_manager = MobileInterfaceManager(db)
    
    validation_result = mobile_manager.validate_mobile_compatibility(component_config)
    return jsonify(success_response(validation_result))


# ==================== MOBILE CONTENT EDITOR ENDPOINTS ====================

@mobile_api.route('/editor/session', methods=['POST'])
@admin_api_required
@validate_json_request(['content_id', 'content_type'])
@handle_api_errors
def create_editing_session():
    """Create a new mobile editing session."""
    user_id = get_current_user_id()
    if not user_id:
        return error_response('User not authenticated', 'AUTH_ERROR', 401)
    
    data = request.get_json()
    content_id = data['content_id']
    content_type = data['content_type']
    
    db = get_admin_db()
    editor = MobileContentEditor(db)
    
    session_id = editor.create_editing_session(user_id, content_id, content_type)
    
    return jsonify(success_response({
        'session_id': str(session_id)
    }, 'Editing session created'))


@mobile_api.route('/editor/session/<session_id>/draft', methods=['POST'])
@admin_api_required
@validate_json_request(['content'])
@handle_api_errors
def save_content_draft(session_id: str):
    """Save content draft for a mobile editing session."""
    try:
        session_obj_id = ObjectId(session_id)
    except:
        return error_response('Invalid session ID', 'INVALID_ID')
    
    data = request.get_json()
    content = data['content']
    metadata = data.get('metadata', {})
    
    db = get_admin_db()
    editor = MobileContentEditor(db)
    
    draft_id = editor.save_content_draft(session_obj_id, content, metadata)
    
    return jsonify(success_response({
        'draft_id': str(draft_id)
    }, 'Draft saved'))


@mobile_api.route('/editor/session/<session_id>/draft', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_content_draft(session_id: str):
    """Get the latest content draft for a session."""
    try:
        session_obj_id = ObjectId(session_id)
    except:
        return error_response('Invalid session ID', 'INVALID_ID')
    
    db = get_admin_db()
    editor = MobileContentEditor(db)
    
    draft = editor.get_content_draft(session_obj_id)
    
    if draft:
        draft['_id'] = str(draft['_id'])
        draft['session_id'] = str(draft['session_id'])
        return jsonify(success_response(draft))
    else:
        return error_response('No draft found', 'NOT_FOUND', 404)


@mobile_api.route('/editor/session/<session_id>/history', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_content_history(session_id: str):
    """Get content editing history for a session."""
    try:
        session_obj_id = ObjectId(session_id)
    except:
        return error_response('Invalid session ID', 'INVALID_ID')
    
    limit = request.args.get('limit', 10, type=int)
    
    db = get_admin_db()
    editor = MobileContentEditor(db)
    
    history = editor.get_content_history(session_obj_id, limit)
    
    # Convert ObjectIds to strings
    for item in history:
        item['_id'] = str(item['_id'])
        item['session_id'] = str(item['session_id'])
    
    return jsonify(success_response(history))


@mobile_api.route('/editor/optimize-content', methods=['POST'])
@admin_api_required
@validate_json_request(['content', 'content_type'])
@handle_api_errors
def optimize_content_for_editing():
    """Optimize content for mobile editing."""
    data = request.get_json()
    content = data['content']
    content_type = data['content_type']
    
    db = get_admin_db()
    editor = MobileContentEditor(db)
    
    optimized = editor.optimize_content_for_mobile(content, content_type)
    return jsonify(success_response(optimized))


@mobile_api.route('/editor/toolbar/<content_type>', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_mobile_editor_toolbar(content_type: str):
    """Get mobile editor toolbar configuration."""
    user_id = get_current_user_id()
    
    db = get_admin_db()
    editor = MobileContentEditor(db)
    
    # Get user preferences if available
    user_preferences = {}
    if user_id:
        settings = editor.get_mobile_editor_settings(user_id)
        user_preferences = settings.get('toolbar_preferences', {})
    
    toolbar = editor.get_mobile_editor_toolbar(content_type, user_preferences)
    return jsonify(success_response(toolbar))


@mobile_api.route('/editor/gesture', methods=['POST'])
@admin_api_required
@validate_json_request(['session_id', 'gesture_type'])
@handle_api_errors
def handle_touch_gesture():
    """Handle touch gesture in mobile editor."""
    data = request.get_json()
    
    try:
        session_id = ObjectId(data['session_id'])
    except:
        return error_response('Invalid session ID', 'INVALID_ID')
    
    gesture_type = data['gesture_type']
    gesture_data = data.get('gesture_data', {})
    
    db = get_admin_db()
    editor = MobileContentEditor(db)
    
    result = editor.handle_touch_gesture(session_id, gesture_type, gesture_data)
    return jsonify(success_response(result))


@mobile_api.route('/editor/settings', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_mobile_editor_settings():
    """Get mobile editor settings for current user."""
    user_id = get_current_user_id()
    if not user_id:
        return error_response('User not authenticated', 'AUTH_ERROR', 401)
    
    db = get_admin_db()
    editor = MobileContentEditor(db)
    
    settings = editor.get_mobile_editor_settings(user_id)
    settings['_id'] = str(settings['_id'])
    settings['user_id'] = str(settings['user_id'])
    
    return jsonify(success_response(settings))


@mobile_api.route('/editor/settings', methods=['POST'])
@admin_api_required
@validate_json_request()
@handle_api_errors
def update_mobile_editor_settings():
    """Update mobile editor settings for current user."""
    user_id = get_current_user_id()
    if not user_id:
        return error_response('User not authenticated', 'AUTH_ERROR', 401)
    
    data = request.get_json()
    
    db = get_admin_db()
    editor = MobileContentEditor(db)
    
    success = editor.update_mobile_editor_settings(user_id, data)
    
    if success:
        return jsonify(success_response(message='Settings updated'))
    else:
        return error_response('Failed to update settings', 'UPDATE_ERROR')


@mobile_api.route('/editor/session/<session_id>/close', methods=['POST'])
@admin_api_required
@handle_api_errors
def close_editing_session(session_id: str):
    """Close a mobile editing session."""
    try:
        session_obj_id = ObjectId(session_id)
    except:
        return error_response('Invalid session ID', 'INVALID_ID')
    
    data = request.get_json() or {}
    save_final_draft = data.get('save_final_draft', True)
    
    db = get_admin_db()
    editor = MobileContentEditor(db)
    
    success = editor.close_editing_session(session_obj_id, save_final_draft)
    
    if success:
        return jsonify(success_response(message='Session closed'))
    else:
        return error_response('Failed to close session', 'CLOSE_ERROR')


@mobile_api.route('/editor/analytics', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_mobile_editing_analytics():
    """Get mobile editing analytics for current user."""
    user_id = get_current_user_id()
    if not user_id:
        return error_response('User not authenticated', 'AUTH_ERROR', 401)
    
    days = request.args.get('days', 30, type=int)
    
    db = get_admin_db()
    editor = MobileContentEditor(db)
    
    analytics = editor.get_mobile_editing_analytics(user_id, days)
    return jsonify(success_response(analytics))


# ==================== PUSH NOTIFICATION ENDPOINTS ====================

@mobile_api.route('/push-subscription', methods=['POST'])
@admin_api_required
@validate_json_request(['endpoint'])
@handle_api_errors
def save_push_subscription():
    """Save push notification subscription."""
    user_id = get_current_user_id()
    if not user_id:
        return error_response('User not authenticated', 'AUTH_ERROR', 401)
    
    subscription_data = request.get_json()
    
    # In a real implementation, you would save this to the database
    # and use it to send push notifications via FCM/APNs
    
    db = get_admin_db()
    db.push_subscriptions.update_one(
        {'user_id': user_id},
        {
            '$set': {
                'subscription': subscription_data,
                'updated_at': datetime.utcnow()
            }
        },
        upsert=True
    )
    
    return jsonify(success_response(message='Push subscription saved'))


@mobile_api.route('/sync-offline-data', methods=['POST'])
@admin_api_required
@validate_json_request()
@handle_api_errors
def sync_offline_data():
    """Sync offline data when connection is restored."""
    user_id = get_current_user_id()
    if not user_id:
        return error_response('User not authenticated', 'AUTH_ERROR', 401)
    
    offline_data = request.get_json()
    
    # Process offline data
    processed_count = 0
    errors = []
    
    for item in offline_data:
        try:
            # Process each offline data item
            # This would depend on the type of data being synced
            processed_count += 1
        except Exception as e:
            errors.append(str(e))
    
    return jsonify(success_response({
        'processed_count': processed_count,
        'errors': errors
    }, 'Offline data synced'))


# Register the blueprint
def register_mobile_api(app):
    """Register mobile API blueprint with Flask app."""
    app.register_blueprint(mobile_api)