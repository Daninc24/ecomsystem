"""
Base API utilities and decorators for admin endpoints
"""

from functools import wraps
from flask import request, jsonify, session
from typing import Any, Dict, Optional
from bson import ObjectId


def admin_api_required(f):
    """Decorator to require admin authentication for API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        # Additional admin role check would go here
        # For now, we'll assume the session validation is sufficient
        
        return f(*args, **kwargs)
    return decorated_function


def validate_json_request(required_fields: list = None):
    """Decorator to validate JSON request data."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Content-Type must be application/json',
                    'code': 'INVALID_CONTENT_TYPE'
                }), 400
            
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Request body must contain valid JSON',
                    'code': 'INVALID_JSON'
                }), 400
            
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'error': f'Missing required fields: {", ".join(missing_fields)}',
                        'code': 'MISSING_FIELDS'
                    }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def handle_api_errors(f):
    """Decorator to handle common API errors."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'code': 'VALIDATION_ERROR'
            }), 400
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Internal server error',
                'code': 'INTERNAL_ERROR'
            }), 500
    return decorated_function


def success_response(data: Any = None, message: str = None) -> Dict[str, Any]:
    """Create a standardized success response."""
    response = {'success': True}
    
    if data is not None:
        response['data'] = data
    
    if message:
        response['message'] = message
    
    return response


def error_response(error: str, code: str = 'ERROR', status_code: int = 400) -> tuple:
    """Create a standardized error response."""
    return jsonify({
        'success': False,
        'error': error,
        'code': code
    }), status_code


def get_current_user_id() -> Optional[ObjectId]:
    """Get the current user ID from session."""
    user_id = session.get('user_id')
    if user_id:
        try:
            return ObjectId(user_id)
        except:
            return None
    return None