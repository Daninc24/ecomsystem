"""
API Usage Monitor for statistics and performance tracking
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from ..models.integration import APIUsageMetric
from .base_service import BaseService


class APIUsageMonitor(BaseService):
    """Monitors API usage statistics and performance metrics for integrations."""
    
    def _get_collection_name(self) -> str:
        return "api_usage_metrics"
    
    def __init__(self, mongo_db):
        super().__init__(mongo_db)
        self.integration_collection = self.db.integrations
    
    def record_api_call(self, integration_id: ObjectId, call_data: Dict[str, Any]) -> ObjectId:
        """Record an API call for usage tracking."""
        metric_data = {
            'integration_id': integration_id,
            'endpoint': call_data.get('endpoint', ''),
            'method': call_data.get('method', 'GET'),
            'status_code': call_data.get('status_code', 200),
            'response_time': call_data.get('response_time', 0.0),
            'request_size': call_data.get('request_size', 0),
            'response_size': call_data.get('response_size', 0),
            'error_message': call_data.get('error_message'),
            'timestamp': call_data.get('timestamp', datetime.utcnow()),
            'user_agent': call_data.get('user_agent', ''),
            'ip_address': call_data.get('ip_address', '')
        }
        
        metric = APIUsageMetric(**metric_data)
        return self.create(metric.to_dict())
    
    def get_usage_statistics(self, integration_id: ObjectId, 
                           date_range: Optional[Dict[str, datetime]] = None) -> Dict[str, Any]:
        """Get comprehensive usage statistics for an integration."""
        # Set default date range to last 30 days
        if not date_range:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            date_range = {'start': start_date, 'end': end_date}
        
        query = {
            'integration_id': integration_id,
            'timestamp': {
                '$gte': date_range['start'],
                '$lte': date_range['end']
            }
        }
        
        metrics = self.find(query)
        
        if not metrics:
            return {
                'integration_id': str(integration_id),
                'date_range': date_range,
                'total_calls': 0,
                'statistics': {}
            }
        
        # Calculate comprehensive statistics
        stats = self._calculate_usage_statistics(metrics)
        stats.update({
            'integration_id': str(integration_id),
            'date_range': date_range,
            'total_calls': len(metrics)
        })
        
        return stats
    
    def get_performance_metrics(self, integration_id: ObjectId, 
                               date_range: Optional[Dict[str, datetime]] = None) -> Dict[str, Any]:
        """Get performance metrics for an integration."""
        if not date_range:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)  # Last 7 days for performance
            date_range = {'start': start_date, 'end': end_date}
        
        query = {
            'integration_id': integration_id,
            'timestamp': {
                '$gte': date_range['start'],
                '$lte': date_range['end']
            }
        }
        
        metrics = self.find(query, sort=[('timestamp', 1)])
        
        if not metrics:
            return {
                'integration_id': str(integration_id),
                'date_range': date_range,
                'performance_metrics': {}
            }
        
        performance = self._calculate_performance_metrics(metrics)
        performance.update({
            'integration_id': str(integration_id),
            'date_range': date_range
        })
        
        return performance
    
    def get_error_analysis(self, integration_id: ObjectId, 
                          date_range: Optional[Dict[str, datetime]] = None) -> Dict[str, Any]:
        """Get error analysis for an integration."""
        if not date_range:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
            date_range = {'start': start_date, 'end': end_date}
        
        query = {
            'integration_id': integration_id,
            'timestamp': {
                '$gte': date_range['start'],
                '$lte': date_range['end']
            },
            'status_code': {'$gte': 400}  # Error status codes
        }
        
        error_metrics = self.find(query, sort=[('timestamp', -1)])
        
        error_analysis = self._analyze_errors(error_metrics)
        error_analysis.update({
            'integration_id': str(integration_id),
            'date_range': date_range,
            'total_errors': len(error_metrics)
        })
        
        return error_analysis
    
    def get_usage_trends(self, integration_id: ObjectId, 
                        period: str = 'daily', days: int = 30) -> Dict[str, Any]:
        """Get usage trends over time."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        query = {
            'integration_id': integration_id,
            'timestamp': {
                '$gte': start_date,
                '$lte': end_date
            }
        }
        
        metrics = self.find(query, sort=[('timestamp', 1)])
        
        trends = self._calculate_usage_trends(metrics, period)
        trends.update({
            'integration_id': str(integration_id),
            'period': period,
            'days': days
        })
        
        return trends
    
    def get_top_endpoints(self, integration_id: ObjectId, 
                         date_range: Optional[Dict[str, datetime]] = None, 
                         limit: int = 10) -> Dict[str, Any]:
        """Get most frequently used endpoints."""
        if not date_range:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            date_range = {'start': start_date, 'end': end_date}
        
        query = {
            'integration_id': integration_id,
            'timestamp': {
                '$gte': date_range['start'],
                '$lte': date_range['end']
            }
        }
        
        metrics = self.find(query)
        
        endpoint_stats = self._analyze_endpoint_usage(metrics, limit)
        endpoint_stats.update({
            'integration_id': str(integration_id),
            'date_range': date_range,
            'limit': limit
        })
        
        return endpoint_stats
    
    def get_rate_limit_analysis(self, integration_id: ObjectId, 
                               date_range: Optional[Dict[str, datetime]] = None) -> Dict[str, Any]:
        """Analyze rate limiting patterns."""
        if not date_range:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
            date_range = {'start': start_date, 'end': end_date}
        
        query = {
            'integration_id': integration_id,
            'timestamp': {
                '$gte': date_range['start'],
                '$lte': date_range['end']
            },
            'status_code': 429  # Rate limit exceeded
        }
        
        rate_limit_metrics = self.find(query, sort=[('timestamp', 1)])
        
        analysis = self._analyze_rate_limits(rate_limit_metrics)
        analysis.update({
            'integration_id': str(integration_id),
            'date_range': date_range,
            'rate_limit_hits': len(rate_limit_metrics)
        })
        
        return analysis
    
    def get_integration_health_score(self, integration_id: ObjectId) -> Dict[str, Any]:
        """Calculate overall health score for an integration."""
        # Get metrics from last 24 hours
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=24)
        
        query = {
            'integration_id': integration_id,
            'timestamp': {
                '$gte': start_date,
                '$lte': end_date
            }
        }
        
        metrics = self.find(query)
        
        if not metrics:
            return {
                'integration_id': str(integration_id),
                'health_score': 100.0,
                'status': 'healthy',
                'message': 'No recent API calls to analyze'
            }
        
        health_score = self._calculate_health_score(metrics)
        
        return {
            'integration_id': str(integration_id),
            'health_score': health_score['score'],
            'status': health_score['status'],
            'factors': health_score['factors'],
            'recommendations': health_score['recommendations']
        }
    
    def cleanup_old_metrics(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """Clean up old API usage metrics."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        query = {'timestamp': {'$lt': cutoff_date}}
        
        # Count records to be deleted
        count_to_delete = self.count(query)
        
        # Delete old records
        result = self.collection.delete_many(query)
        
        return {
            'success': True,
            'records_deleted': result.deleted_count,
            'cutoff_date': cutoff_date,
            'days_kept': days_to_keep
        }
    
    def _calculate_usage_statistics(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive usage statistics."""
        if not metrics:
            return {}
        
        total_calls = len(metrics)
        successful_calls = len([m for m in metrics if m.get('status_code', 200) < 400])
        error_calls = total_calls - successful_calls
        
        response_times = [m.get('response_time', 0) for m in metrics if m.get('response_time')]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Status code distribution
        status_codes = {}
        for metric in metrics:
            code = metric.get('status_code', 200)
            status_codes[code] = status_codes.get(code, 0) + 1
        
        # Method distribution
        methods = {}
        for metric in metrics:
            method = metric.get('method', 'GET')
            methods[method] = methods.get(method, 0) + 1
        
        return {
            'success_rate': (successful_calls / total_calls) * 100 if total_calls > 0 else 0,
            'error_rate': (error_calls / total_calls) * 100 if total_calls > 0 else 0,
            'average_response_time': round(avg_response_time, 3),
            'status_code_distribution': status_codes,
            'method_distribution': methods,
            'total_data_transferred': {
                'requests': sum(m.get('request_size', 0) for m in metrics),
                'responses': sum(m.get('response_size', 0) for m in metrics)
            }
        }
    
    def _calculate_performance_metrics(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance metrics."""
        if not metrics:
            return {}
        
        response_times = [m.get('response_time', 0) for m in metrics if m.get('response_time')]
        
        if not response_times:
            return {'performance_metrics': {}}
        
        response_times.sort()
        count = len(response_times)
        
        return {
            'performance_metrics': {
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'avg_response_time': sum(response_times) / count,
                'median_response_time': response_times[count // 2],
                'p95_response_time': response_times[int(count * 0.95)] if count > 0 else 0,
                'p99_response_time': response_times[int(count * 0.99)] if count > 0 else 0,
                'total_samples': count
            }
        }
    
    def _analyze_errors(self, error_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze error patterns."""
        if not error_metrics:
            return {'error_analysis': {}}
        
        # Group by status code
        error_by_status = {}
        error_by_endpoint = {}
        error_messages = {}
        
        for metric in error_metrics:
            status = metric.get('status_code', 500)
            endpoint = metric.get('endpoint', 'unknown')
            message = metric.get('error_message', 'No message')
            
            error_by_status[status] = error_by_status.get(status, 0) + 1
            error_by_endpoint[endpoint] = error_by_endpoint.get(endpoint, 0) + 1
            
            if message and message != 'No message':
                error_messages[message] = error_messages.get(message, 0) + 1
        
        return {
            'error_analysis': {
                'errors_by_status_code': error_by_status,
                'errors_by_endpoint': dict(sorted(error_by_endpoint.items(), key=lambda x: x[1], reverse=True)[:10]),
                'common_error_messages': dict(sorted(error_messages.items(), key=lambda x: x[1], reverse=True)[:5]),
                'most_recent_errors': [
                    {
                        'timestamp': m.get('timestamp'),
                        'endpoint': m.get('endpoint'),
                        'status_code': m.get('status_code'),
                        'error_message': m.get('error_message')
                    }
                    for m in error_metrics[:5]
                ]
            }
        }
    
    def _calculate_usage_trends(self, metrics: List[Dict[str, Any]], period: str) -> Dict[str, Any]:
        """Calculate usage trends over time."""
        if not metrics:
            return {'trends': []}
        
        # Group metrics by time period
        trends = {}
        
        for metric in metrics:
            timestamp = metric.get('timestamp')
            if not timestamp:
                continue
            
            if period == 'hourly':
                key = timestamp.strftime('%Y-%m-%d %H:00')
            elif period == 'daily':
                key = timestamp.strftime('%Y-%m-%d')
            elif period == 'weekly':
                # Get start of week (Monday)
                start_of_week = timestamp - timedelta(days=timestamp.weekday())
                key = start_of_week.strftime('%Y-%m-%d')
            else:
                key = timestamp.strftime('%Y-%m-%d')
            
            if key not in trends:
                trends[key] = {
                    'period': key,
                    'total_calls': 0,
                    'successful_calls': 0,
                    'error_calls': 0,
                    'avg_response_time': 0,
                    'response_times': []
                }
            
            trends[key]['total_calls'] += 1
            
            if metric.get('status_code', 200) < 400:
                trends[key]['successful_calls'] += 1
            else:
                trends[key]['error_calls'] += 1
            
            if metric.get('response_time'):
                trends[key]['response_times'].append(metric['response_time'])
        
        # Calculate averages
        for trend in trends.values():
            if trend['response_times']:
                trend['avg_response_time'] = sum(trend['response_times']) / len(trend['response_times'])
            del trend['response_times']  # Remove raw data
        
        return {
            'trends': sorted(trends.values(), key=lambda x: x['period'])
        }
    
    def _analyze_endpoint_usage(self, metrics: List[Dict[str, Any]], limit: int) -> Dict[str, Any]:
        """Analyze endpoint usage patterns."""
        if not metrics:
            return {'top_endpoints': []}
        
        endpoint_stats = {}
        
        for metric in metrics:
            endpoint = metric.get('endpoint', 'unknown')
            
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {
                    'endpoint': endpoint,
                    'total_calls': 0,
                    'successful_calls': 0,
                    'error_calls': 0,
                    'avg_response_time': 0,
                    'response_times': []
                }
            
            stats = endpoint_stats[endpoint]
            stats['total_calls'] += 1
            
            if metric.get('status_code', 200) < 400:
                stats['successful_calls'] += 1
            else:
                stats['error_calls'] += 1
            
            if metric.get('response_time'):
                stats['response_times'].append(metric['response_time'])
        
        # Calculate averages and sort
        for stats in endpoint_stats.values():
            if stats['response_times']:
                stats['avg_response_time'] = sum(stats['response_times']) / len(stats['response_times'])
            del stats['response_times']  # Remove raw data
            
            stats['success_rate'] = (stats['successful_calls'] / stats['total_calls']) * 100 if stats['total_calls'] > 0 else 0
        
        top_endpoints = sorted(endpoint_stats.values(), key=lambda x: x['total_calls'], reverse=True)[:limit]
        
        return {
            'top_endpoints': top_endpoints
        }
    
    def _analyze_rate_limits(self, rate_limit_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze rate limiting patterns."""
        if not rate_limit_metrics:
            return {'rate_limit_analysis': {}}
        
        # Group by hour to find patterns
        hourly_hits = {}
        endpoint_hits = {}
        
        for metric in rate_limit_metrics:
            timestamp = metric.get('timestamp')
            endpoint = metric.get('endpoint', 'unknown')
            
            if timestamp:
                hour_key = timestamp.strftime('%H:00')
                hourly_hits[hour_key] = hourly_hits.get(hour_key, 0) + 1
            
            endpoint_hits[endpoint] = endpoint_hits.get(endpoint, 0) + 1
        
        return {
            'rate_limit_analysis': {
                'hits_by_hour': dict(sorted(hourly_hits.items())),
                'hits_by_endpoint': dict(sorted(endpoint_hits.items(), key=lambda x: x[1], reverse=True)),
                'peak_hour': max(hourly_hits.items(), key=lambda x: x[1])[0] if hourly_hits else None,
                'most_limited_endpoint': max(endpoint_hits.items(), key=lambda x: x[1])[0] if endpoint_hits else None
            }
        }
    
    def _calculate_health_score(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall health score for an integration."""
        if not metrics:
            return {'score': 100.0, 'status': 'healthy', 'factors': {}, 'recommendations': []}
        
        total_calls = len(metrics)
        successful_calls = len([m for m in metrics if m.get('status_code', 200) < 400])
        error_calls = total_calls - successful_calls
        
        # Calculate factors
        success_rate = (successful_calls / total_calls) * 100 if total_calls > 0 else 100
        
        response_times = [m.get('response_time', 0) for m in metrics if m.get('response_time')]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        rate_limit_hits = len([m for m in metrics if m.get('status_code') == 429])
        rate_limit_rate = (rate_limit_hits / total_calls) * 100 if total_calls > 0 else 0
        
        # Calculate health score (0-100)
        health_score = 100.0
        
        # Deduct points for errors
        if success_rate < 95:
            health_score -= (95 - success_rate) * 2
        
        # Deduct points for slow response times
        if avg_response_time > 2.0:
            health_score -= min(20, (avg_response_time - 2.0) * 5)
        
        # Deduct points for rate limiting
        if rate_limit_rate > 0:
            health_score -= rate_limit_rate * 3
        
        health_score = max(0, health_score)
        
        # Determine status
        if health_score >= 90:
            status = 'healthy'
        elif health_score >= 70:
            status = 'warning'
        else:
            status = 'critical'
        
        # Generate recommendations
        recommendations = []
        if success_rate < 95:
            recommendations.append('High error rate detected. Check API credentials and endpoint configurations.')
        if avg_response_time > 2.0:
            recommendations.append('Slow response times detected. Consider optimizing API calls or checking network connectivity.')
        if rate_limit_rate > 0:
            recommendations.append('Rate limiting detected. Consider implementing request throttling or upgrading API plan.')
        
        return {
            'score': round(health_score, 1),
            'status': status,
            'factors': {
                'success_rate': round(success_rate, 1),
                'avg_response_time': round(avg_response_time, 3),
                'rate_limit_rate': round(rate_limit_rate, 1),
                'total_calls': total_calls
            },
            'recommendations': recommendations
        }