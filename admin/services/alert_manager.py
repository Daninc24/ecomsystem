"""
Alert management service for monitoring and notifications
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from bson import ObjectId
from enum import Enum

from ..models.base import BaseModel
from .base_service import BaseService


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status values."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertCondition(BaseModel):
    """Model for alert conditions."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name: str = kwargs.get('name', '')
        self.description: str = kwargs.get('description', '')
        self.metric_name: str = kwargs.get('metric_name', '')
        self.condition_type: str = kwargs.get('condition_type', 'threshold')  # threshold, rate, anomaly
        self.threshold_value: float = kwargs.get('threshold_value', 0.0)
        self.comparison_operator: str = kwargs.get('comparison_operator', 'gt')  # gt, lt, eq, gte, lte
        self.time_window_minutes: int = kwargs.get('time_window_minutes', 5)
        self.severity: str = kwargs.get('severity', AlertSeverity.MEDIUM.value)
        self.is_active: bool = kwargs.get('is_active', True)
        self.notification_channels: List[str] = kwargs.get('notification_channels', ['email'])
        self.suppression_duration_minutes: int = kwargs.get('suppression_duration_minutes', 60)
        self.created_by: Optional[ObjectId] = kwargs.get('created_by')


class Alert(BaseModel):
    """Model for alerts."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.condition_id: ObjectId = kwargs.get('condition_id')
        self.condition_name: str = kwargs.get('condition_name', '')
        self.metric_name: str = kwargs.get('metric_name', '')
        self.current_value: float = kwargs.get('current_value', 0.0)
        self.threshold_value: float = kwargs.get('threshold_value', 0.0)
        self.severity: str = kwargs.get('severity', AlertSeverity.MEDIUM.value)
        self.status: str = kwargs.get('status', AlertStatus.ACTIVE.value)
        self.message: str = kwargs.get('message', '')
        self.details: Dict[str, Any] = kwargs.get('details', {})
        self.triggered_at: datetime = kwargs.get('triggered_at', datetime.utcnow())
        self.acknowledged_at: Optional[datetime] = kwargs.get('acknowledged_at')
        self.acknowledged_by: Optional[ObjectId] = kwargs.get('acknowledged_by')
        self.resolved_at: Optional[datetime] = kwargs.get('resolved_at')
        self.resolved_by: Optional[ObjectId] = kwargs.get('resolved_by')
        self.notification_sent: bool = kwargs.get('notification_sent', False)
        self.notification_attempts: int = kwargs.get('notification_attempts', 0)
    
    def acknowledge(self, user_id: ObjectId) -> None:
        """Acknowledge the alert."""
        self.status = AlertStatus.ACKNOWLEDGED.value
        self.acknowledged_at = datetime.utcnow()
        self.acknowledged_by = user_id
        self.updated_at = datetime.utcnow()
    
    def resolve(self, user_id: ObjectId) -> None:
        """Resolve the alert."""
        self.status = AlertStatus.RESOLVED.value
        self.resolved_at = datetime.utcnow()
        self.resolved_by = user_id
        self.updated_at = datetime.utcnow()


class AlertManager(BaseService):
    """Service for managing alerts and monitoring conditions."""
    
    def __init__(self, db_client):
        super().__init__(db_client)
        self._notification_handlers = {}
        self._setup_default_conditions()
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'alerts'
    
    def create_alert_condition(self, name: str, description: str,
                             metric_name: str, condition_type: str,
                             threshold_value: float, comparison_operator: str,
                             time_window_minutes: int = 5,
                             severity: str = AlertSeverity.MEDIUM.value,
                             notification_channels: List[str] = None,
                             user_id: ObjectId = None) -> AlertCondition:
        """Create a new alert condition."""
        condition = AlertCondition(
            name=name,
            description=description,
            metric_name=metric_name,
            condition_type=condition_type,
            threshold_value=threshold_value,
            comparison_operator=comparison_operator,
            time_window_minutes=time_window_minutes,
            severity=severity,
            notification_channels=notification_channels or ['email'],
            created_by=user_id
        )
        
        result = self.db.alert_conditions.insert_one(condition.to_dict())
        condition.id = result.inserted_id
        
        return condition
    
    def check_alert_conditions(self) -> List[Alert]:
        """Check all active alert conditions and generate alerts if needed."""
        alerts_generated = []
        
        # Get all active alert conditions
        conditions_data = self.db.alert_conditions.find({'is_active': True})
        
        for condition_data in conditions_data:
            condition = AlertCondition.from_dict(condition_data)
            
            try:
                alert = self._evaluate_condition(condition)
                if alert:
                    alerts_generated.append(alert)
            except Exception as e:
                print(f"Error evaluating condition {condition.name}: {e}")
        
        return alerts_generated
    
    def create_alert(self, condition: AlertCondition, current_value: float,
                    details: Dict[str, Any] = None) -> Alert:
        """Create a new alert."""
        # Check if there's already an active alert for this condition
        existing_alert = self.collection.find_one({
            'condition_id': condition.id,
            'status': {'$in': [AlertStatus.ACTIVE.value, AlertStatus.ACKNOWLEDGED.value]}
        })
        
        if existing_alert:
            # Update existing alert with new value
            self.collection.update_one(
                {'_id': existing_alert['_id']},
                {'$set': {
                    'current_value': current_value,
                    'updated_at': datetime.utcnow(),
                    'details': details or {}
                }}
            )
            return Alert.from_dict(existing_alert)
        
        # Create new alert
        message = self._generate_alert_message(condition, current_value)
        
        alert = Alert(
            condition_id=condition.id,
            condition_name=condition.name,
            metric_name=condition.metric_name,
            current_value=current_value,
            threshold_value=condition.threshold_value,
            severity=condition.severity,
            message=message,
            details=details or {}
        )
        
        result = self.collection.insert_one(alert.to_dict())
        alert.id = result.inserted_id
        
        # Send notification
        self._send_notification(alert, condition)
        
        return alert
    
    def acknowledge_alert(self, alert_id: ObjectId, user_id: ObjectId) -> bool:
        """Acknowledge an alert."""
        alert_data = self.collection.find_one({'_id': alert_id})
        if not alert_data:
            return False
        
        alert = Alert.from_dict(alert_data)
        alert.acknowledge(user_id)
        
        result = self.collection.update_one(
            {'_id': alert_id},
            {'$set': {
                'status': alert.status,
                'acknowledged_at': alert.acknowledged_at,
                'acknowledged_by': alert.acknowledged_by,
                'updated_at': alert.updated_at
            }}
        )
        
        return result.modified_count > 0
    
    def resolve_alert(self, alert_id: ObjectId, user_id: ObjectId) -> bool:
        """Resolve an alert."""
        alert_data = self.collection.find_one({'_id': alert_id})
        if not alert_data:
            return False
        
        alert = Alert.from_dict(alert_data)
        alert.resolve(user_id)
        
        result = self.collection.update_one(
            {'_id': alert_id},
            {'$set': {
                'status': alert.status,
                'resolved_at': alert.resolved_at,
                'resolved_by': alert.resolved_by,
                'updated_at': alert.updated_at
            }}
        )
        
        return result.modified_count > 0
    
    def get_active_alerts(self, severity: str = None, limit: int = 50) -> List[Alert]:
        """Get active alerts."""
        query = {'status': {'$in': [AlertStatus.ACTIVE.value, AlertStatus.ACKNOWLEDGED.value]}}
        
        if severity:
            query['severity'] = severity
        
        alerts_data = self.collection.find(query).sort('triggered_at', -1).limit(limit)
        return [Alert.from_dict(alert_data) for alert_data in alerts_data]
    
    def get_alert_history(self, start_date: datetime = None,
                         end_date: datetime = None,
                         limit: int = 100) -> List[Alert]:
        """Get alert history."""
        query = {}
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter['$gte'] = start_date
            if end_date:
                date_filter['$lte'] = end_date
            query['triggered_at'] = date_filter
        
        alerts_data = self.collection.find(query).sort('triggered_at', -1).limit(limit)
        return [Alert.from_dict(alert_data) for alert_data in alerts_data]
    
    def get_alert_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get alert statistics for the specified period."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {'$match': {'triggered_at': {'$gte': start_date}}},
            {'$group': {
                '_id': None,
                'total_alerts': {'$sum': 1},
                'alerts_by_severity': {
                    '$push': '$severity'
                },
                'alerts_by_status': {
                    '$push': '$status'
                },
                'avg_resolution_time': {
                    '$avg': {
                        '$subtract': ['$resolved_at', '$triggered_at']
                    }
                }
            }}
        ]
        
        result = list(self.collection.aggregate(pipeline))
        
        if not result:
            return {
                'total_alerts': 0,
                'alerts_by_severity': {},
                'alerts_by_status': {},
                'avg_resolution_time_hours': 0
            }
        
        data = result[0]
        
        # Process severity counts
        severity_counts = {}
        for severity in data.get('alerts_by_severity', []):
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Process status counts
        status_counts = {}
        for status in data.get('alerts_by_status', []):
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Convert resolution time to hours
        avg_resolution_ms = data.get('avg_resolution_time', 0) or 0
        avg_resolution_hours = avg_resolution_ms / (1000 * 60 * 60) if avg_resolution_ms else 0
        
        return {
            'total_alerts': data.get('total_alerts', 0),
            'alerts_by_severity': severity_counts,
            'alerts_by_status': status_counts,
            'avg_resolution_time_hours': round(avg_resolution_hours, 2)
        }
    
    def register_notification_handler(self, channel: str, handler: Callable) -> None:
        """Register a notification handler for a specific channel."""
        self._notification_handlers[channel] = handler
    
    def _evaluate_condition(self, condition: AlertCondition) -> Optional[Alert]:
        """Evaluate a single alert condition."""
        # Get recent metrics for the condition
        time_window_start = datetime.utcnow() - timedelta(minutes=condition.time_window_minutes)
        
        metrics_data = self.db.analytics_metrics.find({
            'metric_name': condition.metric_name,
            'timestamp': {'$gte': time_window_start}
        }).sort('timestamp', -1)
        
        metrics = list(metrics_data)
        if not metrics:
            return None
        
        # Get the latest metric value
        latest_metric = metrics[0]
        current_value = latest_metric.get('value', 0.0)
        
        # Evaluate condition
        condition_met = False
        
        if condition.comparison_operator == 'gt':
            condition_met = current_value > condition.threshold_value
        elif condition.comparison_operator == 'lt':
            condition_met = current_value < condition.threshold_value
        elif condition.comparison_operator == 'eq':
            condition_met = current_value == condition.threshold_value
        elif condition.comparison_operator == 'gte':
            condition_met = current_value >= condition.threshold_value
        elif condition.comparison_operator == 'lte':
            condition_met = current_value <= condition.threshold_value
        
        if condition_met:
            # Check if we should suppress this alert (avoid spam)
            if self._should_suppress_alert(condition):
                return None
            
            details = {
                'metric_data': latest_metric,
                'evaluation_time': datetime.utcnow(),
                'time_window_minutes': condition.time_window_minutes
            }
            
            return self.create_alert(condition, current_value, details)
        
        return None
    
    def _should_suppress_alert(self, condition: AlertCondition) -> bool:
        """Check if alert should be suppressed to avoid spam."""
        suppression_start = datetime.utcnow() - timedelta(minutes=condition.suppression_duration_minutes)
        
        recent_alert = self.collection.find_one({
            'condition_id': condition.id,
            'triggered_at': {'$gte': suppression_start}
        })
        
        return recent_alert is not None
    
    def _generate_alert_message(self, condition: AlertCondition, current_value: float) -> str:
        """Generate a human-readable alert message."""
        operator_text = {
            'gt': 'greater than',
            'lt': 'less than',
            'eq': 'equal to',
            'gte': 'greater than or equal to',
            'lte': 'less than or equal to'
        }
        
        op_text = operator_text.get(condition.comparison_operator, condition.comparison_operator)
        
        return (f"Alert: {condition.name} - "
                f"{condition.metric_name} is {current_value} "
                f"({op_text} threshold of {condition.threshold_value})")
    
    def _send_notification(self, alert: Alert, condition: AlertCondition) -> None:
        """Send notification for an alert."""
        for channel in condition.notification_channels:
            if channel in self._notification_handlers:
                try:
                    self._notification_handlers[channel](alert, condition)
                    # Mark notification as sent
                    self.collection.update_one(
                        {'_id': alert.id},
                        {'$set': {
                            'notification_sent': True,
                            'notification_attempts': alert.notification_attempts + 1
                        }}
                    )
                except Exception as e:
                    print(f"Failed to send notification via {channel}: {e}")
                    # Increment attempt counter
                    self.collection.update_one(
                        {'_id': alert.id},
                        {'$inc': {'notification_attempts': 1}}
                    )
    
    def _setup_default_conditions(self) -> None:
        """Set up default alert conditions."""
        # This would typically be called during system initialization
        # to create standard monitoring conditions
        pass
    
    def _default_email_handler(self, alert: Alert, condition: AlertCondition) -> None:
        """Default email notification handler (placeholder)."""
        # This would integrate with an email service
        print(f"EMAIL ALERT: {alert.message}")
    
    def _default_webhook_handler(self, alert: Alert, condition: AlertCondition) -> None:
        """Default webhook notification handler (placeholder)."""
        # This would send HTTP POST to configured webhook URLs
        print(f"WEBHOOK ALERT: {alert.message}")