"""
Predictive analytics engine for trend analysis and recommendations
"""

import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId

from ..models.analytics import AnalyticsMetric
from .base_service import BaseService


class TrendAnalysis:
    """Class for trend analysis results."""
    
    def __init__(self, metric_name: str, trend_direction: str, 
                 trend_strength: float, confidence: float,
                 predicted_values: List[Dict[str, Any]] = None):
        self.metric_name = metric_name
        self.trend_direction = trend_direction  # 'increasing', 'decreasing', 'stable'
        self.trend_strength = trend_strength  # 0.0 to 1.0
        self.confidence = confidence  # 0.0 to 1.0
        self.predicted_values = predicted_values or []


class Recommendation:
    """Class for system recommendations."""
    
    def __init__(self, title: str, description: str, priority: str,
                 category: str, action_items: List[str] = None,
                 supporting_data: Dict[str, Any] = None):
        self.title = title
        self.description = description
        self.priority = priority  # 'low', 'medium', 'high', 'critical'
        self.category = category  # 'performance', 'sales', 'users', 'system'
        self.action_items = action_items or []
        self.supporting_data = supporting_data or {}
        self.created_at = datetime.utcnow()


class PredictiveAnalytics(BaseService):
    """Service for predictive analytics and trend analysis."""
    
    def __init__(self, db_client):
        super().__init__(db_client)
        self.min_data_points = 10  # Minimum data points for analysis
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'predictive_analytics'
    
    def analyze_trend(self, metric_name: str, 
                     days_back: int = 30,
                     prediction_days: int = 7) -> TrendAnalysis:
        """Analyze trend for a specific metric and predict future values."""
        # Get historical data
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        metrics_data = self.db.analytics_metrics.find({
            'metric_name': metric_name,
            'timestamp': {'$gte': start_date}
        }).sort('timestamp', 1)
        
        data_points = [(metric['timestamp'], metric['value']) 
                      for metric in metrics_data]
        
        if len(data_points) < self.min_data_points:
            return TrendAnalysis(
                metric_name=metric_name,
                trend_direction='insufficient_data',
                trend_strength=0.0,
                confidence=0.0
            )
        
        # Calculate trend using linear regression
        trend_direction, trend_strength, confidence = self._calculate_trend(data_points)
        
        # Generate predictions
        predicted_values = self._predict_future_values(
            data_points, prediction_days
        ) if confidence > 0.5 else []
        
        return TrendAnalysis(
            metric_name=metric_name,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            confidence=confidence,
            predicted_values=predicted_values
        )
    
    def analyze_sales_trends(self, days_back: int = 30) -> Dict[str, TrendAnalysis]:
        """Analyze sales-related trends."""
        sales_metrics = ['revenue', 'orders_count', 'avg_order_value']
        trends = {}
        
        for metric in sales_metrics:
            trends[metric] = self.analyze_trend(metric, days_back)
        
        return trends
    
    def analyze_user_trends(self, days_back: int = 30) -> Dict[str, TrendAnalysis]:
        """Analyze user-related trends."""
        user_metrics = ['active_users', 'new_registrations', 'user_retention']
        trends = {}
        
        for metric in user_metrics:
            trends[metric] = self.analyze_trend(metric, days_back)
        
        return trends
    
    def generate_recommendations(self, analysis_period_days: int = 30) -> List[Recommendation]:
        """Generate recommendations based on trend analysis."""
        recommendations = []
        
        # Analyze sales trends
        sales_trends = self.analyze_sales_trends(analysis_period_days)
        recommendations.extend(self._generate_sales_recommendations(sales_trends))
        
        # Analyze user trends
        user_trends = self.analyze_user_trends(analysis_period_days)
        recommendations.extend(self._generate_user_recommendations(user_trends))
        
        # Analyze system performance
        system_recommendations = self._generate_system_recommendations()
        recommendations.extend(system_recommendations)
        
        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 3))
        
        return recommendations
    
    def detect_anomalies(self, metric_name: str, 
                        days_back: int = 30,
                        sensitivity: float = 2.0) -> List[Dict[str, Any]]:
        """Detect anomalies in metric data using statistical methods."""
        # Get historical data
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        metrics_data = list(self.db.analytics_metrics.find({
            'metric_name': metric_name,
            'timestamp': {'$gte': start_date}
        }).sort('timestamp', 1))
        
        if len(metrics_data) < self.min_data_points:
            return []
        
        values = [metric['value'] for metric in metrics_data]
        
        # Calculate mean and standard deviation
        mean_value = sum(values) / len(values)
        variance = sum((x - mean_value) ** 2 for x in values) / len(values)
        std_dev = math.sqrt(variance)
        
        # Detect anomalies (values outside sensitivity * std_dev)
        anomalies = []
        threshold = sensitivity * std_dev
        
        for metric in metrics_data:
            value = metric['value']
            deviation = abs(value - mean_value)
            
            if deviation > threshold:
                anomalies.append({
                    'timestamp': metric['timestamp'],
                    'value': value,
                    'expected_range': {
                        'min': mean_value - threshold,
                        'max': mean_value + threshold
                    },
                    'deviation': deviation,
                    'severity': 'high' if deviation > threshold * 1.5 else 'medium'
                })
        
        return anomalies
    
    def forecast_capacity_needs(self, resource_type: str = 'storage',
                              days_ahead: int = 30) -> Dict[str, Any]:
        """Forecast capacity needs based on current trends."""
        if resource_type == 'storage':
            return self._forecast_storage_needs(days_ahead)
        elif resource_type == 'users':
            return self._forecast_user_capacity(days_ahead)
        elif resource_type == 'orders':
            return self._forecast_order_capacity(days_ahead)
        else:
            return {'error': f'Unknown resource type: {resource_type}'}
    
    def _calculate_trend(self, data_points: List[Tuple[datetime, float]]) -> Tuple[str, float, float]:
        """Calculate trend direction, strength, and confidence using linear regression."""
        if len(data_points) < 2:
            return 'insufficient_data', 0.0, 0.0
        
        # Convert timestamps to numeric values (days since first point)
        first_timestamp = data_points[0][0]
        x_values = [(point[0] - first_timestamp).total_seconds() / 86400 
                   for point in data_points]
        y_values = [point[1] for point in data_points]
        
        n = len(data_points)
        
        # Calculate linear regression coefficients
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        # Slope (trend strength and direction)
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 'stable', 0.0, 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        
        # Calculate correlation coefficient (confidence)
        mean_x = sum_x / n
        mean_y = sum_y / n
        
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values))
        denominator_x = sum((x - mean_x) ** 2 for x in x_values)
        denominator_y = sum((y - mean_y) ** 2 for y in y_values)
        
        if denominator_x == 0 or denominator_y == 0:
            correlation = 0.0
        else:
            correlation = numerator / math.sqrt(denominator_x * denominator_y)
        
        # Determine trend direction
        if abs(slope) < 0.01:  # Very small slope
            trend_direction = 'stable'
        elif slope > 0:
            trend_direction = 'increasing'
        else:
            trend_direction = 'decreasing'
        
        # Trend strength is absolute value of slope, normalized
        trend_strength = min(abs(slope) / max(y_values) if max(y_values) > 0 else 0, 1.0)
        
        # Confidence is absolute correlation coefficient
        confidence = abs(correlation)
        
        return trend_direction, trend_strength, confidence
    
    def _predict_future_values(self, data_points: List[Tuple[datetime, float]], 
                             prediction_days: int) -> List[Dict[str, Any]]:
        """Predict future values based on trend analysis."""
        if len(data_points) < 2:
            return []
        
        # Use linear regression for simple prediction
        first_timestamp = data_points[0][0]
        x_values = [(point[0] - first_timestamp).total_seconds() / 86400 
                   for point in data_points]
        y_values = [point[1] for point in data_points]
        
        n = len(data_points)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return []
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        
        # Generate predictions
        predictions = []
        last_x = max(x_values)
        
        for i in range(1, prediction_days + 1):
            future_x = last_x + i
            predicted_y = slope * future_x + intercept
            future_date = first_timestamp + timedelta(days=future_x)
            
            predictions.append({
                'date': future_date,
                'predicted_value': max(0, predicted_y),  # Ensure non-negative
                'confidence': max(0, 1.0 - (i / prediction_days) * 0.5)  # Decreasing confidence
            })
        
        return predictions
    
    def _generate_sales_recommendations(self, sales_trends: Dict[str, TrendAnalysis]) -> List[Recommendation]:
        """Generate sales-related recommendations."""
        recommendations = []
        
        revenue_trend = sales_trends.get('revenue')
        if revenue_trend and revenue_trend.confidence > 0.6:
            if revenue_trend.trend_direction == 'decreasing':
                recommendations.append(Recommendation(
                    title="Revenue Decline Detected",
                    description="Revenue shows a declining trend. Consider implementing promotional campaigns or reviewing pricing strategy.",
                    priority="high",
                    category="sales",
                    action_items=[
                        "Review recent pricing changes",
                        "Analyze competitor pricing",
                        "Consider promotional campaigns",
                        "Review product mix performance"
                    ],
                    supporting_data={'trend_strength': revenue_trend.trend_strength}
                ))
            elif revenue_trend.trend_direction == 'increasing' and revenue_trend.trend_strength > 0.5:
                recommendations.append(Recommendation(
                    title="Strong Revenue Growth",
                    description="Revenue is growing strongly. Consider scaling operations and inventory to meet demand.",
                    priority="medium",
                    category="sales",
                    action_items=[
                        "Review inventory levels",
                        "Consider expanding product lines",
                        "Evaluate fulfillment capacity",
                        "Plan for increased customer support needs"
                    ],
                    supporting_data={'trend_strength': revenue_trend.trend_strength}
                ))
        
        orders_trend = sales_trends.get('orders_count')
        if orders_trend and orders_trend.confidence > 0.6:
            if orders_trend.trend_direction == 'decreasing':
                recommendations.append(Recommendation(
                    title="Order Volume Declining",
                    description="Order count is decreasing. Focus on customer acquisition and retention strategies.",
                    priority="high",
                    category="sales",
                    action_items=[
                        "Review marketing campaigns",
                        "Analyze customer feedback",
                        "Implement retention programs",
                        "Optimize conversion funnel"
                    ]
                ))
        
        return recommendations
    
    def _generate_user_recommendations(self, user_trends: Dict[str, TrendAnalysis]) -> List[Recommendation]:
        """Generate user-related recommendations."""
        recommendations = []
        
        active_users_trend = user_trends.get('active_users')
        if active_users_trend and active_users_trend.confidence > 0.6:
            if active_users_trend.trend_direction == 'decreasing':
                recommendations.append(Recommendation(
                    title="User Engagement Declining",
                    description="Active user count is decreasing. Implement engagement strategies to retain users.",
                    priority="high",
                    category="users",
                    action_items=[
                        "Review user experience",
                        "Implement engagement campaigns",
                        "Analyze user journey",
                        "Consider loyalty programs"
                    ]
                ))
        
        registrations_trend = user_trends.get('new_registrations')
        if registrations_trend and registrations_trend.confidence > 0.6:
            if registrations_trend.trend_direction == 'decreasing':
                recommendations.append(Recommendation(
                    title="New User Acquisition Slowing",
                    description="New user registrations are declining. Review acquisition channels and onboarding process.",
                    priority="medium",
                    category="users",
                    action_items=[
                        "Review marketing channels",
                        "Optimize onboarding flow",
                        "Analyze registration barriers",
                        "A/B test signup process"
                    ]
                ))
        
        return recommendations
    
    def _generate_system_recommendations(self) -> List[Recommendation]:
        """Generate system performance recommendations."""
        recommendations = []
        
        # Check database sizes
        total_collections = len(self.db.list_collection_names())
        if total_collections > 20:
            recommendations.append(Recommendation(
                title="Database Optimization Needed",
                description="Large number of collections detected. Consider database optimization and archiving strategies.",
                priority="medium",
                category="system",
                action_items=[
                    "Review collection usage",
                    "Implement data archiving",
                    "Optimize database indexes",
                    "Consider data partitioning"
                ]
            ))
        
        return recommendations
    
    def _forecast_storage_needs(self, days_ahead: int) -> Dict[str, Any]:
        """Forecast storage capacity needs."""
        # Simplified storage forecasting
        current_collections = self.db.list_collection_names()
        total_documents = sum(self.db[col].count_documents({}) for col in current_collections)
        
        # Assume 10% growth per month
        monthly_growth_rate = 0.10
        daily_growth_rate = monthly_growth_rate / 30
        
        projected_documents = total_documents * (1 + daily_growth_rate) ** days_ahead
        
        return {
            'current_documents': total_documents,
            'projected_documents': int(projected_documents),
            'growth_rate_daily': daily_growth_rate,
            'recommendation': 'Monitor storage usage and plan for capacity expansion' if projected_documents > total_documents * 2 else 'Current capacity sufficient'
        }
    
    def _forecast_user_capacity(self, days_ahead: int) -> Dict[str, Any]:
        """Forecast user capacity needs."""
        current_users = self.db.users.count_documents({})
        
        # Analyze recent user growth
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_users = self.db.users.count_documents({'created_at': {'$gte': week_ago}})
        
        daily_growth = recent_users / 7
        projected_users = current_users + (daily_growth * days_ahead)
        
        return {
            'current_users': current_users,
            'projected_users': int(projected_users),
            'daily_growth_rate': daily_growth,
            'recommendation': 'Plan for increased user support capacity' if projected_users > current_users * 1.5 else 'Current capacity sufficient'
        }
    
    def _forecast_order_capacity(self, days_ahead: int) -> Dict[str, Any]:
        """Forecast order processing capacity needs."""
        current_orders = self.db.orders.count_documents({})
        
        # Analyze recent order growth
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_orders = self.db.orders.count_documents({'created_at': {'$gte': week_ago}})
        
        daily_growth = recent_orders / 7
        projected_orders = current_orders + (daily_growth * days_ahead)
        
        return {
            'current_orders': current_orders,
            'projected_orders': int(projected_orders),
            'daily_growth_rate': daily_growth,
            'recommendation': 'Scale fulfillment operations' if projected_orders > current_orders * 1.5 else 'Current capacity sufficient'
        }