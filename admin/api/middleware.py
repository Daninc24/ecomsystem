"""
API Middleware for authentication, authorization, rate limiting, and security
"""

import time
import hashlib
from functools import wraps
from collections import defaultdict, deque
from datetime import datetime, timedelta
from flask import request, jsonify, session, g
from bson import ObjectId
from typing import Dict, List, Optional, Any

from .base_api import error_response


class RateLimiter:
    """Rate limiting implementation using sliding window."""
    
    def __init__(self):
        self.requests = defaultdict(deque)
        self.limits = {
            'default': {'requests': 100, 'window': 3600},  # 100 requests per hour
            'auth': {'requests': 10, 'window': 300},       # 10 auth requests per 5 minutes
            'upload': {'requests': 20, 'window': 3600},    # 20 uploads per hour
            'export': {'requests': 5, 'window': 3600},     # 5 exports per hour
        }
    
    def is_allowed(self, key: str, limit_type: str = 'default') -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        limit_config = self.limits.get(limit_type, self.limits['default'])
        window = limit_config['window']
        max_requests = limit_config['requests']
        
        # Clean old requests outside the window
        while self.requests[key] and self.requests[key][0] <= now - window:
            self.requests[key].popleft()
        
        # Check if under limit
        if len(self.requests[key]) < max_requests:
            self.requests[key].append(now)
            return True
        
        return False
    
    def get_reset_time(self, key: str, limit_type: str = 'default') -> int:
        """Get time when rate limit resets."""
        if not self.requests[key]:
            return int(time.time())
        
        window = self.limits.get(limit_type, self.limits['default'])['window']
        return int(self.requests[key][0] + window)


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_identifier() -> str:
    """Get unique identifier for the client."""
    # Use user ID if authenticated, otherwise use IP + User-Agent
    if 'user_id' in session:
        return f"user:{session['user_id']}"
    
    ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    return f"ip:{hashlib.md5(f'{ip}:{user_agent}'.encode()).hexdigest()}"


def rate_limit(limit_type: str = 'default'):
    """Rate limiting decorator."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_id = get_client_identifier()
            
            if not rate_limiter.is_allowed(client_id, limit_type):
                reset_time = rate_limiter.get_reset_time(client_id, limit_type)
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded',
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'reset_time': reset_time
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_permission(permission: str):
    """Decorator to require specific permission."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return error_response('Authentication required', 'AUTH_REQUIRED', 401)
            
            # Check if user has required permission
            from ..services.permission_engine import PermissionEngine
            from ..database.collections import get_admin_db
            
            try:
                user_id = ObjectId(session['user_id'])
                db = get_admin_db()
                permission_engine = PermissionEngine(db)
                
                if not permission_engine.has_permission(user_id, permission):
                    return error_response('Insufficient permissions', 'PERMISSION_DENIED', 403)
                
                return f(*args, **kwargs)
            
            except Exception as e:
                return error_response('Permission check failed', 'PERMISSION_ERROR', 500)
        
        return decorated_function
    return decorator


def require_role(role: str):
    """Decorator to require specific role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return error_response('Authentication required', 'AUTH_REQUIRED', 401)
            
            user_role = session.get('user_role', '')
            if user_role != role and user_role != 'super_admin':
                return error_response('Insufficient role', 'ROLE_REQUIRED', 403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def log_api_request():
    """Decorator to log API requests for audit purposes."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            # Log request
            from ..services.audit_logger import AuditLogger
            from ..database.collections import get_admin_db
            
            try:
                db = get_admin_db()
                audit_logger = AuditLogger(db)
                
                user_id = session.get('user_id')
                if user_id:
                    user_id = ObjectId(user_id)
                
                request_data = {
                    'method': request.method,
                    'endpoint': request.endpoint,
                    'url': request.url,
                    'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
                    'user_agent': request.headers.get('User-Agent', ''),
                    'timestamp': datetime.utcnow()
                }
                
                # Execute the function
                response = f(*args, **kwargs)
                
                # Log successful request
                request_data['status'] = 'success'
                request_data['duration'] = time.time() - start_time
                
                audit_logger.log_api_request(user_id, request_data)
                
                return response
                
            except Exception as e:
                # Log failed request
                request_data['status'] = 'error'
                request_data['error'] = str(e)
                request_data['duration'] = time.time() - start_time
                
                if 'audit_logger' in locals():
                    audit_logger.log_api_request(user_id, request_data)
                
                raise e
        
        return decorated_function
    return decorator


