"""
Real-time metrics collection service
"""

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from bson import ObjectId

from ..models.analytics import AnalyticsMetric
from .base_service import BaseService


class MetricsCollector(BaseService):
    """Service for collecting and storing real-time system metrics."""
    
    def __init__(self, db_client):
        super().__init__(db_client)
        self._metric_cache = {}
        self._cache_ttl = 60  # Cache metrics for 60 seconds
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'analytics_metrics'
    
    def collect_metric(self, metric_name: str, value: float, 
                      dimensions: Dict[str, str] = None,
                      aggregation_period: str = 'hour',
                      metadata: Dict[str, Any] = None) -> AnalyticsMetric:
        """Collect and store a single metric."""
        metric = AnalyticsMetric(
            metric_name=metric_name,
            value=value,
            dimensions=dimensions or {},
            timestamp=datetime.utcnow(),
            aggregation_period=aggregation_period,
            metadata=metadata or {},
            source='system'
        )
        
        # Store in database
        result = self.collection.insert_one(metric.to_dict())
        metric.id = result.inserted_id
        
        # Update cache
        cache_key = f"{metric_name}_{aggregation_period}"
        self._metric_cache[cache_key] = {
            'value': value,
            'timestamp': time.time(),
            'metric': metric
        }
        
        return metric
    
    def collect_sales_metrics(self) -> Dict[str, AnalyticsMetric]:
        """Collect real-time sales metrics."""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        metrics = {}
        
        # Total orders in last hour
        hourly_orders = self.db.orders.count_documents({
            'created_at': {'$gte': hour_ago}
        })
        metrics['orders_hourly'] = self.collect_metric(
            'orders_count', hourly_orders, 
            {'period': 'hour'}, 'hour'
        )
        
        # Total orders in last day
        daily_orders = self.db.orders.count_documents({
            'created_at': {'$gte': day_ago}
        })
        metrics['orders_daily'] = self.collect_metric(
            'orders_count', daily_orders,
            {'period': 'day'}, 'day'
        )
        
        # Revenue in last hour
        hourly_revenue_pipeline = [
            {'$match': {'created_at': {'$gte': hour_ago}}},
            {'$group': {'_id': None, 'total': {'$sum': '$total_amount'}}}
        ]
        hourly_revenue_result = list(self.db.orders.aggregate(hourly_revenue_pipeline))
        hourly_revenue = hourly_revenue_result[0]['total'] if hourly_revenue_result else 0.0
        
        metrics['revenue_hourly'] = self.collect_metric(
            'revenue', hourly_revenue,
            {'period': 'hour', 'currency': 'USD'}, 'hour'
        )
        
        # Revenue in last day
        daily_revenue_pipeline = [
            {'$match': {'created_at': {'$gte': day_ago}}},
            {'$group': {'_id': None, 'total': {'$sum': '$total_amount'}}}
        ]
        daily_revenue_result = list(self.db.orders.aggregate(daily_revenue_pipeline))
        daily_revenue = daily_revenue_result[0]['total'] if daily_revenue_result else 0.0
        
        metrics['revenue_daily'] = self.collect_metric(
            'revenue', daily_revenue,
            {'period': 'day', 'currency': 'USD'}, 'day'
        )
        
        return metrics
    
    def collect_user_metrics(self) -> Dict[str, AnalyticsMetric]:
        """Collect real-time user metrics."""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        metrics = {}
        
        # Active users in last hour
        hourly_active = self.db.user_sessions.count_documents({
            'last_activity': {'$gte': hour_ago}
        })
        metrics['active_users_hourly'] = self.collect_metric(
            'active_users', hourly_active,
            {'period': 'hour'}, 'hour'
        )
        
        # New registrations in last day
        daily_registrations = self.db.users.count_documents({
            'created_at': {'$gte': day_ago}
        })
        metrics['registrations_daily'] = self.collect_metric(
            'new_registrations', daily_registrations,
            {'period': 'day'}, 'day'
        )
        
        # Total users
        total_users = self.db.users.count_documents({})
        metrics['total_users'] = self.collect_metric(
            'total_users', total_users,
            {'period': 'current'}, 'current'
        )
        
        return metrics
    
    def collect_system_metrics(self) -> Dict[str, AnalyticsMetric]:
        """Collect system performance metrics."""
        metrics = {}
        
        # Database collection sizes
        collections = ['orders', 'users', 'products', 'analytics_metrics']
        for collection_name in collections:
            count = self.db[collection_name].count_documents({})
            metrics[f'{collection_name}_count'] = self.collect_metric(
                f'{collection_name}_count', count,
                {'collection': collection_name}, 'current'
            )
        
        # Error rates (simplified - would normally track actual errors)
        error_rate = 0.0  # Placeholder
        metrics['error_rate'] = self.collect_metric(
            'error_rate', error_rate,
            {'period': 'hour'}, 'hour'
        )
        
        return metrics
    
    def get_real_time_metrics(self, metric_names: List[str] = None) -> Dict[str, Any]:
        """Get current real-time metrics with caching."""
        current_time = time.time()
        result = {}
        
        # If no specific metrics requested, get all recent metrics
        if not metric_names:
            # Get latest metrics from last 5 minutes
            five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
            recent_metrics = self.collection.find({
                'timestamp': {'$gte': five_minutes_ago}
            }).sort('timestamp', -1)
            
            for metric_doc in recent_metrics:
                metric = AnalyticsMetric.from_dict(metric_doc)
                key = f"{metric.metric_name}_{metric.aggregation_period}"
                if key not in result:
                    result[key] = {
                        'metric_name': metric.metric_name,
                        'value': metric.value,
                        'dimensions': metric.dimensions,
                        'timestamp': metric.timestamp,
                        'aggregation_period': metric.aggregation_period
                    }
        else:
            # Get specific metrics from cache or database
            for metric_name in metric_names:
                cache_key = f"{metric_name}_hour"
                
                # Check cache first
                if cache_key in self._metric_cache:
                    cached = self._metric_cache[cache_key]
                    if current_time - cached['timestamp'] < self._cache_ttl:
                        result[cache_key] = {
                            'metric_name': cached['metric'].metric_name,
                            'value': cached['metric'].value,
                            'dimensions': cached['metric'].dimensions,
                            'timestamp': cached['metric'].timestamp,
                            'aggregation_period': cached['metric'].aggregation_period
                        }
                        continue
                
                # Get from database
                latest_metric = self.collection.find_one(
                    {'metric_name': metric_name}
                )
                
                if latest_metric:
                    metric = AnalyticsMetric.from_dict(latest_metric)
                    result[cache_key] = {
                        'metric_name': metric.metric_name,
                        'value': metric.value,
                        'dimensions': metric.dimensions,
                        'timestamp': metric.timestamp,
                        'aggregation_period': metric.aggregation_period
                    }
        
        return result
    
    def get_metric_history(self, metric_name: str, 
                          start_date: datetime = None,
                          end_date: datetime = None,
                          aggregation_period: str = 'hour') -> List[AnalyticsMetric]:
        """Get historical data for a specific metric."""
        query = {
            'metric_name': metric_name,
            'aggregation_period': aggregation_period
        }
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter['$gte'] = start_date
            if end_date:
                date_filter['$lte'] = end_date
            query['timestamp'] = date_filter
        
        metrics_data = self.collection.find(query)
        # Sort manually since mock doesn't support sort in find
        all_metrics = list(metrics_data)
        all_metrics.sort(key=lambda x: x.get('timestamp', datetime.min))
        return [AnalyticsMetric.from_dict(metric_doc) for metric_doc in all_metrics]
    
    def collect_all_metrics(self) -> Dict[str, Dict[str, AnalyticsMetric]]:
        """Collect all available real-time metrics."""
        all_metrics = {}
        
        try:
            all_metrics['sales'] = self.collect_sales_metrics()
        except Exception as e:
            print(f"Error collecting sales metrics: {e}")
            all_metrics['sales'] = {}
        
        try:
            all_metrics['users'] = self.collect_user_metrics()
        except Exception as e:
            print(f"Error collecting user metrics: {e}")
            all_metrics['users'] = {}
        
        try:
            all_metrics['system'] = self.collect_system_metrics()
        except Exception as e:
            print(f"Error collecting system metrics: {e}")
            all_metrics['system'] = {}
        
        return all_metrics
    
    def clear_old_metrics(self, days_to_keep: int = 30) -> int:
        """Clear metrics older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        result = self.collection.delete_many({
            'timestamp': {'$lt': cutoff_date}
        })
        return result.deleted_count