"""
API Key Management System
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from bson import ObjectId
from .base_api import admin_api_required, validate_json_request, handle_api_errors, success_response, error_response, get_current_user_id
from .middleware import require_permission, rate_limit, cors_headers, security_headers, log_api_request

api_keys_bp = Blueprint('admin_api_keys', __name__, url_prefix='/api/admin/api-keys')


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"ak_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


@api_keys_bp.route('/', methods=['GET'])
@admin_api_required
@require_permission('manage_api_keys')
@rate_limit('default')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def list_api_keys():
    """List all API keys (without revealing the actual keys)."""
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    status = request.args.get('status')  # active, inactive, expired
    
    # Build query
    query = {}
    if status:
        if status == 'expired':
            query['expires_at'] = {'$lt': datetime.utcnow()}
        else:
            query['active'] = status == 'active'
    
    # Get total count
    total = db.api_keys.count_documents(query)
    
    # Get paginated results
    skip = (page - 1) * limit
    api_keys = list(db.api_keys.find(query)
                   .sort('created_at', -1)
                   .skip(skip)
                   .limit(limit))
    
    # Remove sensitive data and convert ObjectIds
    for key_data in api_keys:
        key_data['_id'] = str(key_data['_id'])
        key_data['created_by'] = str(key_data['created_by'])
        # Don't return the actual key or hash
        key_data.pop('key_hash', None)
        # Show only last 4 characters of the key for identification
        if 'key_preview' not in key_data:
            key_data['key_preview'] = '****' + key_data.get('name', '')[-4:]
    
    return jsonify(success_response({
        'items': api_keys,
        'total': total,
        'page': page,
        'limit': limit,
        'pages': (total + limit - 1) // limit
    }))


@api_keys_bp.route('/', methods=['POST'])
@admin_api_required
@require_permission('manage_api_keys')
@validate_json_request(['name'])
@rate_limit('auth')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def create_api_key():
    """Create a new API key."""
    from ..database.collections import get_admin_db
    
    data = request.get_json()
    user_id = get_current_user_id()
    
    # Generate API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    # Set expiration date
    expires_days = data.get('expires_days', 365)  # Default 1 year
    expires_at = datetime.utcnow() + timedelta(days=expires_days) if expires_days > 0 else None
    
    # Create API key document
    api_key_doc = {
        'name': data['name'],
        'description': data.get('description', ''),
        'key_hash': key_hash,
        'key_preview': api_key[-8:],  # Store last 8 chars for identification
        'permissions': data.get('permissions', []),
        'rate_limit_override': data.get('rate_limit_override'),
        'ip_whitelist': data.get('ip_whitelist', []),
        'active': True,
        'created_at': datetime.utcnow(),
        'created_by': user_id,
        'expires_at': expires_at,
        'last_used_at': None,
        'usage_count': 0
    }
    
    db = get_admin_db()
    result = db.api_keys.insert_one(api_key_doc)
    
    # Return the API key (only time it's shown in full)
    return jsonify(success_response({
        'id': str(result.inserted_id),
        'api_key': api_key,  # Only returned once!
        'name': data['name'],
        'expires_at': expires_at.isoformat() if expires_at else None,
        'warning': 'This is the only time the full API key will be shown. Store it securely.'
    })), 201


@api_keys_bp.route('/<key_id>', methods=['GET'])
@admin_api_required
@require_permission('manage_api_keys')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def get_api_key(key_id):
    """Get API key details (without the actual key)."""
    from ..database.collections import get_admin_db
    
    try:
        key_obj_id = ObjectId(key_id)
    except:
        return error_response('Invalid API key ID', 'INVALID_ID')
    
    db = get_admin_db()
    api_key = db.api_keys.find_one({'_id': key_obj_id})
    
    if not api_key:
        return error_response('API key not found', 'NOT_FOUND', 404)
    
    # Convert ObjectIds and remove sensitive data
    api_key['_id'] = str(api_key['_id'])
    api_key['created_by'] = str(api_key['created_by'])
    api_key.pop('key_hash', None)
    
    return jsonify(success_response(api_key))


@api_keys_bp.route('/<key_id>', methods=['PUT'])
@admin_api_required
@require_permission('manage_api_keys')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def update_api_key(key_id):
    """Update API key settings (not the key itself)."""
    from ..database.collections import get_admin_db
    
    try:
        key_obj_id = ObjectId(key_id)
    except:
        return error_response('Invalid API key ID', 'INVALID_ID')
    
    data = request.get_json()
    user_id = get_current_user_id()
    
    # Prepare update data
    update_data = {
        'updated_at': datetime.utcnow(),
        'updated_by': user_id
    }
    
    # Allow updating specific fields
    allowed_fields = ['name', 'description', 'permissions', 'rate_limit_override', 'ip_whitelist', 'active']
    for field in allowed_fields:
        if field in data:
            update_data[field] = data[field]
    
    db = get_admin_db()
    result = db.api_keys.update_one(
        {'_id': key_obj_id},
        {'$set': update_data}
    )
    
    if result.matched_count == 0:
        return error_response('API key not found', 'NOT_FOUND', 404)
    
    return jsonify(success_response(message='API key updated successfully'))


@api_keys_bp.route('/<key_id>', methods=['DELETE'])
@admin_api_required
@require_permission('manage_api_keys')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def delete_api_key(key_id):
    """Delete an API key."""
    from ..database.collections import get_admin_db
    
    try:
        key_obj_id = ObjectId(key_id)
    except:
        return error_response('Invalid API key ID', 'INVALID_ID')
    
    db = get_admin_db()
    result = db.api_keys.delete_one({'_id': key_obj_id})
    
    if result.deleted_count == 0:
        return error_response('API key not found', 'NOT_FOUND', 404)
    
    return jsonify(success_response(message='API key deleted successfully'))


@api_keys_bp.route('/<key_id>/regenerate', methods=['POST'])
@admin_api_required
@require_permission('manage_api_keys')
@rate_limit('auth')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def regenerate_api_key(key_id):
    """Regenerate an API key (creates new key, invalidates old one)."""
    from ..database.collections import get_admin_db
    
    try:
        key_obj_id = ObjectId(key_id)
    except:
        return error_response('Invalid API key ID', 'INVALID_ID')
    
    # Generate new API key
    new_api_key = generate_api_key()
    new_key_hash = hash_api_key(new_api_key)
    
    user_id = get_current_user_id()
    
    db = get_admin_db()
    result = db.api_keys.update_one(
        {'_id': key_obj_id},
        {
            '$set': {
                'key_hash': new_key_hash,
                'key_preview': new_api_key[-8:],
                'regenerated_at': datetime.utcnow(),
                'regenerated_by': user_id,
                'usage_count': 0,  # Reset usage count
                'last_used_at': None
            }
        }
    )
    
    if result.matched_count == 0:
        return error_response('API key not found', 'NOT_FOUND', 404)
    
    return jsonify(success_response({
        'api_key': new_api_key,  # Only returned once!
        'regenerated_at': datetime.utcnow().isoformat(),
        'warning': 'This is the only time the new API key will be shown. Store it securely.'
    }))


@api_keys_bp.route('/<key_id>/usage', methods=['GET'])
@admin_api_required
@require_permission('manage_api_keys')
@cors_headers()
@security_headers()
@handle_api_errors
def get_api_key_usage(key_id):
    """Get API key usage statistics."""
    from ..database.collections import get_admin_db
    
    try:
        key_obj_id = ObjectId(key_id)
    except:
        return error_response('Invalid API key ID', 'INVALID_ID')
    
    db = get_admin_db()
    
    # Get API key info
    api_key = db.api_keys.find_one({'_id': key_obj_id}, {'name': 1, 'usage_count': 1, 'last_used_at': 1})
    if not api_key:
        return error_response('API key not found', 'NOT_FOUND', 404)
    
    # Get usage statistics from audit logs
    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    usage_stats = list(db.audit_logs.aggregate([
        {
            '$match': {
                'api_key_id': key_obj_id,
                'timestamp': {'$gte': start_date}
            }
        },
        {
            '$group': {
                '_id': {
                    'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}},
                    'endpoint': '$details.endpoint'
                },
                'count': {'$sum': 1}
            }
        },
        {
            '$sort': {'_id.date': 1}
        }
    ]))
    
    # Get error rate
    error_count = db.audit_logs.count_documents({
        'api_key_id': key_obj_id,
        'timestamp': {'$gte': start_date},
        'details.status': 'error'
    })
    
    total_requests = db.audit_logs.count_documents({
        'api_key_id': key_obj_id,
        'timestamp': {'$gte': start_date}
    })
    
    error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
    
    return jsonify(success_response({
        'api_key_name': api_key['name'],
        'total_usage': api_key.get('usage_count', 0),
        'last_used_at': api_key.get('last_used_at'),
        'period_days': days,
        'period_requests': total_requests,
        'error_rate': round(error_rate, 2),
        'daily_usage': usage_stats
    }))


@api_keys_bp.route('/validate', methods=['POST'])
@validate_json_request(['api_key'])
@rate_limit('auth')
@cors_headers()
@security_headers()
@handle_api_errors
def validate_api_key():
    """Validate an API key (for internal use)."""
    from ..database.collections import get_admin_db
    
    data = request.get_json()
    api_key = data['api_key']
    
    if not api_key.startswith('ak_'):
        return error_response('Invalid API key format', 'INVALID_FORMAT')
    
    key_hash = hash_api_key(api_key)
    
    db = get_admin_db()
    api_key_doc = db.api_keys.find_one({
        'key_hash': key_hash,
        'active': True
    })
    
    if not api_key_doc:
        return error_response('Invalid API key', 'INVALID_KEY', 401)
    
    # Check expiration
    if api_key_doc.get('expires_at') and api_key_doc['expires_at'] < datetime.utcnow():
        return error_response('API key expired', 'KEY_EXPIRED', 401)
    
    # Update usage statistics
    db.api_keys.update_one(
        {'_id': api_key_doc['_id']},
        {
            '$set': {'last_used_at': datetime.utcnow()},
            '$inc': {'usage_count': 1}
        }
    )
    
    # Return key info (without sensitive data)
    key_info = {
        'id': str(api_key_doc['_id']),
        'name': api_key_doc['name'],
        'permissions': api_key_doc.get('permissions', []),
        'rate_limit_override': api_key_doc.get('rate_limit_override'),
        'ip_whitelist': api_key_doc.get('ip_whitelist', [])
    }
    
    return jsonify(success_response(key_info))