def validate_api_key():
    """Decorator to validate API key for external access."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get('X-API-Key')
            
            if not api_key:
                return error_response('API key required', 'API_KEY_REQUIRED', 401)
            
            # Validate API key
            from ..services.authentication_manager import AuthenticationManager
            from ..database.collections import get_admin_db
            
            try:
                db = get_admin_db()
                auth_manager = AuthenticationManager(db)
                
                api_key_data = auth_manager.validate_api_key(api_key)
                
                if not api_key_data:
                    return error_response('Invalid API key', 'INVALID_API_KEY', 401)
                
                if not api_key_data.get('active', False):
                    return error_response('API key disabled', 'API_KEY_DISABLED', 401)
                
                # Store API key info in request context
                g.api_key_data = api_key_data
                
                return f(*args, **kwargs)
                
            except Exception as e:
                return error_response('API key validation failed', 'API_KEY_ERROR', 500)
        
        return decorated_function
    return decorator


def cors_headers():
    """Decorator to add CORS headers."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)
            
            # Add CORS headers if response is a tuple (response, status_code)
            if isinstance(response, tuple):
                response_data, status_code = response
                if hasattr(response_data, 'headers'):
                    response_data.headers['Access-Control-Allow-Origin'] = '*'
                    response_data.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                    response_data.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-API-Key'
                return response_data, status_code
            else:
                if hasattr(response, 'headers'):
                    response.headers['Access-Control-Allow-Origin'] = '*'
                    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-API-Key'
                return response
        
        return decorated_function
    return decorator


def security_headers():
    """Decorator to add security headers."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)
            
            security_headers_dict = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
                'Content-Security-Policy': "default-src 'self'",
                'Referrer-Policy': 'strict-origin-when-cross-origin'
            }
            
            # Add security headers
            if isinstance(response, tuple):
                response_data, status_code = response
                if hasattr(response_data, 'headers'):
                    for header, value in security_headers_dict.items():
                        response_data.headers[header] = value
                return response_data, status_code
            else:
                if hasattr(response, 'headers'):
                    for header, value in security_headers_dict.items():
                        response.headers[header] = value
                return response
        
        return decorated_function
    return decorator


def api_versioning(version: str = 'v1'):
    """Decorator to handle API versioning."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            requested_version = request.headers.get('API-Version', 'v1')
            
            if requested_version != version:
                return error_response(
                    f'API version {requested_version} not supported. Use {version}',
                    'UNSUPPORTED_VERSION',
                    400
                )
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def cache_control(max_age: int = 0, public: bool = False):
    """Decorator to add cache control headers."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)
            
            cache_value = f"max-age={max_age}"
            if public:
                cache_value = f"public, {cache_value}"
            else:
                cache_value = f"private, {cache_value}"
            
            if max_age == 0:
                cache_value = "no-cache, no-store, must-revalidate"
            
            # Add cache control headers
            if isinstance(response, tuple):
                response_data, status_code = response
                if hasattr(response_data, 'headers'):
                    response_data.headers['Cache-Control'] = cache_value
                return response_data, status_code
            else:
                if hasattr(response, 'headers'):
                    response.headers['Cache-Control'] = cache_value
                return response
        
        return decorated_function
    return decorator


def request_size_limit(max_size_mb: int = 10):
    """Decorator to limit request size."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            content_length = request.content_length
            
            if content_length and content_length > max_size_mb * 1024 * 1024:
                return error_response(
                    f'Request too large. Maximum size: {max_size_mb}MB',
                    'REQUEST_TOO_LARGE',
                    413
                )
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator