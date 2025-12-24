"""
Security Middleware
Comprehensive security middleware for API endpoints and admin interface
"""

import time
import json
from functools import wraps
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from flask import request, jsonify, g
from bson import ObjectId

from .input_validator import InputValidator, ValidationError
from .session_security_manager import SessionSecurityManager
from .security_monitor import SecurityMonitor


class SecurityMiddleware:
    """Comprehensive security middleware for admin system."""
    
    def __init__(self, db, audit_logger=None):
        self.db = db
        self.audit_logger = audit_logger
        self.input_validator = InputValidator(db, audit_logger)
        self.session_manager = SessionSecurityManager(db, audit_logger)
        self.security_monitor = SecurityMonitor(db)
        
        # Rate limiting storage
        self.rate_limit_storage = {}
        
        # Security configuration
        self.config = {
            'rate_limit_requests_per_minute': 60,
            'rate_limit_burst_requests': 10,
            'max_request_size_mb': 10,
            'require_csrf_token': True,
            'block_suspicious_ips': True,
            'log_all_requests': False,
            'validate_all_inputs': True,
            'require_secure_headers': True
        }
        
        # Blocked IPs (in production, this would be in database/cache)
        self.blocked_ips = set()
        
        # CSRF tokens (in production, use Redis or database)
        self.csrf_tokens = {}
    
    def apply_security_middleware(self, app):
        """Apply security middleware to Flask app."""
        
        @app.before_request
        def before_request():
            """Execute before each request."""
            return self._before_request_handler()
        
        @app.after_request
        def after_request(response):
            """Execute after each request."""
            return self._after_request_handler(response)
        
        @app.errorhandler(429)
        def rate_limit_handler(e):
            """Handle rate limit exceeded."""
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.',
                'retry_after': 60
            }), 429
        
        @app.errorhandler(413)
        def payload_too_large_handler(e):
            """Handle payload too large."""
            return jsonify({
                'error': 'Payload too large',
                'message': f'Request size exceeds {self.config["max_request_size_mb"]}MB limit'
            }), 413
    
    def _before_request_handler(self):
        """Handle security checks before request processing."""
        try:
            # Get client information
            client_ip = self._get_client_ip()
            user_agent = request.headers.get('User-Agent', '')
            
            # Store in request context
            g.client_ip = client_ip
            g.user_agent = user_agent
            g.request_start_time = time.time()
            
            # Check if IP is blocked
            if self._is_ip_blocked(client_ip):
                self._log_blocked_request(client_ip, 'blocked_ip')
                return jsonify({
                    'error': 'Access denied',
                    'message': 'Your IP address has been blocked'
                }), 403
            
            # Rate limiting
            if not self._check_rate_limit(client_ip):
                self._log_blocked_request(client_ip, 'rate_limit_exceeded')
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests from your IP address'
                }), 429
            
            # Request size validation
            if not self._validate_request_size():
                self._log_blocked_request(client_ip, 'payload_too_large')
                return jsonify({
                    'error': 'Request too large',
                    'message': f'Request exceeds {self.config["max_request_size_mb"]}MB limit'
                }), 413
            
            # Security headers validation
            if self.config['require_secure_headers']:
                header_issues = self._validate_security_headers()
                if header_issues:
                    self._log_security_warning('missing_security_headers', {
                        'missing_headers': header_issues,
                        'client_ip': client_ip
                    })
            
            # Log suspicious requests
            if self._is_suspicious_request():
                self.security_monitor.log_request(
                    client_ip, user_agent, request.path, 
                    request.method, None, str(request.get_data())
                )
            
            # CSRF protection for state-changing requests
            if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                if self.config['require_csrf_token'] and not self._validate_csrf_token():
                    self._log_blocked_request(client_ip, 'csrf_token_invalid')
                    return jsonify({
                        'error': 'CSRF token invalid',
                        'message': 'Invalid or missing CSRF token'
                    }), 403
            
            return None  # Continue processing
            
        except Exception as e:
            # Log security middleware error
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=None,
                    action='security_middleware_error',
                    resource_type='security',
                    resource_id='middleware',
                    details={
                        'error': str(e),
                        'client_ip': getattr(g, 'client_ip', 'unknown'),
                        'path': request.path
                    },
                    success=False
                )
            
            # In case of security middleware failure, allow request but log
            return None
    
    def _after_request_handler(self, response):
        """Handle security measures after request processing."""
        try:
            # Add security headers
            response = self._add_security_headers(response)
            
            # Log request if configured
            if self.config['log_all_requests']:
                self._log_request_completion(response)
            
            return response
            
        except Exception as e:
            # Log error but don't break response
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=None,
                    action='security_after_request_error',
                    resource_type='security',
                    resource_id='middleware',
                    details={'error': str(e)},
                    success=False
                )
            
            return response
    
    def require_authentication(self, f):
        """Decorator to require valid authentication."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get session token from header or cookie
            session_token = request.headers.get('Authorization')
            if session_token and session_token.startswith('Bearer '):
                session_token = session_token[7:]  # Remove 'Bearer ' prefix
            else:
                session_token = request.cookies.get('session_token')
            
            if not session_token:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'No session token provided'
                }), 401
            
            # Validate session
            session, warnings = self.session_manager.validate_session_security(
                session_token, g.client_ip, g.user_agent
            )
            
            if not session:
                return jsonify({
                    'error': 'Invalid session',
                    'message': 'Session is invalid or expired'
                }), 401
            
            # Store session info in request context
            g.current_session = session
            g.current_user_id = session.user_id
            g.session_warnings = warnings
            
            # Log security warnings
            if warnings and self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=session.user_id,
                    action='session_security_warnings',
                    resource_type='session',
                    resource_id=str(session.id),
                    details={'warnings': warnings},
                    severity='warning'
                )
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def require_permission(self, permission: str):
        """Decorator to require specific permission."""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # This assumes require_authentication was already applied
                if not hasattr(g, 'current_user_id'):
                    return jsonify({
                        'error': 'Authentication required',
                        'message': 'User not authenticated'
                    }), 401
                
                # Check permission (this would integrate with PermissionEngine)
                # For now, we'll assume admin users have all permissions
                # In production, integrate with the PermissionEngine
                
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
    
    def validate_input(self, input_schema: Dict[str, str]):
        """Decorator to validate request input according to schema."""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    # Get request data
                    if request.is_json:
                        request_data = request.get_json()
                    else:
                        request_data = request.form.to_dict()
                    
                    if not request_data:
                        request_data = {}
                    
                    # Prepare inputs for validation
                    inputs_to_validate = {}
                    validation_errors = []
                    
                    for field_name, input_type in input_schema.items():
                        if field_name in request_data:
                            inputs_to_validate[field_name] = (request_data[field_name], input_type)
                    
                    # Validate inputs
                    if inputs_to_validate:
                        validation_results = self.input_validator.validate_batch_inputs(
                            inputs_to_validate, 
                            getattr(g, 'current_user_id', None)
                        )
                        
                        # Check for validation failures
                        for field_name, result in validation_results.items():
                            if result.sanitized_value is None:
                                validation_errors.extend(result.warnings)
                            else:
                                # Replace original value with sanitized value
                                request_data[field_name] = result.sanitized_value
                    
                    if validation_errors:
                        return jsonify({
                            'error': 'Validation failed',
                            'message': 'Input validation errors',
                            'details': validation_errors
                        }), 400
                    
                    # Store sanitized data in request context
                    g.validated_data = request_data
                    
                    return f(*args, **kwargs)
                    
                except ValidationError as e:
                    return jsonify({
                        'error': 'Validation error',
                        'message': str(e)
                    }), 400
                except Exception as e:
                    if self.audit_logger:
                        self.audit_logger.log_activity(
                            user_id=getattr(g, 'current_user_id', None),
                            action='input_validation_error',
                            resource_type='validation',
                            resource_id=request.path,
                            details={'error': str(e)},
                            success=False
                        )
                    
                    return jsonify({
                        'error': 'Validation system error',
                        'message': 'Unable to validate input'
                    }), 500
            
            return decorated_function
        return decorator
    
    def _get_client_ip(self) -> str:
        """Get client IP address, considering proxies."""
        # Check for forwarded IP headers
        forwarded_ips = request.headers.get('X-Forwarded-For')
        if forwarded_ips:
            return forwarded_ips.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.remote_addr or 'unknown'
    
    def _is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP address is blocked."""
        return ip_address in self.blocked_ips
    
    def _check_rate_limit(self, ip_address: str) -> bool:
        """Check rate limiting for IP address."""
        now = time.time()
        minute_window = int(now // 60)
        
        # Clean old entries
        self._cleanup_rate_limit_storage()
        
        # Get current counts
        if ip_address not in self.rate_limit_storage:
            self.rate_limit_storage[ip_address] = {}
        
        ip_data = self.rate_limit_storage[ip_address]
        current_minute_count = ip_data.get(minute_window, 0)
        
        # Check if limit exceeded
        if current_minute_count >= self.config['rate_limit_requests_per_minute']:
            return False
        
        # Increment counter
        ip_data[minute_window] = current_minute_count + 1
        
        return True
    
    def _cleanup_rate_limit_storage(self):
        """Clean up old rate limit data."""
        now = time.time()
        current_minute = int(now // 60)
        cutoff_minute = current_minute - 5  # Keep last 5 minutes
        
        for ip_address in list(self.rate_limit_storage.keys()):
            ip_data = self.rate_limit_storage[ip_address]
            
            # Remove old minute buckets
            for minute in list(ip_data.keys()):
                if minute < cutoff_minute:
                    del ip_data[minute]
            
            # Remove empty IP entries
            if not ip_data:
                del self.rate_limit_storage[ip_address]
    
    def _validate_request_size(self) -> bool:
        """Validate request size."""
        content_length = request.content_length
        if content_length is None:
            return True
        
        max_size = self.config['max_request_size_mb'] * 1024 * 1024  # Convert to bytes
        return content_length <= max_size
    
    def _validate_security_headers(self) -> List[str]:
        """Validate presence of security headers."""
        missing_headers = []
        
        # Check for important security headers
        security_headers = {
            'X-Requested-With': 'XMLHttpRequest',  # For AJAX requests
            'Content-Type': None,  # Should be present for POST/PUT
        }
        
        if request.method in ['POST', 'PUT', 'PATCH']:
            if not request.headers.get('Content-Type'):
                missing_headers.append('Content-Type')
        
        return missing_headers
    
    def _validate_csrf_token(self) -> bool:
        """Validate CSRF token."""
        # Get CSRF token from header or form data
        csrf_token = request.headers.get('X-CSRF-Token')
        if not csrf_token and request.is_json:
            csrf_token = request.get_json().get('csrf_token')
        elif not csrf_token:
            csrf_token = request.form.get('csrf_token')
        
        if not csrf_token:
            return False
        
        # In production, validate against stored token
        # For now, we'll accept any non-empty token
        return len(csrf_token) > 0
    
    def _is_suspicious_request(self) -> bool:
        """Check if request appears suspicious."""
        # Check for suspicious patterns in URL
        suspicious_paths = [
            'admin', 'wp-admin', 'phpmyadmin', 'config',
            '.env', 'backup', 'test', 'debug', 'shell'
        ]
        
        path_lower = request.path.lower()
        if any(suspicious in path_lower for suspicious in suspicious_paths):
            return True
        
        # Check user agent
        user_agent = request.headers.get('User-Agent', '').lower()
        suspicious_agents = ['bot', 'crawler', 'scanner', 'sqlmap', 'nikto']
        
        if any(agent in user_agent for agent in suspicious_agents):
            return True
        
        return False
    
    def _add_security_headers(self, response):
        """Add security headers to response."""
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy (basic)
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )
        
        return response
    
    def _log_blocked_request(self, ip_address: str, reason: str):
        """Log blocked request."""
        if self.audit_logger:
            self.audit_logger.log_activity(
                user_id=None,
                action='request_blocked',
                resource_type='security',
                resource_id='middleware',
                details={
                    'reason': reason,
                    'ip_address': ip_address,
                    'path': request.path,
                    'method': request.method,
                    'user_agent': request.headers.get('User-Agent', '')
                },
                severity='warning'
            )
    
    def _log_security_warning(self, warning_type: str, details: Dict[str, Any]):
        """Log security warning."""
        if self.audit_logger:
            self.audit_logger.log_activity(
                user_id=getattr(g, 'current_user_id', None),
                action=f'security_warning_{warning_type}',
                resource_type='security',
                resource_id='middleware',
                details=details,
                severity='warning'
            )
    
    def _log_request_completion(self, response):
        """Log request completion."""
        if self.audit_logger:
            duration = time.time() - getattr(g, 'request_start_time', 0)
            
            self.audit_logger.log_activity(
                user_id=getattr(g, 'current_user_id', None),
                action='request_completed',
                resource_type='api',
                resource_id=request.path,
                details={
                    'method': request.method,
                    'status_code': response.status_code,
                    'duration_seconds': round(duration, 3),
                    'client_ip': getattr(g, 'client_ip', 'unknown'),
                    'user_agent': getattr(g, 'user_agent', '')[:100]
                }
            )
    
    def block_ip(self, ip_address: str, reason: str):
        """Block an IP address."""
        self.blocked_ips.add(ip_address)
        
        if self.audit_logger:
            self.audit_logger.log_activity(
                user_id=None,
                action='ip_blocked',
                resource_type='security',
                resource_id=ip_address,
                details={'reason': reason}
            )
    
    def unblock_ip(self, ip_address: str):
        """Unblock an IP address."""
        self.blocked_ips.discard(ip_address)
        
        if self.audit_logger:
            self.audit_logger.log_activity(
                user_id=None,
                action='ip_unblocked',
                resource_type='security',
                resource_id=ip_address
            )
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status."""
        return {
            'blocked_ips_count': len(self.blocked_ips),
            'rate_limit_tracked_ips': len(self.rate_limit_storage),
            'configuration': self.config,
            'active_csrf_tokens': len(self.csrf_tokens)
        }