"""
Input Validation and Sanitization Service
Provides comprehensive input validation and sanitization for all admin inputs
"""

import re
import html
import json
from typing import Any, Dict, List, Optional, Union, Tuple
from urllib.parse import urlparse
from datetime import datetime
from bson import ObjectId

from .base_service import BaseService


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class SanitizationResult:
    """Result of input sanitization."""
    
    def __init__(self, sanitized_value: Any, was_modified: bool = False, warnings: List[str] = None):
        self.sanitized_value = sanitized_value
        self.was_modified = was_modified
        self.warnings = warnings or []
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)


class InputValidator(BaseService):
    """Service for validating and sanitizing all admin inputs."""
    
    def _get_collection_name(self) -> str:
        return "validation_logs"
    
    def __init__(self, db, audit_logger=None):
        super().__init__(db)
        self.audit_logger = audit_logger
        
        # Dangerous patterns for security validation
        self.sql_injection_patterns = [
            r'(?i)(union|select|insert|delete|drop|create|alter|exec|execute)\s+',
            r'(?i)(or|and)\s+\d+\s*=\s*\d+',
            r'(?i)(\'\s*(or|and)\s*\')',
            r'(?i)(;|\|\||&&)',
            r'(?i)(\/\*|\*\/|--)',
        ]
        
        self.xss_patterns = [
            r'(?i)<script[^>]*>.*?</script>',
            r'(?i)javascript:',
            r'(?i)on\w+\s*=',
            r'(?i)<iframe[^>]*>',
            r'(?i)<object[^>]*>',
            r'(?i)<embed[^>]*>',
            r'(?i)<link[^>]*>',
            r'(?i)<meta[^>]*>',
        ]
        
        self.path_traversal_patterns = [
            r'\.\./',
            r'\.\.\\',
            r'%2e%2e%2f',
            r'%2e%2e%5c',
        ]
        
        self.command_injection_patterns = [
            r'(?i)(cmd|exec|system|eval|shell_exec|passthru|popen)\s*\(',
            r'(?i)(\||&|;|`|\$\()',
            r'(?i)(nc|netcat|wget|curl|ping|nslookup)\s+',
        ]
        
        # Allowed HTML tags for rich text content
        self.allowed_html_tags = {
            'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'code', 'pre'
        }
        
        # Allowed HTML attributes
        self.allowed_html_attributes = {
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'title', 'width', 'height'],
            'blockquote': ['cite'],
        }
    
    def validate_and_sanitize_input(self, 
                                  input_data: Any, 
                                  input_type: str,
                                  field_name: str = "",
                                  user_id: Optional[ObjectId] = None) -> SanitizationResult:
        """
        Validate and sanitize input data based on type.
        
        Args:
            input_data: The data to validate and sanitize
            input_type: Type of input (string, email, url, html, json, etc.)
            field_name: Name of the field being validated
            user_id: ID of user making the input
        
        Returns:
            SanitizationResult with sanitized data and warnings
        """
        try:
            if input_type == 'string':
                return self._validate_string(input_data, field_name)
            elif input_type == 'email':
                return self._validate_email(input_data, field_name)
            elif input_type == 'url':
                return self._validate_url(input_data, field_name)
            elif input_type == 'html':
                return self._validate_html(input_data, field_name)
            elif input_type == 'json':
                return self._validate_json(input_data, field_name)
            elif input_type == 'number':
                return self._validate_number(input_data, field_name)
            elif input_type == 'boolean':
                return self._validate_boolean(input_data, field_name)
            elif input_type == 'object_id':
                return self._validate_object_id(input_data, field_name)
            elif input_type == 'filename':
                return self._validate_filename(input_data, field_name)
            elif input_type == 'sql_safe':
                return self._validate_sql_safe(input_data, field_name)
            else:
                # Default string validation
                return self._validate_string(input_data, field_name)
                
        except Exception as e:
            # Log validation error
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=user_id,
                    action='input_validation_error',
                    resource_type='validation',
                    resource_id=field_name,
                    details={
                        'input_type': input_type,
                        'error': str(e),
                        'input_preview': str(input_data)[:100] if input_data else None
                    },
                    success=False
                )
            raise ValidationError(f"Validation failed for {field_name}: {str(e)}")
    
    def _validate_string(self, value: Any, field_name: str) -> SanitizationResult:
        """Validate and sanitize string input."""
        if value is None:
            return SanitizationResult("")
        
        # Convert to string
        str_value = str(value)
        original_value = str_value
        warnings = []
        
        # Check for security threats
        threats_found = self._detect_security_threats(str_value)
        if threats_found:
            warnings.extend([f"Security threat detected: {threat}" for threat in threats_found])
        
        # Basic sanitization
        # Remove null bytes
        str_value = str_value.replace('\x00', '')
        
        # Normalize whitespace
        str_value = re.sub(r'\s+', ' ', str_value).strip()
        
        # HTML escape if not explicitly HTML content
        str_value = html.escape(str_value)
        
        was_modified = str_value != original_value
        
        return SanitizationResult(str_value, was_modified, warnings)
    
    def _validate_email(self, value: Any, field_name: str) -> SanitizationResult:
        """Validate and sanitize email input."""
        if not value:
            raise ValidationError(f"{field_name}: Email cannot be empty")
        
        email = str(value).strip().lower()
        original_email = email
        warnings = []
        
        # Basic email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            raise ValidationError(f"{field_name}: Invalid email format")
        
        # Check for suspicious patterns
        if any(pattern in email for pattern in ['..', '--', '__']):
            warnings.append("Email contains suspicious patterns")
        
        # Length validation
        if len(email) > 254:
            raise ValidationError(f"{field_name}: Email too long (max 254 characters)")
        
        was_modified = email != original_email
        
        return SanitizationResult(email, was_modified, warnings)
    
    def _validate_url(self, value: Any, field_name: str) -> SanitizationResult:
        """Validate and sanitize URL input."""
        if not value:
            return SanitizationResult("")
        
        url = str(value).strip()
        original_url = url
        warnings = []
        
        try:
            parsed = urlparse(url)
            
            # Ensure scheme is present and safe
            if not parsed.scheme:
                url = 'https://' + url
                parsed = urlparse(url)
                warnings.append("Added HTTPS scheme to URL")
            
            if parsed.scheme not in ['http', 'https', 'ftp', 'ftps']:
                raise ValidationError(f"{field_name}: Unsupported URL scheme: {parsed.scheme}")
            
            # Check for suspicious patterns
            if any(pattern in url.lower() for pattern in ['javascript:', 'data:', 'vbscript:']):
                raise ValidationError(f"{field_name}: Potentially dangerous URL scheme")
            
            # Length validation
            if len(url) > 2048:
                raise ValidationError(f"{field_name}: URL too long (max 2048 characters)")
            
        except Exception as e:
            raise ValidationError(f"{field_name}: Invalid URL format: {str(e)}")
        
        was_modified = url != original_url
        
        return SanitizationResult(url, was_modified, warnings)
    
    def _validate_html(self, value: Any, field_name: str) -> SanitizationResult:
        """Validate and sanitize HTML input."""
        if not value:
            return SanitizationResult("")
        
        html_content = str(value)
        original_content = html_content
        warnings = []
        
        # Check for XSS patterns
        xss_threats = []
        for pattern in self.xss_patterns:
            if re.search(pattern, html_content):
                xss_threats.append(pattern)
        
        if xss_threats:
            warnings.extend([f"Potential XSS pattern detected: {pattern}" for pattern in xss_threats])
        
        # Basic HTML sanitization (remove dangerous tags and attributes)
        # This is a simplified version - in production, use a library like bleach
        html_content = self._sanitize_html_tags(html_content)
        
        was_modified = html_content != original_content
        
        return SanitizationResult(html_content, was_modified, warnings)
    
    def _sanitize_html_tags(self, html_content: str) -> str:
        """Sanitize HTML by removing dangerous tags and attributes."""
        # Remove script tags and their content
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove dangerous tags
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input', 'button', 'link', 'meta', 'style']
        for tag in dangerous_tags:
            html_content = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
            html_content = re.sub(f'<{tag}[^>]*/?>', '', html_content, flags=re.IGNORECASE)
        
        # Remove dangerous attributes
        html_content = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'javascript:', '', html_content, flags=re.IGNORECASE)
        
        return html_content
    
    def _validate_json(self, value: Any, field_name: str) -> SanitizationResult:
        """Validate and sanitize JSON input."""
        if not value:
            return SanitizationResult({})
        
        warnings = []
        
        try:
            if isinstance(value, str):
                # Parse JSON string
                json_data = json.loads(value)
            elif isinstance(value, (dict, list)):
                # Already parsed JSON
                json_data = value
            else:
                raise ValidationError(f"{field_name}: Invalid JSON data type")
            
            # Validate JSON structure doesn't contain dangerous patterns
            json_str = json.dumps(json_data)
            threats = self._detect_security_threats(json_str)
            if threats:
                warnings.extend([f"Security threat in JSON: {threat}" for threat in threats])
            
            return SanitizationResult(json_data, False, warnings)
            
        except json.JSONDecodeError as e:
            raise ValidationError(f"{field_name}: Invalid JSON format: {str(e)}")
    
    def _validate_number(self, value: Any, field_name: str) -> SanitizationResult:
        """Validate and sanitize numeric input."""
        if value is None:
            return SanitizationResult(0)
        
        try:
            if isinstance(value, str):
                # Try to parse as number
                if '.' in value:
                    num_value = float(value)
                else:
                    num_value = int(value)
            elif isinstance(value, (int, float)):
                num_value = value
            else:
                raise ValidationError(f"{field_name}: Cannot convert to number")
            
            # Check for reasonable bounds
            if abs(num_value) > 1e15:  # Very large number
                raise ValidationError(f"{field_name}: Number too large")
            
            return SanitizationResult(num_value)
            
        except (ValueError, OverflowError) as e:
            raise ValidationError(f"{field_name}: Invalid number format: {str(e)}")
    
    def _validate_boolean(self, value: Any, field_name: str) -> SanitizationResult:
        """Validate and sanitize boolean input."""
        if isinstance(value, bool):
            return SanitizationResult(value)
        
        if isinstance(value, str):
            lower_value = value.lower().strip()
            if lower_value in ['true', '1', 'yes', 'on']:
                return SanitizationResult(True, True)
            elif lower_value in ['false', '0', 'no', 'off', '']:
                return SanitizationResult(False, True)
        
        if isinstance(value, (int, float)):
            return SanitizationResult(bool(value), True)
        
        raise ValidationError(f"{field_name}: Invalid boolean value")
    
    def _validate_object_id(self, value: Any, field_name: str) -> SanitizationResult:
        """Validate and sanitize MongoDB ObjectId input."""
        if not value:
            raise ValidationError(f"{field_name}: ObjectId cannot be empty")
        
        try:
            if isinstance(value, ObjectId):
                return SanitizationResult(value)
            
            # Try to create ObjectId from string
            object_id = ObjectId(str(value))
            return SanitizationResult(object_id, True)
            
        except Exception as e:
            raise ValidationError(f"{field_name}: Invalid ObjectId format: {str(e)}")
    
    def _validate_filename(self, value: Any, field_name: str) -> SanitizationResult:
        """Validate and sanitize filename input."""
        if not value:
            raise ValidationError(f"{field_name}: Filename cannot be empty")
        
        filename = str(value).strip()
        original_filename = filename
        warnings = []
        
        # Remove path traversal attempts
        filename = filename.replace('..', '')
        filename = filename.replace('/', '')
        filename = filename.replace('\\', '')
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*\x00-\x1f]', '', filename)
        
        # Check for reserved names (Windows)
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
        if filename.upper() in reserved_names:
            filename = f"file_{filename}"
            warnings.append("Renamed reserved filename")
        
        # Length validation
        if len(filename) > 255:
            filename = filename[:255]
            warnings.append("Filename truncated to 255 characters")
        
        if not filename:
            raise ValidationError(f"{field_name}: Filename cannot be empty after sanitization")
        
        was_modified = filename != original_filename
        
        return SanitizationResult(filename, was_modified, warnings)
    
    def _validate_sql_safe(self, value: Any, field_name: str) -> SanitizationResult:
        """Validate input for SQL injection safety."""
        if not value:
            return SanitizationResult("")
        
        str_value = str(value)
        warnings = []
        
        # Check for SQL injection patterns
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, str_value):
                raise ValidationError(f"{field_name}: Potentially dangerous SQL pattern detected")
        
        # Additional SQL-specific checks
        dangerous_keywords = ['union', 'select', 'insert', 'delete', 'drop', 'create', 'alter', 'exec', 'execute']
        words = str_value.lower().split()
        
        for word in words:
            if word in dangerous_keywords:
                warnings.append(f"SQL keyword detected: {word}")
        
        return SanitizationResult(str_value, False, warnings)
    
    def _detect_security_threats(self, input_str: str) -> List[str]:
        """Detect various security threats in input string."""
        threats = []
        
        # SQL Injection
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, input_str):
                threats.append("SQL Injection")
                break
        
        # XSS
        for pattern in self.xss_patterns:
            if re.search(pattern, input_str):
                threats.append("Cross-Site Scripting (XSS)")
                break
        
        # Path Traversal
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, input_str):
                threats.append("Path Traversal")
                break
        
        # Command Injection
        for pattern in self.command_injection_patterns:
            if re.search(pattern, input_str):
                threats.append("Command Injection")
                break
        
        return threats
    
    def validate_batch_inputs(self, 
                            inputs: Dict[str, Tuple[Any, str]], 
                            user_id: Optional[ObjectId] = None) -> Dict[str, SanitizationResult]:
        """
        Validate multiple inputs at once.
        
        Args:
            inputs: Dict mapping field_name -> (value, input_type)
            user_id: ID of user making the inputs
        
        Returns:
            Dict mapping field_name -> SanitizationResult
        """
        results = {}
        
        for field_name, (value, input_type) in inputs.items():
            try:
                results[field_name] = self.validate_and_sanitize_input(
                    value, input_type, field_name, user_id
                )
            except ValidationError as e:
                # Store error as failed result
                results[field_name] = SanitizationResult(
                    None, False, [str(e)]
                )
        
        return results
    
    def get_validation_summary(self, results: Dict[str, SanitizationResult]) -> Dict[str, Any]:
        """Get summary of validation results."""
        total_fields = len(results)
        successful_validations = sum(1 for r in results.values() if r.sanitized_value is not None)
        failed_validations = total_fields - successful_validations
        modified_fields = sum(1 for r in results.values() if r.was_modified)
        total_warnings = sum(len(r.warnings) for r in results.values())
        
        failed_fields = {
            field: result.warnings[0] if result.warnings else "Validation failed"
            for field, result in results.items()
            if result.sanitized_value is None
        }
        
        return {
            'total_fields': total_fields,
            'successful_validations': successful_validations,
            'failed_validations': failed_validations,
            'modified_fields': modified_fields,
            'total_warnings': total_warnings,
            'success_rate': (successful_validations / total_fields * 100) if total_fields > 0 else 100,
            'failed_fields': failed_fields
        }