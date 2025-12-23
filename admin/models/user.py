"""
User management models for the admin system
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from bson import ObjectId
from .base import BaseModel


class UserRole(Enum):
    """User roles in the system."""
    ADMIN = "admin"
    MODERATOR = "moderator"
    VENDOR = "vendor"
    CUSTOMER = "customer"
    GUEST = "guest"


class UserStatus(Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    BANNED = "banned"


class Permission(Enum):
    """System permissions."""
    # Configuration permissions
    CONFIG_READ = "config_read"
    CONFIG_WRITE = "config_write"
    
    # Content permissions
    CONTENT_READ = "content_read"
    CONTENT_WRITE = "content_write"
    CONTENT_PUBLISH = "content_publish"
    
    # User management permissions
    USER_READ = "user_read"
    USER_WRITE = "user_write"
    USER_DELETE = "user_delete"
    USER_SUSPEND = "user_suspend"
    
    # Product management permissions
    PRODUCT_READ = "product_read"
    PRODUCT_WRITE = "product_write"
    PRODUCT_DELETE = "product_delete"
    
    # Order management permissions
    ORDER_READ = "order_read"
    ORDER_WRITE = "order_write"
    ORDER_REFUND = "order_refund"
    
    # Analytics permissions
    ANALYTICS_READ = "analytics_read"
    ANALYTICS_EXPORT = "analytics_export"
    
    # System permissions
    SYSTEM_MONITOR = "system_monitor"
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_MAINTENANCE = "system_maintenance"


class User(BaseModel):
    """User model for the admin system."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.username: str = kwargs.get('username', '')
        self.email: str = kwargs.get('email', '')
        self.password_hash: str = kwargs.get('password_hash', '')
        self.first_name: str = kwargs.get('first_name', '')
        self.last_name: str = kwargs.get('last_name', '')
        self.role: UserRole = UserRole(kwargs.get('role', UserRole.CUSTOMER.value))
        self.status: UserStatus = UserStatus(kwargs.get('status', UserStatus.ACTIVE.value))
        self.permissions: List[Permission] = [
            Permission(p) for p in kwargs.get('permissions', [])
        ]
        self.last_login: Optional[datetime] = kwargs.get('last_login')
        self.login_attempts: int = kwargs.get('login_attempts', 0)
        self.locked_until: Optional[datetime] = kwargs.get('locked_until')
        self.email_verified: bool = kwargs.get('email_verified', False)
        self.phone: Optional[str] = kwargs.get('phone')
        self.profile_image: Optional[str] = kwargs.get('profile_image')
        self.preferences: Dict[str, Any] = kwargs.get('preferences', {})
        self.metadata: Dict[str, Any] = kwargs.get('metadata', {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for MongoDB storage."""
        data = super().to_dict()
        data['role'] = self.role.value
        data['status'] = self.status.value
        data['permissions'] = [p.value for p in self.permissions]
        return data
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions
    
    def add_permission(self, permission: Permission) -> None:
        """Add a permission to the user."""
        if permission not in self.permissions:
            self.permissions.append(permission)
            self.update_timestamp()
    
    def remove_permission(self, permission: Permission) -> None:
        """Remove a permission from the user."""
        if permission in self.permissions:
            self.permissions.remove(permission)
            self.update_timestamp()
    
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE
    
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return False
    
    def get_full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}".strip()


class UserSession(BaseModel):
    """User session model for authentication management."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_id: ObjectId = kwargs.get('user_id')
        self.session_token: str = kwargs.get('session_token', '')
        self.ip_address: str = kwargs.get('ip_address', '')
        self.user_agent: str = kwargs.get('user_agent', '')
        self.expires_at: datetime = kwargs.get('expires_at')
        self.is_active: bool = kwargs.get('is_active', True)
        self.last_activity: datetime = kwargs.get('last_activity', datetime.utcnow())
        self.login_method: str = kwargs.get('login_method', 'password')
        self.device_info: Dict[str, Any] = kwargs.get('device_info', {})
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if session is valid and active."""
        return self.is_active and not self.is_expired()
    
    def extend_session(self, hours: int = 24) -> None:
        """Extend session expiration time."""
        from datetime import timedelta
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.last_activity = datetime.utcnow()
        self.update_timestamp()


class VendorApplication(BaseModel):
    """Vendor application model for vendor approval workflow."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_id: ObjectId = kwargs.get('user_id')
        self.business_name: str = kwargs.get('business_name', '')
        self.business_type: str = kwargs.get('business_type', '')
        self.business_address: Dict[str, str] = kwargs.get('business_address', {})
        self.tax_id: str = kwargs.get('tax_id', '')
        self.business_license: str = kwargs.get('business_license', '')
        self.contact_person: str = kwargs.get('contact_person', '')
        self.contact_email: str = kwargs.get('contact_email', '')
        self.contact_phone: str = kwargs.get('contact_phone', '')
        self.website: Optional[str] = kwargs.get('website')
        self.product_categories: List[str] = kwargs.get('product_categories', [])
        self.expected_monthly_volume: Optional[int] = kwargs.get('expected_monthly_volume')
        self.documents: List[Dict[str, str]] = kwargs.get('documents', [])
        self.status: str = kwargs.get('status', 'pending')  # pending, approved, rejected, under_review
        self.reviewed_by: Optional[ObjectId] = kwargs.get('reviewed_by')
        self.reviewed_at: Optional[datetime] = kwargs.get('reviewed_at')
        self.review_notes: str = kwargs.get('review_notes', '')
        self.rejection_reason: Optional[str] = kwargs.get('rejection_reason')
    
    def approve(self, reviewer_id: ObjectId, notes: str = '') -> None:
        """Approve the vendor application."""
        self.status = 'approved'
        self.reviewed_by = reviewer_id
        self.reviewed_at = datetime.utcnow()
        self.review_notes = notes
        self.update_timestamp(reviewer_id)
    
    def reject(self, reviewer_id: ObjectId, reason: str, notes: str = '') -> None:
        """Reject the vendor application."""
        self.status = 'rejected'
        self.reviewed_by = reviewer_id
        self.reviewed_at = datetime.utcnow()
        self.rejection_reason = reason
        self.review_notes = notes
        self.update_timestamp(reviewer_id)
    
    def set_under_review(self, reviewer_id: ObjectId) -> None:
        """Set application status to under review."""
        self.status = 'under_review'
        self.reviewed_by = reviewer_id
        self.reviewed_at = datetime.utcnow()
        self.update_timestamp(reviewer_id)


class RolePermissionMapping(BaseModel):
    """Role to permission mapping model."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.role: UserRole = UserRole(kwargs.get('role'))
        self.permissions: List[Permission] = [
            Permission(p) for p in kwargs.get('permissions', [])
        ]
        self.is_default: bool = kwargs.get('is_default', False)
        self.description: str = kwargs.get('description', '')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert role mapping to dictionary for MongoDB storage."""
        data = super().to_dict()
        data['role'] = self.role.value
        data['permissions'] = [p.value for p in self.permissions]
        return data