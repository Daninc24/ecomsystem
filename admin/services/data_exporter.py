"""
Data export service supporting multiple formats (CSV, PDF, API)
"""

import csv
import json
from datetime import datetime
from io import StringIO, BytesIO
from typing import Any, Dict, List, Optional, Union
from bson import ObjectId

from .base_service import BaseService


class DataExporter(BaseService):
    """Service for exporting data in multiple formats."""
    
    def __init__(self, db_client):
        super().__init__(db_client)
        self.supported_formats = ['json', 'csv', 'xml', 'api']
        # PDF support would require additional dependencies like reportlab
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'export_logs'
    
    def export_data(self, data: Union[List[Dict], Dict[str, Any]], 
                   export_format: str = 'json',
                   filename: str = None,
                   options: Dict[str, Any] = None,
                   user_id: ObjectId = None) -> Dict[str, Any]:
        """Export data in the specified format."""
        if export_format not in self.supported_formats:
            return {
                'success': False,
                'error': f'Unsupported format: {export_format}. Supported formats: {self.supported_formats}'
            }
        
        if not filename:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"export_{timestamp}"
        
        options = options or {}
        
        try:
            if export_format == 'json':
                result = self._export_to_json(data, filename, options)
            elif export_format == 'csv':
                result = self._export_to_csv(data, filename, options)
            elif export_format == 'xml':
                result = self._export_to_xml(data, filename, options)
            elif export_format == 'api':
                result = self._export_to_api(data, filename, options)
            else:
                return {'success': False, 'error': f'Format {export_format} not implemented'}
            
            # Log the export operation
            if result.get('success'):
                self._log_export_operation(export_format, filename, len(str(data)), user_id)
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def export_collection(self, collection_name: str, 
                         query: Dict[str, Any] = None,
                         export_format: str = 'json',
                         filename: str = None,
                         limit: int = None,
                         options: Dict[str, Any] = None,
                         user_id: ObjectId = None) -> Dict[str, Any]:
        """Export data from a MongoDB collection."""
        if collection_name not in self.db.list_collection_names():
            return {'success': False, 'error': f'Collection {collection_name} not found'}
        
        query = query or {}
        
        try:
            # Get data from collection
            cursor = self.db[collection_name].find(query)
            
            if limit:
                cursor = cursor.limit(limit)
            
            data = list(cursor)
            
            if not data:
                return {'success': False, 'error': 'No data found matching the query'}
            
            # Export the data
            return self.export_data(data, export_format, filename, options, user_id)
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def export_report_data(self, report_data: Dict[str, Any],
                          export_format: str = 'json',
                          filename: str = None,
                          user_id: ObjectId = None) -> Dict[str, Any]:
        """Export report data with proper formatting."""
        if not filename:
            report_name = report_data.get('config_name', 'report')
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"{report_name}_{timestamp}"
        
        # Prepare data for export
        export_data = {
            'report_metadata': {
                'name': report_data.get('config_name', 'Unknown Report'),
                'generated_at': report_data.get('generated_at', datetime.utcnow()),
                'generated_by': str(report_data.get('generated_by', '')),
                'total_records': report_data.get('metadata', {}).get('total_records', 0)
            },
            'summary': report_data.get('data', {}).get('summary', {}),
            'records': report_data.get('data', {}).get('records', [])
        }
        
        return self.export_data(export_data, export_format, filename, user_id=user_id)
    
    def get_export_history(self, user_id: ObjectId = None, 
                          limit: int = 50) -> List[Dict[str, Any]]:
        """Get export operation history."""
        query = {}
        if user_id:
            query['user_id'] = user_id
        
        exports = self.collection.find(query).sort('created_at', -1).limit(limit)
        return list(exports)
    
    def get_export_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get export statistics for the specified period."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {'$match': {'created_at': {'$gte': start_date}}},
            {'$group': {
                '_id': None,
                'total_exports': {'$sum': 1},
                'total_size_bytes': {'$sum': '$size_bytes'},
                'exports_by_format': {'$push': '$format'},
                'exports_by_user': {'$push': '$user_id'}
            }}
        ]
        
        result = list(self.collection.aggregate(pipeline))
        
        if not result:
            return {
                'total_exports': 0,
                'total_size_bytes': 0,
                'exports_by_format': {},
                'unique_users': 0
            }
        
        data = result[0]
        
        # Process format counts
        format_counts = {}
        for format_name in data.get('exports_by_format', []):
            format_counts[format_name] = format_counts.get(format_name, 0) + 1
        
        # Count unique users
        unique_users = len(set(str(uid) for uid in data.get('exports_by_user', []) if uid))
        
        return {
            'total_exports': data.get('total_exports', 0),
            'total_size_bytes': data.get('total_size_bytes', 0),
            'exports_by_format': format_counts,
            'unique_users': unique_users
        }
    
    def _export_to_json(self, data: Union[List[Dict], Dict[str, Any]], 
                       filename: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Export data to JSON format."""
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
        
        converted_data = convert_objects(data)
        
        # JSON formatting options
        indent = options.get('indent', 2)
        sort_keys = options.get('sort_keys', False)
        
        json_content = json.dumps(converted_data, indent=indent, sort_keys=sort_keys)
        
        return {
            'success': True,
            'format': 'json',
            'content': json_content,
            'filename': f"{filename}.json",
            'size_bytes': len(json_content.encode('utf-8')),
            'content_type': 'application/json'
        }
    
    def _export_to_csv(self, data: Union[List[Dict], Dict[str, Any]], 
                      filename: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Export data to CSV format."""
        output = StringIO()
        
        # Handle different data structures
        if isinstance(data, dict):
            if 'records' in data:
                records = data['records']
            else:
                # Convert dict to single record
                records = [data]
        else:
            records = data
        
        if not records:
            return {'success': False, 'error': 'No records to export'}
        
        # CSV options
        delimiter = options.get('delimiter', ',')
        include_headers = options.get('include_headers', True)
        
        # Get all unique field names
        fieldnames = set()
        for record in records:
            if isinstance(record, dict):
                fieldnames.update(record.keys())
        
        fieldnames = sorted(list(fieldnames))
        
        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter)
        
        if include_headers:
            writer.writeheader()
        
        for record in records:
            if isinstance(record, dict):
                # Convert complex objects to strings
                row = {}
                for field in fieldnames:
                    value = record.get(field, '')
                    if isinstance(value, (ObjectId, datetime)):
                        row[field] = str(value)
                    elif isinstance(value, (dict, list)):
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
            'size_bytes': len(csv_content.encode('utf-8')),
            'content_type': 'text/csv'
        }
    
    def _export_to_xml(self, data: Union[List[Dict], Dict[str, Any]], 
                      filename: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Export data to XML format."""
        def dict_to_xml(d, root_name='item'):
            xml_str = f'<{root_name}>'
            for key, value in d.items():
                if isinstance(value, dict):
                    xml_str += dict_to_xml(value, key)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            xml_str += dict_to_xml(item, key)
                        else:
                            xml_str += f'<{key}>{self._escape_xml(str(item))}</{key}>'
                else:
                    xml_str += f'<{key}>{self._escape_xml(str(value))}</{key}>'
            xml_str += f'</{root_name}>'
            return xml_str
        
        # Handle different data structures
        if isinstance(data, dict):
            if 'records' in data:
                records = data['records']
                metadata = {k: v for k, v in data.items() if k != 'records'}
            else:
                records = [data]
                metadata = {}
        else:
            records = data
            metadata = {}
        
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<export>\n'
        
        # Add metadata if present
        if metadata:
            xml_content += '<metadata>\n'
            for key, value in metadata.items():
                if isinstance(value, dict):
                    xml_content += dict_to_xml(value, key) + '\n'
                else:
                    xml_content += f'<{key}>{self._escape_xml(str(value))}</{key}>\n'
            xml_content += '</metadata>\n'
        
        # Add records
        xml_content += '<records>\n'
        for record in records:
            if isinstance(record, dict):
                xml_content += dict_to_xml(record, 'record') + '\n'
        xml_content += '</records>\n</export>'
        
        return {
            'success': True,
            'format': 'xml',
            'content': xml_content,
            'filename': f"{filename}.xml",
            'size_bytes': len(xml_content.encode('utf-8')),
            'content_type': 'application/xml'
        }
    
    def _export_to_api(self, data: Union[List[Dict], Dict[str, Any]], 
                      filename: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Export data in API-friendly format."""
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
        
        converted_data = convert_objects(data)
        
        # API response format
        api_response = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'data': converted_data,
            'metadata': {
                'export_format': 'api',
                'filename': filename,
                'record_count': len(converted_data) if isinstance(converted_data, list) else 1
            }
        }
        
        json_content = json.dumps(api_response, indent=2)
        
        return {
            'success': True,
            'format': 'api',
            'content': json_content,
            'filename': f"{filename}_api.json",
            'size_bytes': len(json_content.encode('utf-8')),
            'content_type': 'application/json',
            'api_response': api_response
        }
    
    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters."""
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')
        return text
    
    def _log_export_operation(self, format_name: str, filename: str, 
                            size_bytes: int, user_id: ObjectId = None) -> None:
        """Log export operation for auditing."""
        log_entry = {
            'format': format_name,
            'filename': filename,
            'size_bytes': size_bytes,
            'user_id': user_id,
            'created_at': datetime.utcnow()
        }
        
        try:
            self.collection.insert_one(log_entry)
        except Exception as e:
            print(f"Failed to log export operation: {e}")


# Import timedelta for statistics method
from datetime import timedelta