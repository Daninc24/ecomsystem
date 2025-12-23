"""
Custom report generation service with filtering and export capabilities
"""

import csv
import json
from datetime import datetime, timedelta
from io import StringIO
from typing import Any, Dict, List, Optional, Union
from bson import ObjectId

from ..models.analytics import ReportConfig, AnalyticsMetric
from .base_service import BaseService


class CustomReportGenerator(BaseService):
    """Service for generating custom reports with filtering and export capabilities."""
    
    def __init__(self, db_client):
        super().__init__(db_client)
        self.supported_formats = ['json', 'csv', 'pdf']
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'report_configs'
    
    def create_report_config(self, name: str, description: str,
                           metrics: List[str], filters: Dict[str, Any] = None,
                           date_range: Dict[str, Any] = None,
                           grouping: List[str] = None,
                           sorting: Dict[str, Any] = None,
                           format: str = 'json',
                           user_id: ObjectId = None) -> ReportConfig:
        """Create a new report configuration."""
        config = ReportConfig(
            name=name,
            description=description,
            metrics=metrics,
            filters=filters or {},
            date_range=date_range or {},
            grouping=grouping or [],
            sorting=sorting or {'field': 'timestamp', 'order': 'desc'},
            format=format,
            created_by=user_id
        )
        
        result = self.collection.insert_one(config.to_dict())
        config.id = result.inserted_id
        
        return config
    
    def generate_report(self, config_id: ObjectId = None,
                       config: ReportConfig = None,
                       user_id: ObjectId = None) -> Dict[str, Any]:
        """Generate a report based on configuration."""
        if config_id and not config:
            config_data = self.collection.find_one({'_id': config_id})
            if not config_data:
                return {'success': False, 'error': 'Report configuration not found'}
            config = ReportConfig.from_dict(config_data)
        
        if not config:
            return {'success': False, 'error': 'No report configuration provided'}
        
        try:
            # Build query based on filters and date range
            query = self._build_query(config.filters, config.date_range)
            
            # Get data from appropriate collections
            report_data = self._collect_report_data(config.metrics, query, config.grouping, config.sorting)
            
            # Apply additional processing
            processed_data = self._process_report_data(report_data, config)
            
            # Update config generation count
            config.increment_generation_count()
            if config.id:
                self.collection.update_one(
                    {'_id': config.id},
                    {'$set': {
                        'generation_count': config.generation_count,
                        'last_generated': config.last_generated,
                        'updated_at': config.updated_at
                    }}
                )
            
            return {
                'success': True,
                'report_id': str(config.id) if config.id else None,
                'config_name': config.name,
                'generated_at': datetime.utcnow(),
                'generated_by': user_id,
                'data': processed_data,
                'metadata': {
                    'total_records': len(processed_data.get('records', [])),
                    'filters_applied': config.filters,
                    'date_range': config.date_range,
                    'metrics': config.metrics
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def generate_sales_report(self, start_date: datetime, end_date: datetime,
                            filters: Dict[str, Any] = None,
                            grouping: List[str] = None,
                            user_id: ObjectId = None) -> Dict[str, Any]:
        """Generate a sales report with specified parameters."""
        config = ReportConfig(
            name=f"Sales Report {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            description="Custom sales report",
            metrics=['orders_count', 'revenue', 'avg_order_value'],
            filters=filters or {},
            date_range={'start': start_date, 'end': end_date},
            grouping=grouping or ['date'],
            sorting={'field': 'date', 'order': 'asc'}
        )
        
        return self.generate_report(config=config, user_id=user_id)
    
    def generate_user_analytics_report(self, start_date: datetime, end_date: datetime,
                                     filters: Dict[str, Any] = None,
                                     user_id: ObjectId = None) -> Dict[str, Any]:
        """Generate a user analytics report."""
        config = ReportConfig(
            name=f"User Analytics {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            description="User behavior and engagement analytics",
            metrics=['active_users', 'new_registrations', 'user_retention'],
            filters=filters or {},
            date_range={'start': start_date, 'end': end_date},
            grouping=['date', 'user_type'],
            sorting={'field': 'date', 'order': 'asc'}
        )
        
        return self.generate_report(config=config, user_id=user_id)
    
    def export_report(self, report_data: Dict[str, Any], 
                     export_format: str = 'json',
                     filename: str = None) -> Dict[str, Any]:
        """Export report data in specified format."""
        if export_format not in self.supported_formats:
            return {'success': False, 'error': f'Unsupported format: {export_format}'}
        
        if not filename:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"report_{timestamp}"
        
        try:
            if export_format == 'json':
                return self._export_to_json(report_data, filename)
            elif export_format == 'csv':
                return self._export_to_csv(report_data, filename)
            elif export_format == 'pdf':
                return self._export_to_pdf(report_data, filename)
            else:
                return {'success': False, 'error': f'Format {export_format} not implemented'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_report_config(self, config_id: ObjectId) -> Optional[ReportConfig]:
        """Get report configuration by ID."""
        config_data = self.collection.find_one({'_id': config_id})
        if config_data:
            return ReportConfig.from_dict(config_data)
        return None
    
    def list_report_configs(self, user_id: ObjectId = None, 
                           limit: int = 50) -> List[ReportConfig]:
        """List report configurations."""
        query = {}
        if user_id:
            query['created_by'] = user_id
        
        configs_data = self.collection.find(query).sort('created_at', -1).limit(limit)
        return [ReportConfig.from_dict(config_data) for config_data in configs_data]
    
    def update_report_config(self, config_id: ObjectId, 
                           updates: Dict[str, Any],
                           user_id: ObjectId = None) -> bool:
        """Update report configuration."""
        updates['updated_at'] = datetime.utcnow()
        if user_id:
            updates['updated_by'] = user_id
        
        result = self.collection.update_one(
            {'_id': config_id},
            {'$set': updates}
        )
        
        return result.modified_count > 0
    
    def delete_report_config(self, config_id: ObjectId) -> bool:
        """Delete report configuration."""
        result = self.collection.delete_one({'_id': config_id})
        return result.deleted_count > 0
    
    def _build_query(self, filters: Dict[str, Any], 
                    date_range: Dict[str, Any]) -> Dict[str, Any]:
        """Build MongoDB query from filters and date range."""
        query = {}
        
        # Apply date range
        if date_range:
            date_filter = {}
            if 'start' in date_range:
                date_filter['$gte'] = date_range['start']
            if 'end' in date_range:
                date_filter['$lte'] = date_range['end']
            if date_filter:
                query['timestamp'] = date_filter
        
        # Apply other filters
        for key, value in filters.items():
            if key == 'status':
                query['status'] = value
            elif key == 'user_type':
                query['user_type'] = value
            elif key == 'vendor_id':
                query['vendor_id'] = ObjectId(value) if isinstance(value, str) else value
            elif key == 'category':
                query['category'] = value
            elif key.startswith('dimensions.'):
                query[key] = value
        
        return query
    
    def _collect_report_data(self, metrics: List[str], query: Dict[str, Any],
                           grouping: List[str], sorting: Dict[str, Any]) -> Dict[str, Any]:
        """Collect data for report based on metrics and query."""
        data = {'records': [], 'summary': {}}
        
        # Collect metrics data
        for metric_name in metrics:
            if metric_name in ['orders_count', 'revenue', 'avg_order_value']:
                metric_data = self._collect_sales_metrics_data(query, grouping, sorting)
                data['records'].extend(metric_data)
            elif metric_name in ['active_users', 'new_registrations', 'user_retention']:
                metric_data = self._collect_user_metrics_data(query, grouping, sorting)
                data['records'].extend(metric_data)
            else:
                # Generic metrics from analytics collection
                metric_query = dict(query)
                metric_query['metric_name'] = metric_name
                
                metrics_cursor = self.db.analytics_metrics.find(metric_query)
                if sorting:
                    sort_order = 1 if sorting.get('order', 'asc') == 'asc' else -1
                    metrics_cursor = metrics_cursor.sort(sorting.get('field', 'timestamp'), sort_order)
                
                for metric_doc in metrics_cursor:
                    metric = AnalyticsMetric.from_dict(metric_doc)
                    data['records'].append({
                        'metric_name': metric.metric_name,
                        'value': metric.value,
                        'timestamp': metric.timestamp,
                        'dimensions': metric.dimensions,
                        'aggregation_period': metric.aggregation_period
                    })
        
        return data
    
    def _collect_sales_metrics_data(self, query: Dict[str, Any],
                                  grouping: List[str], 
                                  sorting: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect sales-specific metrics data."""
        # Build aggregation pipeline for sales data
        pipeline = []
        
        # Match stage
        match_stage = {}
        if 'timestamp' in query:
            match_stage['created_at'] = query['timestamp']
        if 'status' in query:
            match_stage['status'] = query['status']
        if 'vendor_id' in query:
            match_stage['vendor_id'] = query['vendor_id']
        
        if match_stage:
            pipeline.append({'$match': match_stage})
        
        # Group stage
        group_id = {}
        if 'date' in grouping:
            group_id['date'] = {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}}
        if 'vendor_id' in grouping:
            group_id['vendor_id'] = '$vendor_id'
        if 'status' in grouping:
            group_id['status'] = '$status'
        
        if not group_id:
            group_id = None
        
        group_stage = {
            '_id': group_id,
            'orders_count': {'$sum': 1},
            'revenue': {'$sum': '$total_amount'},
            'avg_order_value': {'$avg': '$total_amount'}
        }
        
        pipeline.append({'$group': group_stage})
        
        # Sort stage
        if sorting:
            sort_field = sorting.get('field', 'date')
            sort_order = 1 if sorting.get('order', 'asc') == 'asc' else -1
            if sort_field == 'date' and group_id and 'date' in group_id:
                pipeline.append({'$sort': {'_id.date': sort_order}})
            else:
                pipeline.append({'$sort': {sort_field: sort_order}})
        
        # Execute aggregation
        results = list(self.db.orders.aggregate(pipeline))
        
        # Format results
        formatted_results = []
        for result in results:
            record = {
                'orders_count': result.get('orders_count', 0),
                'revenue': result.get('revenue', 0.0),
                'avg_order_value': result.get('avg_order_value', 0.0),
                'timestamp': datetime.utcnow()
            }
            
            # Add grouping dimensions
            if result['_id']:
                if isinstance(result['_id'], dict):
                    record.update(result['_id'])
                else:
                    record['group'] = result['_id']
            
            formatted_results.append(record)
        
        return formatted_results
    
    def _collect_user_metrics_data(self, query: Dict[str, Any],
                                 grouping: List[str],
                                 sorting: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect user-specific metrics data."""
        # Simplified user metrics collection
        # In a real implementation, this would aggregate user session and registration data
        
        results = []
        
        # Active users metric
        active_users_count = self.db.user_sessions.count_documents({
            'last_activity': {'$gte': datetime.utcnow() - timedelta(hours=24)}
        })
        
        results.append({
            'metric_name': 'active_users',
            'value': active_users_count,
            'timestamp': datetime.utcnow(),
            'dimensions': {'period': 'daily'}
        })
        
        # New registrations metric
        date_filter = query.get('timestamp', {})
        registration_query = {}
        if date_filter:
            registration_query['created_at'] = date_filter
        
        new_registrations = self.db.users.count_documents(registration_query)
        
        results.append({
            'metric_name': 'new_registrations',
            'value': new_registrations,
            'timestamp': datetime.utcnow(),
            'dimensions': {'period': 'custom'}
        })
        
        return results
    
    def _process_report_data(self, data: Dict[str, Any], 
                           config: ReportConfig) -> Dict[str, Any]:
        """Process and format report data."""
        processed = {
            'records': data['records'],
            'summary': {},
            'config': {
                'name': config.name,
                'description': config.description,
                'metrics': config.metrics,
                'filters': config.filters,
                'grouping': config.grouping
            }
        }
        
        # Calculate summary statistics
        if data['records']:
            numeric_fields = ['value', 'orders_count', 'revenue', 'avg_order_value']
            
            for field in numeric_fields:
                values = [record.get(field, 0) for record in data['records'] 
                         if isinstance(record.get(field), (int, float))]
                
                if values:
                    processed['summary'][field] = {
                        'total': sum(values),
                        'average': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'count': len(values)
                    }
        
        return processed
    
    def _export_to_json(self, report_data: Dict[str, Any], 
                       filename: str) -> Dict[str, Any]:
        """Export report to JSON format."""
        def convert_objects(obj):
            if isinstance(obj, ObjectId):
                return str(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_objects(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_objects(item) for item in obj]
            return obj
        
        converted_data = convert_objects(report_data)
        json_content = json.dumps(converted_data, indent=2)
        
        return {
            'success': True,
            'format': 'json',
            'content': json_content,
            'filename': f"{filename}.json",
            'size': len(json_content)
        }
    
    def _export_to_csv(self, report_data: Dict[str, Any], 
                      filename: str) -> Dict[str, Any]:
        """Export report to CSV format."""
        output = StringIO()
        
        records = report_data.get('data', {}).get('records', [])
        if not records:
            return {'success': False, 'error': 'No data to export'}
        
        # Get all unique field names
        fieldnames = set()
        for record in records:
            fieldnames.update(record.keys())
        
        fieldnames = sorted(list(fieldnames))
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for record in records:
            # Convert complex objects to strings
            row = {}
            for field in fieldnames:
                value = record.get(field, '')
                if isinstance(value, (ObjectId, datetime)):
                    row[field] = str(value)
                elif isinstance(value, dict):
                    row[field] = json.dumps(value)
                else:
                    row[field] = value
            writer.writerow(row)
        
        csv_content = output.getvalue()
        
        return {
            'success': True,
            'format': 'csv',
            'content': csv_content,
            'filename': f"{filename}.csv",
            'size': len(csv_content)
        }
    
    def _export_to_pdf(self, report_data: Dict[str, Any], 
                      filename: str) -> Dict[str, Any]:
        """Export report to PDF format (placeholder implementation)."""
        # This would require a PDF library like reportlab
        # For now, return a placeholder
        return {
            'success': False,
            'error': 'PDF export not implemented - requires additional dependencies'
        }