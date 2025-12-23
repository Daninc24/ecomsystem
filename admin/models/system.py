"""
System monitoring and maintenance models
"""

from datetime import datetime
from typing import Any, Dict, Optional, List
from enum import Enum
from bson import ObjectId
from .base import BaseModel


class SystemHealthStatus(Enum):
    """System health status enumeration."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"


class BackupStatus(Enum):
    """Backup status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatLevel(Enum):
    """Security threat levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SystemMetric(BaseModel):
    """Model for system performance metrics."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.metric_name: str = kwargs.get('metric_name', '')
        self.value: float = kwargs.get('value', 0.0)
        self.unit: str = kwargs.get('unit', '')
        self.timestamp: datetime = kwargs.get('timestamp', datetime.utcnow())
        self.server_id: str = kwargs.get('server_id', 'default')
        self.metadata: Dict[str, Any] = kwargs.get('metadata', {})


class SystemHealth(BaseModel):
    """Model for system health status."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.component: str = kwargs.get('component', '')
        self.status: SystemHealthStatus = SystemHealthStatus(kwargs.get('status', SystemHealthStatus.HEALTHY.value))
        self.message: str = kwargs.get('message', '')
        self.details: Dict[str, Any] = kwargs.get('details', {})
        self.last_check: datetime = kwargs.get('last_check', datetime.utcnow())


class BackupRecord(BaseModel):
    """Model for backup records."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.backup_type: str = kwargs.get('backup_type', 'full')
        self.status: BackupStatus = BackupStatus(kwargs.get('status', BackupStatus.PENDING.value))
        self.file_path: str = kwargs.get('file_path', '')
        self.file_size: int = kwargs.get('file_size', 0)
        self.started_at: Optional[datetime] = kwargs.get('started_at')
        self.completed_at: Optional[datetime] = kwargs.get('completed_at')
        self.error_message: Optional[str] = kwargs.get('error_message')
        self.metadata: Dict[str, Any] = kwargs.get('metadata', {})


class SecurityEvent(BaseModel):
    """Model for security events and threats."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type: str = kwargs.get('event_type', '')
        self.threat_level: ThreatLevel = ThreatLevel(kwargs.get('threat_level', ThreatLevel.NONE.value))
        self.source_ip: str = kwargs.get('source_ip', '')
        self.user_agent: str = kwargs.get('user_agent', '')
        self.user_id: Optional[ObjectId] = kwargs.get('user_id')
        self.description: str = kwargs.get('description', '')
        self.details: Dict[str, Any] = kwargs.get('details', {})
        self.resolved: bool = kwargs.get('resolved', False)
        self.resolved_at: Optional[datetime] = kwargs.get('resolved_at')


class SystemAlert(BaseModel):
    """Model for system alerts."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.alert_type: str = kwargs.get('alert_type', '')
        self.severity: AlertSeverity = AlertSeverity(kwargs.get('severity', AlertSeverity.LOW.value))
        self.title: str = kwargs.get('title', '')
        self.message: str = kwargs.get('message', '')
        self.source_component: str = kwargs.get('source_component', '')
        self.threshold_value: Optional[float] = kwargs.get('threshold_value')
        self.current_value: Optional[float] = kwargs.get('current_value')
        self.acknowledged: bool = kwargs.get('acknowledged', False)
        self.acknowledged_by: Optional[ObjectId] = kwargs.get('acknowledged_by')
        self.acknowledged_at: Optional[datetime] = kwargs.get('acknowledged_at')
        self.resolved: bool = kwargs.get('resolved', False)
        self.resolved_at: Optional[datetime] = kwargs.get('resolved_at')
        self.metadata: Dict[str, Any] = kwargs.get('metadata', {})


class CacheEntry(BaseModel):
    """Model for cache entries."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.key: str = kwargs.get('key', '')
        self.value: Any = kwargs.get('value')
        self.ttl: int = kwargs.get('ttl', 3600)  # Time to live in seconds
        self.expires_at: datetime = kwargs.get('expires_at', datetime.utcnow())
        self.hit_count: int = kwargs.get('hit_count', 0)
        self.last_accessed: datetime = kwargs.get('last_accessed', datetime.utcnow())


class ConfigurationBackup(BaseModel):
    """Model for configuration backups."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.backup_name: str = kwargs.get('backup_name', '')
        self.configuration_data: Dict[str, Any] = kwargs.get('configuration_data', {})
        self.backup_reason: str = kwargs.get('backup_reason', 'manual')
        self.is_automatic: bool = kwargs.get('is_automatic', False)
        self.restored: bool = kwargs.get('restored', False)
        self.restored_at: Optional[datetime] = kwargs.get('restored_at')
        self.restored_by: Optional[ObjectId] = kwargs.get('restored_by')