"""
Audit logging system for all user management actions
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from bson import ObjectId

from .base_service import BaseService
from ..models.audit import ActivityLog, SystemAlert


class AuditLogger(BaseService):
    """Service for comprehensive audit logging of all admin actions."""
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'activity_logs'
    
    def __init__(self, db):
        super().__init__(db)
        self.activity_logs_collection = db.activity_logs
        self.system_alerts_collection = db.system_alerts
        
        # Configuration
        self.log_retention_days = 365  # Keep logs for 1 year
        self.alert_retention_days = 90  # Keep alerts for 3 months
    
    def log_activity(self, 
                    user_id: Optional[ObjectId],
                    action: str,
                    resource_type: str,
                    resource_id: Optional[str] = None,
                    details: Optional[Dict[str, Any]] = None,
                    ip_address: str = '',
                    user_agent: str = '',
                    session_id: str = '',
                    severity: str = 'info',
                    success: bool = True,
                    error_message: Optional[str] = None) -> ActivityLog:
        """Log a user activity with comprehensive details."""
        
        activity_log = ActivityLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id or '',
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            severity=severity,
            success=success,
            error_message=error_message,
            created_at=datetime.utcnow()
        )
        
        # Insert into database
        result = self.activity_logs_collection.insert_one(activity_log.to_dict())
        activity_log.id = result.inserted_id
        
        # Create system alert for critical failures
        if not success and severity in ['error', 'critical']:
            self._create_failure_alert(activity_log)
        
        return activity_log
    
    def _create_failure_alert(self, activity_log: ActivityLog) -> None:
        """Create a system alert for critical failures."""
        alert = SystemAlert(
            alert_type='security' if 'login' in activity_log.action or 'auth' in activity_log.action else 'error',
            severity=activity_log.severity,
            title=f"Failed Action: {activity_log.action}",
            message=f"Action '{activity_log.action}' failed for {activity_log.resource_type} {activity_log.resource_id}",
            source='audit_logger',
            metadata={
                'activity_log_id': str(activity_log.id),
                'user_id': str(activity_log.user_id) if activity_log.user_id else None,
                'error_message': activity_log.error_message,
                'details': activity_log.details
            },
            created_at=datetime.utcnow()
        )
        
        self.system_alerts_collection.insert_one(alert.to_dict())
    
    def get_user_activity(self, 
                         user_id: ObjectId, 
                         limit: int = 100, 
                         skip: int = 0,
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> List[ActivityLog]:
        """Get activity logs for a specific user."""
        query = {'user_id': user_id}
        
        # Add date range filter
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter['$gte'] = start_date
            if end_date:
                date_filter['$lte'] = end_date
            query['created_at'] = date_filter
        
        cursor = self.activity_logs_collection.find(query).limit(limit).skip(skip).sort('created_at', -1)
        
        activities = []
        for log_data in cursor:
            log_data['id'] = log_data.pop('_id')
            activities.append(ActivityLog(**log_data))
        
        return activities
    
    def get_resource_activity(self, 
                            resource_type: str, 
                            resource_id: str,
                            limit: int = 100,
                            skip: int = 0) -> List[ActivityLog]:
        """Get activity logs for a specific resource."""
        query = {
            'resource_type': resource_type,
            'resource_id': resource_id
        }
        
        cursor = self.activity_logs_collection.find(query).limit(limit).skip(skip).sort('created_at', -1)
        
        activities = []
        for log_data in cursor:
            log_data['id'] = log_data.pop('_id')
            activities.append(ActivityLog(**log_data))
        
        return activities
    
    def get_failed_activities(self, 
                            limit: int = 100,
                            skip: int = 0,
                            hours_back: int = 24) -> List[ActivityLog]:
        """Get recent failed activities."""
        since = datetime.utcnow() - timedelta(hours=hours_back)
        query = {
            'success': False,
            'created_at': {'$gte': since}
        }
        
        cursor = self.activity_logs_collection.find(query).limit(limit).skip(skip).sort('created_at', -1)
        
        activities = []
        for log_data in cursor:
            log_data['id'] = log_data.pop('_id')
            activities.append(ActivityLog(**log_data))
        
        return activities
    
    def get_security_events(self, 
                          limit: int = 100,
                          skip: int = 0,
                          hours_back: int = 24) -> List[ActivityLog]:
        """Get recent security-related events."""
        since = datetime.utcnow() - timedelta(hours=hours_back)
        
        security_actions = [
            'login_failed', 'login_successful', 'logout',
            'user_suspended', 'user_activated', 'user_deleted',
            'permissions_updated', 'role_changed',
            'password_reset_forced', 'account_locked'
        ]
        
        query = {
            'action': {'$in': security_actions},
            'created_at': {'$gte': since}
        }
        
        cursor = self.activity_logs_collection.find(query).limit(limit).skip(skip).sort('created_at', -1)
        
        activities = []
        for log_data in cursor:
            log_data['id'] = log_data.pop('_id')
            activities.append(ActivityLog(**log_data))
        
        return activities
    
    def search_activities(self, 
                         filters: Dict[str, Any],
                         limit: int = 100,
                         skip: int = 0) -> List[ActivityLog]:
        """Search activities with custom filters."""
        cursor = self.activity_logs_collection.find(filters).limit(limit).skip(skip).sort('created_at', -1)
        
        activities = []
        for log_data in cursor:
            log_data['id'] = log_data.pop('_id')
            activities.append(ActivityLog(**log_data))
        
        return activities
    
    def get_activity_statistics(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get activity statistics for the specified time period."""
        since = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Total activities
        total_activities = self.activity_logs_collection.count_documents({
            'created_at': {'$gte': since}
        })
        
        # Failed activities
        failed_activities = self.activity_logs_collection.count_documents({
            'created_at': {'$gte': since},
            'success': False
        })
        
        # Activities by action
        pipeline = [
            {'$match': {'created_at': {'$gte': since}}},
            {'$group': {'_id': '$action', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]
        
        top_actions = {}
        for result in self.activity_logs_collection.aggregate(pipeline):
            top_actions[result['_id']] = result['count']
        
        # Activities by user
        pipeline = [
            {'$match': {'created_at': {'$gte': since}, 'user_id': {'$ne': None}}},
            {'$group': {'_id': '$user_id', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]
        
        top_users = {}
        for result in self.activity_logs_collection.aggregate(pipeline):
            top_users[str(result['_id'])] = result['count']
        
        # Security events
        security_actions = [
            'login_failed', 'login_successful', 'logout',
            'user_suspended', 'user_activated', 'user_deleted'
        ]
        
        security_events = self.activity_logs_collection.count_documents({
            'created_at': {'$gte': since},
            'action': {'$in': security_actions}
        })
        
        return {
            'time_period_hours': hours_back,
            'total_activities': total_activities,
            'failed_activities': failed_activities,
            'success_rate': ((total_activities - failed_activities) / total_activities * 100) if total_activities > 0 else 100,
            'security_events': security_events,
            'top_actions': top_actions,
            'top_users': top_users
        }
    
    def create_system_alert(self,
                          alert_type: str,
                          severity: str,
                          title: str,
                          message: str,
                          source: str = 'system',
                          metadata: Optional[Dict[str, Any]] = None) -> SystemAlert:
        """Create a system alert."""
        alert = SystemAlert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            source=source,
            metadata=metadata or {},
            created_at=datetime.utcnow()
        )
        
        result = self.system_alerts_collection.insert_one(alert.to_dict())
        alert.id = result.inserted_id
        
        return alert
    
    def get_unresolved_alerts(self, limit: int = 50) -> List[SystemAlert]:
        """Get unresolved system alerts."""
        cursor = self.system_alerts_collection.find({
            'is_resolved': False
        }).limit(limit).sort('created_at', -1)
        
        alerts = []
        for alert_data in cursor:
            alert_data['id'] = alert_data.pop('_id')
            alerts.append(SystemAlert(**alert_data))
        
        return alerts
    
    def resolve_alert(self, alert_id: ObjectId, user_id: ObjectId, notes: str = '') -> bool:
        """Resolve a system alert."""
        result = self.system_alerts_collection.update_one(
            {'_id': alert_id},
            {
                '$set': {
                    'is_resolved': True,
                    'resolved_at': datetime.utcnow(),
                    'resolved_by': user_id,
                    'resolution_notes': notes,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            # Log the resolution
            self.log_activity(
                user_id=user_id,
                action='alert_resolved',
                resource_type='system_alert',
                resource_id=str(alert_id),
                details={'resolution_notes': notes}
            )
            return True
        
        return False
    
    def cleanup_old_logs(self) -> Dict[str, int]:
        """Clean up old logs and alerts based on retention policy."""
        now = datetime.utcnow()
        
        # Clean up old activity logs
        log_cutoff = now - timedelta(days=self.log_retention_days)
        log_result = self.activity_logs_collection.delete_many({
            'created_at': {'$lt': log_cutoff}
        })
        
        # Clean up old resolved alerts
        alert_cutoff = now - timedelta(days=self.alert_retention_days)
        alert_result = self.system_alerts_collection.delete_many({
            'created_at': {'$lt': alert_cutoff},
            'is_resolved': True
        })
        
        # Log the cleanup
        self.log_activity(
            user_id=None,
            action='audit_cleanup',
            resource_type='system',
            resource_id='audit_logger',
            details={
                'logs_deleted': log_result.deleted_count,
                'alerts_deleted': alert_result.deleted_count,
                'log_retention_days': self.log_retention_days,
                'alert_retention_days': self.alert_retention_days
            }
        )
        
        return {
            'logs_deleted': log_result.deleted_count,
            'alerts_deleted': alert_result.deleted_count
        }
    
    def export_audit_trail(self, 
                          start_date: datetime,
                          end_date: datetime,
                          user_id: Optional[ObjectId] = None,
                          resource_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Export audit trail for compliance or investigation purposes."""
        query = {
            'created_at': {
                '$gte': start_date,
                '$lte': end_date
            }
        }
        
        if user_id:
            query['user_id'] = user_id
        
        if resource_type:
            query['resource_type'] = resource_type
        
        cursor = self.activity_logs_collection.find(query).sort('created_at', 1)
        
        audit_trail = []
        for log_data in cursor:
            # Convert ObjectId to string for JSON serialization
            log_data['_id'] = str(log_data['_id'])
            if log_data.get('user_id'):
                log_data['user_id'] = str(log_data['user_id'])
            
            audit_trail.append(log_data)
        
        # Log the export
        self.log_activity(
            user_id=user_id,
            action='audit_trail_exported',
            resource_type='audit',
            resource_id='export',
            details={
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'record_count': len(audit_trail),
                'filters': {
                    'user_id': str(user_id) if user_id else None,
                    'resource_type': resource_type
                }
            }
        )
        
        return audit_trail