"""
Settings Validator for configuration management
Handles input validation and error handling for configuration settings
"""

from typing import Any, Dict, Optional, List, Tuple
from ..models.configuration import AdminSetting


class ValidationResult:
    """Result of configuration validation."""
    
    def __init__(self, is_valid: bool, error_message: Optional[str] = None):
        self.is_valid = is_valid
        self.error_message = error_message
    
    def __bool__(self):
        return self.is_valid
    
    def __str__(self):
        if self.is_valid:
            return "Valid"
        return f"Invalid: {self.error_message}"


class SettingsValidator:
    """Validator for configuration settings with comprehensive validation rules."""
    
    def __init__(self):
        self.custom_validators = {}
    
    def validate_setting(self, setting: AdminSetting, value: Any) -> ValidationResult:
        """Validate a value against a setting's validation rules."""
        return self.validate_value(value, setting.validation_rules, setting.key)
    
    def validate_value(self, value: Any, validation_rules: Dict[str, Any], setting_key: str = "") -> ValidationResult:
        """Validate a value against validation rules."""
        if not validation_rules:
            return ValidationResult(True)
        
        # Type validation
        if 'type' in validation_rules:
            type_result = self._validate_type(value, validation_rules['type'])
            if not type_result.is_valid:
                return type_result
        
        # Range validation for numbers
        if isinstance(value, (int, float)):
            range_result = self._validate_number_range(value, validation_rules)
            if not range_result.is_valid:
                return range_result
        
        # Length validation for strings
        if isinstance(value, str):
            length_result = self._validate_string_length(value, validation_rules)
            if not length_result.is_valid:
                return length_result
        
        # Pattern validation for strings
        if isinstance(value, str) and 'pattern' in validation_rules:
            pattern_result = self._validate_pattern(value, validation_rules['pattern'])
            if not pattern_result.is_valid:
                return pattern_result
        
        # Allowed values validation
        if 'allowed_values' in validation_rules:
            allowed_result = self._validate_allowed_values(value, validation_rules['allowed_values'])
            if not allowed_result.is_valid:
                return allowed_result
        
        # Custom validation
        if setting_key in self.custom_validators:
            custom_result = self.custom_validators[setting_key](value)
            if not custom_result.is_valid:
                return custom_result
        
        return ValidationResult(True)
    
    def _validate_type(self, value: Any, expected_type: str) -> ValidationResult:
        """Validate the type of a value."""
        type_mapping = {
            'string': str,
            'number': (int, float),
            'integer': int,
            'float': float,
            'boolean': bool,
            'list': list,
            'dict': dict
        }
        
        if expected_type not in type_mapping:
            return ValidationResult(False, f"Unknown type '{expected_type}'")
        
        expected_python_type = type_mapping[expected_type]
        
        if not isinstance(value, expected_python_type):
            actual_type = type(value).__name__
            return ValidationResult(False, f"Expected {expected_type}, got {actual_type}")
        
        return ValidationResult(True)
    
    def _validate_number_range(self, value: float, validation_rules: Dict[str, Any]) -> ValidationResult:
        """Validate number range constraints."""
        if 'min' in validation_rules and value < validation_rules['min']:
            return ValidationResult(False, f"Value {value} is below minimum {validation_rules['min']}")
        
        if 'max' in validation_rules and value > validation_rules['max']:
            return ValidationResult(False, f"Value {value} is above maximum {validation_rules['max']}")
        
        return ValidationResult(True)
    
    def _validate_string_length(self, value: str, validation_rules: Dict[str, Any]) -> ValidationResult:
        """Validate string length constraints."""
        if 'min_length' in validation_rules and len(value) < validation_rules['min_length']:
            return ValidationResult(False, f"String length {len(value)} is below minimum {validation_rules['min_length']}")
        
        if 'max_length' in validation_rules and len(value) > validation_rules['max_length']:
            return ValidationResult(False, f"String length {len(value)} is above maximum {validation_rules['max_length']}")
        
        return ValidationResult(True)
    
    def _validate_pattern(self, value: str, pattern: str) -> ValidationResult:
        """Validate string against a regex pattern."""
        import re
        try:
            if not re.match(pattern, value):
                return ValidationResult(False, f"Value '{value}' does not match required pattern")
        except re.error as e:
            return ValidationResult(False, f"Invalid regex pattern: {e}")
        
        return ValidationResult(True)
    
    def _validate_allowed_values(self, value: Any, allowed_values: List[Any]) -> ValidationResult:
        """Validate that value is in the list of allowed values."""
        if value not in allowed_values:
            return ValidationResult(False, f"Value {value} not in allowed values: {allowed_values}")
        
        return ValidationResult(True)
    
    def register_custom_validator(self, setting_key: str, validator_func) -> None:
        """Register a custom validator function for a specific setting."""
        self.custom_validators[setting_key] = validator_func
    
    def validate_multiple_settings(self, settings_values: Dict[str, Tuple[AdminSetting, Any]]) -> Dict[str, ValidationResult]:
        """Validate multiple settings at once."""
        results = {}
        for key, (setting, value) in settings_values.items():
            results[key] = self.validate_setting(setting, value)
        return results
    
    def get_validation_summary(self, validation_results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Get a summary of validation results."""
        valid_count = sum(1 for result in validation_results.values() if result.is_valid)
        invalid_count = len(validation_results) - valid_count
        
        invalid_settings = {
            key: result.error_message 
            for key, result in validation_results.items() 
            if not result.is_valid
        }
        
        return {
            'total_settings': len(validation_results),
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'is_all_valid': invalid_count == 0,
            'invalid_settings': invalid_settings
        }