"""
Analytics and reporting models
"""

from datetime import datetime
from typing import Any, Dict, Optional, List
from bson import ObjectId
from .base import BaseModel


class AnalyticsMetric(BaseModel):
    """Model for analytics metrics and data points."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.metric_name: str = kwargs.get('metric_name', '')
        self.value: float = kwargs.get('value', 0.0)
        self.dimensions: Dict[str, str] = kwargs.get('dimensions', {})
        self.timestamp: datetime = kwargs.get('timestamp', datetime.utcnow())
        self.aggregation_period: str = kwargs.get('aggregation_period', 'hour')  # minute, hour, day, week, month
        self.metadata: Dict[str, Any] = kwargs.get('metadata', {})
        self.source: str = kwargs.get('source', 'system')
        self.tags: List[str] = kwargs.get('tags', [])
    
    def add_dimension(self, key: str, value: str) -> None:
        """Add a dimension to the metric."""
        self.dimensions[key] = value
    
    def get_dimension(self, key: str, default: str = '') -> str:
        """Get a dimension value."""
        return self.dimensions.get(key, default)


class ReportConfig(BaseModel):
    """Model for custom report configurations."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name: str = kwargs.get('name', '')
        self.description: str = kwargs.get('description', '')
        self.report_type: str = kwargs.get('report_type', 'custom')  # custom, scheduled, template
        self.metrics: List[str] = kwargs.get('metrics', [])
        self.filters: Dict[str, Any] = kwargs.get('filters', {})
        self.date_range: Dict[str, Any] = kwargs.get('date_range', {})
        self.grouping: List[str] = kwargs.get('grouping', [])
        self.sorting: Dict[str, Any] = kwargs.get('sorting', {})
        self.format: str = kwargs.get('format', 'json')  # json, csv, pdf, excel
        self.schedule: Optional[Dict[str, Any]] = kwargs.get('schedule')  # for scheduled reports
        self.recipients: List[str] = kwargs.get('recipients', [])  # email addresses
        self.is_active: bool = kwargs.get('is_active', True)
        self.last_generated: Optional[datetime] = kwargs.get('last_generated')
        self.generation_count: int = kwargs.get('generation_count', 0)
    
    def add_metric(self, metric_name: str) -> None:
        """Add a metric to the report."""
        if metric_name not in self.metrics:
            self.metrics.append(metric_name)
    
    def remove_metric(self, metric_name: str) -> None:
        """Remove a metric from the report."""
        if metric_name in self.metrics:
            self.metrics.remove(metric_name)
    
    def set_filter(self, key: str, value: Any) -> None:
        """Set a filter for the report."""
        self.filters[key] = value
    
    def increment_generation_count(self) -> None:
        """Increment the generation count and update last generated time."""
        self.generation_count += 1
        self.last_generated = datetime.utcnow()
        self.updated_at = datetime.utcnow()