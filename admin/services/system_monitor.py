"""
System monitoring service for server health and performance tracking
"""

import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from bson import ObjectId

from .base_service import BaseService
from ..models.system import SystemMetric, SystemHealth, SystemHealthStatus, SystemAlert, AlertSeverity


class SystemMonitor(BaseService):
    """Service for monitoring system health and performance."""
    
    def _get_collection_name(self) -> str:
        return "system_metrics"
    
    def __init__(self, mongo_db):
        super().__init__(mongo_db)
        self.health_collection = self.db.system_health
        self.alert_collection = self.db.system_alerts
        
        # Performance thresholds
        self.thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'response_time': 2000.0,  # milliseconds
            'error_rate': 5.0  # percentage
        }
    
    def collect_system_metrics(self) -> Dict[str, float]:
        """Collect current system performance metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available = memory.available / (1024**3)  # GB
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free = disk.free / (1024**3)  # GB
            
            # Network metrics (if available)
            try:
                network = psutil.net_io_counters()
                bytes_sent = network.bytes_sent
                bytes_recv = network.bytes_recv
            except:
                bytes_sent = bytes_recv = 0
            
            metrics = {
                'cpu_usage': cpu_percent,
                'cpu_count': cpu_count,
                'memory_usage': memory_percent,
                'memory_available_gb': memory_available,
                'disk_usage': disk_percent,
                'disk_free_gb': disk_free,
                'network_bytes_sent': bytes_sent,
                'network_bytes_recv': bytes_recv,
                'timestamp': time.time()
            }
            
            return metrics
            
        except Exception as e:
            # Log error and return empty metrics
            print(f"Error collecting system metrics: {e}")
            return {}
    
    def store_metrics(self, metrics: Dict[str, float], server_id: str = "default") -> List[ObjectId]:
        """Store system metrics in the database."""
        stored_ids = []
        timestamp = datetime.utcnow()
        
        for metric_name, value in metrics.items():
            if metric_name == 'timestamp':
                continue
                
            metric = SystemMetric(
                metric_name=metric_name,
                value=float(value),
                unit=self._get_metric_unit(metric_name),
                timestamp=timestamp,
                server_id=server_id
            )
            
            metric_id = self.create(metric.to_dict())
            stored_ids.append(metric_id)
        
        return stored_ids
    
    def _get_metric_unit(self, metric_name: str) -> str:
        """Get the unit for a metric."""
        unit_map = {
            'cpu_usage': '%',
            'memory_usage': '%',
            'disk_usage': '%',
            'memory_available_gb': 'GB',
            'disk_free_gb': 'GB',
            'network_bytes_sent': 'bytes',
            'network_bytes_recv': 'bytes',
            'response_time': 'ms',
            'error_rate': '%'
        }
        return unit_map.get(metric_name, '')
    
    def check_system_health(self) -> Dict[str, SystemHealth]:
        """Check overall system health and return status for each component."""
        health_status = {}
        current_metrics = self.collect_system_metrics()
        
        # Check CPU health
        cpu_usage = current_metrics.get('cpu_usage', 0)
        cpu_status = self._determine_health_status('cpu_usage', cpu_usage)
        health_status['cpu'] = SystemHealth(
            component='cpu',
            status=cpu_status,
            message=f"CPU usage: {cpu_usage:.1f}%",
            details={'usage': cpu_usage, 'threshold': self.thresholds['cpu_usage']},
            last_check=datetime.utcnow()
        )
        
        # Check Memory health
        memory_usage = current_metrics.get('memory_usage', 0)
        memory_status = self._determine_health_status('memory_usage', memory_usage)
        health_status['memory'] = SystemHealth(
            component='memory',
            status=memory_status,
            message=f"Memory usage: {memory_usage:.1f}%",
            details={'usage': memory_usage, 'threshold': self.thresholds['memory_usage']},
            last_check=datetime.utcnow()
        )
        
        # Check Disk health
        disk_usage = current_metrics.get('disk_usage', 0)
        disk_status = self._determine_health_status('disk_usage', disk_usage)
        health_status['disk'] = SystemHealth(
            component='disk',
            status=disk_status,
            message=f"Disk usage: {disk_usage:.1f}%",
            details={'usage': disk_usage, 'threshold': self.thresholds['disk_usage']},
            last_check=datetime.utcnow()
        )
        
        # Store health status
        for component, health in health_status.items():
            self.health_collection.replace_one(
                {'component': component},
                health.to_dict(),
                upsert=True
            )
        
        return health_status
    
    def _determine_health_status(self, metric_name: str, value: float) -> SystemHealthStatus:
        """Determine health status based on metric value and thresholds."""
        threshold = self.thresholds.get(metric_name, 100.0)
        
        if value >= threshold:
            return SystemHealthStatus.CRITICAL
        elif value >= threshold * 0.8:
            return SystemHealthStatus.WARNING
        else:
            return SystemHealthStatus.HEALTHY
    
    def generate_alerts(self, health_status: Dict[str, SystemHealth]) -> List[ObjectId]:
        """Generate alerts based on system health status."""
        alert_ids = []
        
        for component, health in health_status.items():
            if health.status in [SystemHealthStatus.WARNING, SystemHealthStatus.CRITICAL]:
                # Check if alert already exists for this component
                existing_alert = self.alert_collection.find_one({
                    'source_component': component,
                    'resolved': False
                })
                
                if not existing_alert:
                    severity = AlertSeverity.HIGH if health.status == SystemHealthStatus.CRITICAL else AlertSeverity.MEDIUM
                    
                    alert = SystemAlert(
                        alert_type='system_health',
                        severity=severity,
                        title=f"{component.upper()} {health.status.value}",
                        message=health.message,
                        source_component=component,
                        current_value=health.details.get('usage'),
                        threshold_value=health.details.get('threshold')
                    )
                    
                    alert_id = ObjectId()
                    alert_data = alert.to_dict()
                    alert_data['_id'] = alert_id
                    
                    self.alert_collection.insert_one(alert_data)
                    alert_ids.append(alert_id)
        
        return alert_ids
    
    def get_metrics_history(self, metric_name: str, hours: int = 24, server_id: str = "default") -> List[Dict[str, Any]]:
        """Get historical metrics for a specific metric."""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = {
            'metric_name': metric_name,
            'server_id': server_id,
            'timestamp': {'$gte': start_time}
        }
        
        return list(self.collection.find(query).sort('timestamp', 1))
    
    def get_current_health_status(self) -> Dict[str, Any]:
        """Get current health status for all components."""
        health_records = list(self.health_collection.find())
        return {record['component']: record for record in health_records}
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active (unresolved) alerts."""
        return list(self.alert_collection.find({'resolved': False}).sort('created_at', -1))
    
    def acknowledge_alert(self, alert_id: ObjectId, user_id: ObjectId) -> bool:
        """Acknowledge an alert."""
        result = self.alert_collection.update_one(
            {'_id': alert_id},
            {
                '$set': {
                    'acknowledged': True,
                    'acknowledged_by': user_id,
                    'acknowledged_at': datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    def resolve_alert(self, alert_id: ObjectId, user_id: ObjectId) -> bool:
        """Resolve an alert."""
        result = self.alert_collection.update_one(
            {'_id': alert_id},
            {
                '$set': {
                    'resolved': True,
                    'resolved_at': datetime.utcnow(),
                    'updated_by': user_id
                }
            }
        )
        return result.modified_count > 0
    
    def run_health_check(self) -> Dict[str, Any]:
        """Run a complete health check and return summary."""
        # Collect current metrics
        metrics = self.collect_system_metrics()
        
        # Store metrics
        if metrics:
            self.store_metrics(metrics)
        
        # Check health status
        health_status = self.check_system_health()
        
        # Generate alerts if needed
        alert_ids = self.generate_alerts(health_status)
        
        return {
            'timestamp': datetime.utcnow(),
            'metrics': metrics,
            'health_status': {k: v.to_dict() for k, v in health_status.items()},
            'new_alerts': len(alert_ids),
            'alert_ids': alert_ids
        }