"""
Integration models for external service management
"""

from datetime import datetime
from typing import Any, Dict, Optional, List
from enum import Enum
from bson import ObjectId
from .base import BaseModel


class IntegrationType(Enum):
    """Types of integrations supported."""
    PAYMENT_GATEWAY = "payment_gateway"
    SHIPPING_API = "shipping_api"
    EMAIL_SERVICE = "email_service"
    SOCIAL_MEDIA = "social_media"
    ANALYTICS = "analytics"
    OTHER = "other"


class IntegrationStatus(Enum):
    """Status of an integration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    ERROR = "error"
    PENDING = "pending"


class Integration(BaseModel):
    """Model for external service integrations."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name: str = kwargs.get('name', '')
        self.type: IntegrationType = IntegrationType(kwargs.get('type', IntegrationType.OTHER.value))
        self.status: IntegrationStatus = IntegrationStatus(kwargs.get('status', IntegrationStatus.INACTIVE.value))
        self.provider: str = kwargs.get('provider', '')
        self.config: Dict[str, Any] = kwargs.get('config', {})
        self.credentials: Dict[str, str] = kwargs.get('credentials', {})
        self.webhook_url: Optional[str] = kwargs.get('webhook_url')
        self.test_mode: bool = kwargs.get('test_mode', True)
        self.last_tested: Optional[datetime] = kwargs.get('last_tested')
        self.test_results: Dict[str, Any] = kwargs.get('test_results', {})
        self.error_message: Optional[str] = kwargs.get('error_message')


class PaymentGateway(BaseModel):
    """Model for payment gateway configurations."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name: str = kwargs.get('name', '')
        self.provider: str = kwargs.get('provider', '')  # stripe, paypal, square, etc.
        self.is_active: bool = kwargs.get('is_active', False)
        self.is_test_mode: bool = kwargs.get('is_test_mode', True)
        self.public_key: str = kwargs.get('public_key', '')
        self.private_key: str = kwargs.get('private_key', '')
        self.webhook_secret: str = kwargs.get('webhook_secret', '')
        self.supported_currencies: List[str] = kwargs.get('supported_currencies', ['USD'])
        self.supported_methods: List[str] = kwargs.get('supported_methods', ['card'])
        self.fees: Dict[str, float] = kwargs.get('fees', {})
        self.last_test_transaction: Optional[datetime] = kwargs.get('last_test_transaction')
        self.test_results: Dict[str, Any] = kwargs.get('test_results', {})


class ShippingProvider(BaseModel):
    """Model for shipping provider configurations."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name: str = kwargs.get('name', '')
        self.provider: str = kwargs.get('provider', '')  # fedex, ups, usps, dhl, etc.
        self.is_active: bool = kwargs.get('is_active', False)
        self.api_key: str = kwargs.get('api_key', '')
        self.api_secret: str = kwargs.get('api_secret', '')
        self.account_number: str = kwargs.get('account_number', '')
        self.test_mode: bool = kwargs.get('test_mode', True)
        self.supported_services: List[str] = kwargs.get('supported_services', [])
        self.rate_calculation_enabled: bool = kwargs.get('rate_calculation_enabled', True)
        self.tracking_enabled: bool = kwargs.get('tracking_enabled', True)
        self.label_printing_enabled: bool = kwargs.get('label_printing_enabled', False)
        self.last_rate_test: Optional[datetime] = kwargs.get('last_rate_test')
        self.test_results: Dict[str, Any] = kwargs.get('test_results', {})


class EmailService(BaseModel):
    """Model for email service configurations."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name: str = kwargs.get('name', '')
        self.provider: str = kwargs.get('provider', '')  # smtp, sendgrid, mailgun, ses, etc.
        self.is_active: bool = kwargs.get('is_active', False)
        self.smtp_host: str = kwargs.get('smtp_host', '')
        self.smtp_port: int = kwargs.get('smtp_port', 587)
        self.smtp_username: str = kwargs.get('smtp_username', '')
        self.smtp_password: str = kwargs.get('smtp_password', '')
        self.use_tls: bool = kwargs.get('use_tls', True)
        self.use_ssl: bool = kwargs.get('use_ssl', False)
        self.from_email: str = kwargs.get('from_email', '')
        self.from_name: str = kwargs.get('from_name', '')
        self.api_key: str = kwargs.get('api_key', '')
        self.templates: Dict[str, str] = kwargs.get('templates', {})
        self.last_test_email: Optional[datetime] = kwargs.get('last_test_email')
        self.test_results: Dict[str, Any] = kwargs.get('test_results', {})


class SocialMediaAccount(BaseModel):
    """Model for social media account integrations."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.platform: str = kwargs.get('platform', '')  # facebook, twitter, instagram, etc.
        self.account_name: str = kwargs.get('account_name', '')
        self.account_id: str = kwargs.get('account_id', '')
        self.is_active: bool = kwargs.get('is_active', False)
        self.access_token: str = kwargs.get('access_token', '')
        self.refresh_token: str = kwargs.get('refresh_token', '')
        self.token_expires_at: Optional[datetime] = kwargs.get('token_expires_at')
        self.permissions: List[str] = kwargs.get('permissions', [])
        self.auto_post_enabled: bool = kwargs.get('auto_post_enabled', False)
        self.sync_enabled: bool = kwargs.get('sync_enabled', False)
        self.last_sync: Optional[datetime] = kwargs.get('last_sync')
        self.sync_results: Dict[str, Any] = kwargs.get('sync_results', {})


class APIUsageMetric(BaseModel):
    """Model for API usage tracking."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.integration_id: ObjectId = kwargs.get('integration_id')
        self.endpoint: str = kwargs.get('endpoint', '')
        self.method: str = kwargs.get('method', 'GET')
        self.status_code: int = kwargs.get('status_code', 200)
        self.response_time: float = kwargs.get('response_time', 0.0)
        self.request_size: int = kwargs.get('request_size', 0)
        self.response_size: int = kwargs.get('response_size', 0)
        self.error_message: Optional[str] = kwargs.get('error_message')
        self.timestamp: datetime = kwargs.get('timestamp', datetime.utcnow())
        self.user_agent: str = kwargs.get('user_agent', '')
        self.ip_address: str = kwargs.get('ip_address', '')