"""
User Management API endpoints for the dynamic admin system
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from bson import ObjectId
from flask import Blueprint, request, jsonify, session

from .base_api import admin_api_required, validate_json_request, handle_api_errors, success_response, error_response, get_current_user_id


user_bp = Blueprint('user_api', __name__, url_prefix='/api/admin/users')


@user_bp.route('/', methods=['GET'])
@admin_api_required
@handle_api_errors
def list_users():
    """List all users with pagination and filtering."""
    from ..services.user_manager import UserManager
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    user_manager = UserManager(db)
    
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    role = request.args.get('role')
    status = request.args.get('status')
    search = request.args.get('search')
    
    users = user_manager.list_users(page, limit, role, status, search)
    
    # Convert ObjectIds to strings and remove sensitive data
    for user in users['items']:
        user['_id'] = str(user['_id'])
        if 'password_hash' in user:
            del user['password_hash']
    
    return jsonify(success_response(users))


@user_bp.route('/<user_id>', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_user(user_id):
    """Get a specific user by ID."""
    from ..services.user_manager import UserManager
    from ..database.collections import get_admin_db
    
    try:
        user_obj_id = ObjectId(user_id)
    except:
        return error_response('Invalid user ID', 'INVALID_ID')
    
    db = get_admin_db()
    user_manager = UserManager(db)
    
    user = user_manager.get_user(user_obj_id)
    
    if not user:
        return error_response('User not found', 'NOT_FOUND', 404)
    
    user['_id'] = str(user['_id'])
    if 'password_hash' in user:
        del user['password_hash']
    
    return jsonify(success_response(user))


@user_bp.route('/', methods=['POST'])
@admin_api_required
@validate_json_request(['email', 'password', 'role'])
@handle_api_errors
def create_user():
    """Create a new user account."""
    from ..services.user_manager import UserManager
    from ..database.collections import get_admin_db
    
    data = request.get_json()
    admin_user_id = get_current_user_id()
    
    db = get_admin_db()
    user_manager = UserManager(db)
    
    try:
        user_id = user_manager.create_user(
            email=data['email'],
            password=data['password'],
            role=data['role'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            profile_data=data.get('profile_data', {}),
            admin_user_id=admin_user_id
        )
        
        return jsonify(success_response(
            {'id': str(user_id)},
            'User created successfully'
        )), 201
    
    except ValueError as e:
        return error_response(str(e), 'VALIDATION_ERROR')


@user_bp.route('/<user_id>', methods=['PUT'])
@admin_api_required
@handle_api_errors
def update_user(user_id):
    """Update user information."""
    from ..services.user_manager import UserManager
    from ..database.collections import get_admin_db
    
    try:
        user_obj_id = ObjectId(user_id)
    except:
        return error_response('Invalid user ID', 'INVALID_ID')
    
    data = request.get_json()
    admin_user_id = get_current_user_id()
    
    db = get_admin_db()
    user_manager = UserManager(db)
    
    success = user_manager.update_user(user_obj_id, data, admin_user_id)
    
    if success:
        return jsonify(success_response(message='User updated successfully'))
    else:
        return error_response('User not found', 'NOT_FOUND', 404)


@user_bp.route('/<user_id>/permissions', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_user_permissions(user_id):
    """Get user permissions."""
    from ..services.permission_engine import PermissionEngine
    from ..database.collections import get_admin_db
    
    try:
        user_obj_id = ObjectId(user_id)
    except:
        return error_response('Invalid user ID', 'INVALID_ID')
    
    db = get_admin_db()
    permission_engine = PermissionEngine(db)
    
    permissions = permission_engine.get_user_permissions(user_obj_id)
    
    return jsonify(success_response(permissions))


@user_bp.route('/<user_id>/permissions', methods=['PUT'])
@admin_api_required
@validate_json_request(['permissions'])
@handle_api_errors
def update_user_permissions(user_id):
    """Update user permissions."""
    from ..services.permission_engine import PermissionEngine
    from ..database.collections import get_admin_db
    
    try:
        user_obj_id = ObjectId(user_id)
    except:
        return error_response('Invalid user ID', 'INVALID_ID')
    
    data = request.get_json()
    permissions = data['permissions']
    admin_user_id = get_current_user_id()
    
    db = get_admin_db()
    permission_engine = PermissionEngine(db)
    
    success = permission_engine.update_user_permissions(user_obj_id, permissions, admin_user_id)
    
    if success:
        return jsonify(success_response(message='User permissions updated successfully'))
    else:
        return error_response('User not found', 'NOT_FOUND', 404)


@user_bp.route('/<user_id>/suspend', methods=['POST'])
@admin_api_required
@validate_json_request(['reason'])
@handle_api_errors
def suspend_user(user_id):
    """Suspend a user account."""
    from ..services.user_manager import UserManager
    from ..database.collections import get_admin_db
    
    try:
        user_obj_id = ObjectId(user_id)
    except:
        return error_response('Invalid user ID', 'INVALID_ID')
    
    data = request.get_json()
    reason = data['reason']
    admin_user_id = get_current_user_id()
    
    db = get_admin_db()
    user_manager = UserManager(db)
    
    success = user_manager.suspend_user(user_obj_id, reason, admin_user_id)
    
    if success:
        return jsonify(success_response(message='User suspended successfully'))
    else:
        return error_response('User not found', 'NOT_FOUND', 404)


@user_bp.route('/<user_id>/activate', methods=['POST'])
@admin_api_required
@handle_api_errors
def activate_user(user_id):
    """Activate a suspended user account."""
    from ..services.user_manager import UserManager
    from ..database.collections import get_admin_db
    
    try:
        user_obj_id = ObjectId(user_id)
    except:
        return error_response('Invalid user ID', 'INVALID_ID')
    
    admin_user_id = get_current_user_id()
    
    db = get_admin_db()
    user_manager = UserManager(db)
    
    success = user_manager.activate_user(user_obj_id, admin_user_id)
    
    if success:
        return jsonify(success_response(message='User activated successfully'))
    else:
        return error_response('User not found', 'NOT_FOUND', 404)


@user_bp.route('/<user_id>/activity', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_user_activity(user_id):
    """Get user activity log."""
    from ..services.audit_logger import AuditLogger
    from ..database.collections import get_admin_db
    
    try:
        user_obj_id = ObjectId(user_id)
    except:
        return error_response('Invalid user ID', 'INVALID_ID')
    
    db = get_admin_db()
    audit_logger = AuditLogger(db)
    
    limit = request.args.get('limit', 50, type=int)
    activity_logs = audit_logger.get_user_activity(user_obj_id, limit)
    
    # Convert ObjectIds to strings
    for log in activity_logs:
        log['_id'] = str(log['_id'])
        log['user_id'] = str(log['user_id'])
    
    return jsonify(success_response(activity_logs))


@user_bp.route('/vendors/applications', methods=['GET'])
@admin_api_required
@handle_api_errors
def list_vendor_applications():
    """List vendor applications."""
    from ..services.vendor_approval_workflow import VendorApprovalWorkflow
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    vendor_workflow = VendorApprovalWorkflow(db)
    
    status = request.args.get('status')  # pending, approved, rejected
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    applications = vendor_workflow.list_vendor_applications(status, page, limit)
    
    # Convert ObjectIds to strings
    for app in applications['items']:
        app['_id'] = str(app['_id'])
        app['user_id'] = str(app['user_id'])
    
    return jsonify(success_response(applications))


@user_bp.route('/vendors/applications/<application_id>', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_vendor_application(application_id):
    """Get vendor application details."""
    from ..services.vendor_approval_workflow import VendorApprovalWorkflow
    from ..database.collections import get_admin_db
    
    try:
        app_obj_id = ObjectId(application_id)
    except:
        return error_response('Invalid application ID', 'INVALID_ID')
    
    db = get_admin_db()
    vendor_workflow = VendorApprovalWorkflow(db)
    
    application = vendor_workflow.get_vendor_application(app_obj_id)
    
    if not application:
        return error_response('Application not found', 'NOT_FOUND', 404)
    
    application['_id'] = str(application['_id'])
    application['user_id'] = str(application['user_id'])
    
    return jsonify(success_response(application))


@user_bp.route('/vendors/applications/<application_id>/approve', methods=['POST'])
@admin_api_required
@handle_api_errors
def approve_vendor_application(application_id):
    """Approve a vendor application."""
    from ..services.vendor_approval_workflow import VendorApprovalWorkflow
    from ..database.collections import get_admin_db
    
    try:
        app_obj_id = ObjectId(application_id)
    except:
        return error_response('Invalid application ID', 'INVALID_ID')
    
    data = request.get_json() or {}
    notes = data.get('notes', '')
    admin_user_id = get_current_user_id()
    
    db = get_admin_db()
    vendor_workflow = VendorApprovalWorkflow(db)
    
    success = vendor_workflow.approve_vendor_application(app_obj_id, notes, admin_user_id)
    
    if success:
        return jsonify(success_response(message='Vendor application approved'))
    else:
        return error_response('Application not found', 'NOT_FOUND', 404)


@user_bp.route('/vendors/applications/<application_id>/reject', methods=['POST'])
@admin_api_required
@validate_json_request(['reason'])
@handle_api_errors
def reject_vendor_application(application_id):
    """Reject a vendor application."""
    from ..services.vendor_approval_workflow import VendorApprovalWorkflow
    from ..database.collections import get_admin_db
    
    try:
        app_obj_id = ObjectId(application_id)
    except:
        return error_response('Invalid application ID', 'INVALID_ID')
    
    data = request.get_json()
    reason = data['reason']
    admin_user_id = get_current_user_id()
    
    db = get_admin_db()
    vendor_workflow = VendorApprovalWorkflow(db)
    
    success = vendor_workflow.reject_vendor_application(app_obj_id, reason, admin_user_id)
    
    if success:
        return jsonify(success_response(message='Vendor application rejected'))
    else:
        return error_response('Application not found', 'NOT_FOUND', 404)


@user_bp.route('/roles', methods=['GET'])
@admin_api_required
@handle_api_errors
def list_roles():
    """List all available user roles."""
    from ..services.permission_engine import PermissionEngine
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    permission_engine = PermissionEngine(db)
    
    roles = permission_engine.list_roles()
    
    # Convert ObjectIds to strings
    for role in roles:
        role['_id'] = str(role['_id'])
    
    return jsonify(success_response(roles))


@user_bp.route('/bulk/update', methods=['POST'])
@admin_api_required
@validate_json_request(['user_ids', 'updates'])
@handle_api_errors
def bulk_update_users():
    """Bulk update multiple users."""
    from ..services.bulk_operation_handler import BulkOperationHandler
    from ..database.collections import get_admin_db
    
    data = request.get_json()
    user_ids = data['user_ids']
    updates = data['updates']
    admin_user_id = get_current_user_id()
    
    # Convert string IDs to ObjectIds
    try:
        user_obj_ids = [ObjectId(uid) for uid in user_ids]
    except:
        return error_response('Invalid user IDs', 'INVALID_ID')
    
    db = get_admin_db()
    bulk_handler = BulkOperationHandler(db)
    
    result = bulk_handler.bulk_update_users(user_obj_ids, updates, admin_user_id)
    
    return jsonify(success_response(result))


@user_bp.route('/sessions', methods=['GET'])
@admin_api_required
@handle_api_errors
def list_active_sessions():
    """List active user sessions."""
    from ..services.authentication_manager import AuthenticationManager
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    auth_manager = AuthenticationManager(db)
    
    limit = request.args.get('limit', 50, type=int)
    sessions = auth_manager.list_active_sessions(limit)
    
    # Convert ObjectIds to strings
    for session in sessions:
        session['_id'] = str(session['_id'])
        session['user_id'] = str(session['user_id'])
    
    return jsonify(success_response(sessions))


@user_bp.route('/sessions/<session_id>/terminate', methods=['POST'])
@admin_api_required
@handle_api_errors
def terminate_session(session_id):
    """Terminate a user session."""
    from ..services.authentication_manager import AuthenticationManager
    from ..database.collections import get_admin_db
    
    try:
        session_obj_id = ObjectId(session_id)
    except:
        return error_response('Invalid session ID', 'INVALID_ID')
    
    admin_user_id = get_current_user_id()
    
    db = get_admin_db()
    auth_manager = AuthenticationManager(db)
    
    success = auth_manager.terminate_session(session_obj_id, admin_user_id)
    
    if success:
        return jsonify(success_response(message='Session terminated successfully'))
    else:
        return error_response('Session not found', 'NOT_FOUND', 404)