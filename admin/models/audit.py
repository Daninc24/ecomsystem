"""
Audit and logging models
"""

from datetime import datetime
from typing import Any, Dict, Optional, List
from bson import ObjectId
from .base import BaseModel


class ActivityLog(BaseModel):
    """Model for user activity audit logs."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_id: ObjectId = kwargs.get('user_id')
        self.action: str = kwargs.get('action', '')
        self.resource_type: str = kwargs.get('resource_type', '')
        self.resource_id: str = kwargs.get('resource_id', '')
        self.details: Dict[str, Any] = kwargs.get('details', {})
        self.ip_address: str = kwargs.get('ip_address', '')
        self.user_agent: str = kwargs.get('user_agent', '')
        self.session_id: str = kwargs.get('session_id', '')
        self.severity: str = kwargs.get('severity', 'info')  # info, warning, error, critical
        self.success: bool = kwargs.get('success', True)
        self.error_message: Optional[str] = kwargs.get('error_message')
    
    def add_detail(self, key: str, value: Any) -> None:
        """Add a detail to the activity log."""
        self.details[key] = value
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the activity."""
        return f"{self.action} on {self.resource_type} {self.resource_id}"


class SystemAlert(BaseModel):
    """Model for system alerts and notifications."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.alert_type: str = kwargs.get('alert_type', '')  # security, performance, error, maintenance
        self.severity: str = kwargs.get('severity', 'info')  # info, warning, error, critical
        self.title: str = kwargs.get('title', '')
        self.message: str = kwargs.get('message', '')
        self.source: str = kwargs.get('source', '')  # system component that generated the alert
        self.is_resolved: bool = kwargs.get('is_resolved', False)
        self.resolved_at: Optional[datetime] = kwargs.get('resolved_at')
        self.resolved_by: Optional[ObjectId] = kwargs.get('resolved_by')
        self.resolution_notes: str = kwargs.get('resolution_notes', '')
        self.metadata: Dict[str, Any] = kwargs.get('metadata', {})
        self.notification_sent: bool = kwargs.get('notification_sent', False)
        self.recipients: List[ObjectId] = kwargs.get('recipients', [])
    
    def resolve(self, user_id: ObjectId, notes: str = '') -> None:
        """Mark the alert as resolved."""
        self.is_resolved = True
        self.resolved_at = datetime.utcnow()
        self.resolved_by = user_id
        self.resolution_notes = notes
        self.updated_at = datetime.utcnow()
    
    def should_notify(self) -> bool:
        """Check if this alert should trigger notifications."""
        return not self.notification_sent and self.severity in ['warning', 'error', 'critical']