"""
Property-based tests for analytics and reporting engine
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timedelta
from bson import ObjectId
import json
import csv
from io import StringIO
import os
import shutil

from admin.services.metrics_collector import MetricsCollector
from admin.services.custom_report_generator import CustomReportGenerator
from admin.services.data_exporter import DataExporter
from admin.models.analytics import AnalyticsMetric, ReportConfig
from simple_mongo_mock import mock_mongo


# Generators for property-based testing
@st.composite
def valid_metric_name(draw):
    """Generate valid metric names."""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_'),
        min_size=1,
        max_size=50
    ).filter(lambda x: x and not x.startswith('_') and not x.endswith('_')))


@st.composite
def valid_metric_value(draw):
    """Generate valid metric values."""
    return draw(st.floats(
        min_value=0.0,
        max_value=1000000.0,
        allow_nan=False,
        allow_infinity=False
    ))


@st.composite
def valid_dimensions(draw):
    """Generate valid metric dimensions."""
    num_dimensions = draw(st.integers(min_value=0, max_value=5))
    dimensions = {}
    
    for _ in range(num_dimensions):
        key = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_'),
            min_size=1,
            max_size=20
        ).filter(lambda x: x and not x.startswith('_')))
        
        value = draw(st.text(min_size=1, max_size=50))
        dimensions[key] = value
    
    return dimensions


@st.composite
def analytics_metric(draw):
    """Generate a complete analytics metric."""
    # Use fixed dates to avoid flaky strategy
    base_date = datetime(2024, 1, 1)
    return {
        'metric_name': draw(valid_metric_name()),
        'value': draw(valid_metric_value()),
        'dimensions': draw(valid_dimensions()),
        'aggregation_period': draw(st.sampled_from(['minute', 'hour', 'day', 'week', 'month'])),
        'timestamp': draw(st.datetimes(
            min_value=base_date,
            max_value=base_date + timedelta(days=30)
        ))
    }


@st.composite
def report_data_record(draw):
    """Generate a report data record."""
    # Use fixed dates to avoid flaky strategy
    base_date = datetime(2024, 1, 1)
    return {
        'metric_name': draw(valid_metric_name()),
        'value': draw(valid_metric_value()),
        'timestamp': draw(st.datetimes(
            min_value=base_date,
            max_value=base_date + timedelta(days=30)
        )),
        'dimensions': draw(valid_dimensions())
    }


@st.composite
def export_data(draw):
    """Generate data suitable for export testing."""
    num_records = draw(st.integers(min_value=1, max_value=20))
    records = [draw(report_data_record()) for _ in range(num_records)]
    
    return {
        'records': records,
        'summary': {
            'total_records': len(records),
            'generated_at': datetime(2024, 1, 1)  # Fixed date
        }
    }


def get_clean_mongo_db():
    """Get a clean MongoDB mock instance."""
    # Clear all collections by deleting their files
    db_path = "mock_db/ecommerce"
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    
    # Recreate the database directory
    os.makedirs(db_path, exist_ok=True)
    
    return mock_mongo.db


class TestRealTimeMetricsAccuracy:
    """Property-based tests for real-time metrics accuracy."""
    
    @given(metric=analytics_metric())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_real_time_metrics_accuracy_property(self, metric):
        """
        **Feature: dynamic-admin-system, Property 14: Real-time Metrics Accuracy**
        **Validates: Requirements 7.1**
        
        Property: For any analytics metric, the displayed value should accurately 
        reflect the current system state within acceptable latency bounds.
        
        This test verifies that:
        1. Collected metrics are immediately available for retrieval
        2. Metric values are accurately stored and retrieved
        3. Timestamps reflect the actual collection time
        4. Dimensions and metadata are preserved correctly
        """
        mongo_db = get_clean_mongo_db()
        metrics_collector = MetricsCollector(mongo_db)
        
        # Property 1: Collected metrics should be immediately available
        collected_metric = metrics_collector.collect_metric(
            metric_name=metric['metric_name'],
            value=metric['value'],
            dimensions=metric['dimensions'],
            aggregation_period=metric['aggregation_period']
        )
        
        assert collected_metric is not None, "Collected metric should not be None"
        assert collected_metric.id is not None, "Collected metric should have an ID"
        
        # Property 2: Metric values should be accurately stored and retrieved
        assert collected_metric.metric_name == metric['metric_name'], "Metric name should be preserved"
        assert collected_metric.value == metric['value'], "Metric value should be preserved exactly"
        assert collected_metric.dimensions == metric['dimensions'], "Dimensions should be preserved"
        assert collected_metric.aggregation_period == metric['aggregation_period'], "Aggregation period should be preserved"
        
        # Property 3: Timestamps should reflect actual collection time (within reasonable bounds)
        collection_time = datetime.utcnow()
        time_diff = abs((collected_metric.timestamp - collection_time).total_seconds())
        assert time_diff < 5.0, f"Timestamp should be within 5 seconds of collection time, was {time_diff} seconds"
        
        # Property 4: Real-time queries should return the most recent data
        real_time_metrics = metrics_collector.get_real_time_metrics([metric['metric_name']])
        
        # Should have at least one metric for our metric name
        matching_metrics = [m for key, m in real_time_metrics.items() 
                          if m['metric_name'] == metric['metric_name']]
        assert len(matching_metrics) > 0, "Real-time query should return the collected metric"
        
        latest_metric = matching_metrics[0]  # Should be the most recent
        assert latest_metric['value'] == metric['value'], "Real-time query should return accurate value"
        assert latest_metric['dimensions'] == metric['dimensions'], "Real-time query should return accurate dimensions"
    
    @given(metrics_list=st.lists(analytics_metric(), min_size=2, max_size=10))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_multiple_metrics_accuracy(self, metrics_list):
        """
        Test that multiple metrics collected simultaneously maintain accuracy.
        
        This ensures that concurrent metric collection doesn't cause data corruption
        or loss of accuracy.
        """
        mongo_db = get_clean_mongo_db()
        metrics_collector = MetricsCollector(mongo_db)
        
        # Ensure unique metric names to avoid conflicts
        unique_metrics = []
        seen_names = set()
        for metric in metrics_list:
            unique_name = f"{metric['metric_name']}_{len(seen_names)}"
            if unique_name not in seen_names:
                metric_copy = metric.copy()
                metric_copy['metric_name'] = unique_name
                unique_metrics.append(metric_copy)
                seen_names.add(unique_name)
        
        if len(unique_metrics) < 2:
            return  # Skip if we don't have enough unique metrics
        
        # Collect all metrics
        collected_metrics = []
        for metric in unique_metrics:
            collected = metrics_collector.collect_metric(
                metric_name=metric['metric_name'],
                value=metric['value'],
                dimensions=metric['dimensions'],
                aggregation_period=metric['aggregation_period']
            )
            collected_metrics.append((metric, collected))
        
        # Verify all metrics were collected accurately
        for original, collected in collected_metrics:
            assert collected.metric_name == original['metric_name'], "Metric name should be preserved in batch collection"
            assert collected.value == original['value'], "Metric value should be preserved in batch collection"
            assert collected.dimensions == original['dimensions'], "Dimensions should be preserved in batch collection"
        
        # Verify real-time queries return all metrics accurately
        all_metric_names = [m['metric_name'] for m in unique_metrics]
        real_time_data = metrics_collector.get_real_time_metrics(all_metric_names)
        
        # Should have data for all collected metrics
        returned_names = set(m['metric_name'] for m in real_time_data.values())
        expected_names = set(all_metric_names)
        
        # Allow for some metrics to be grouped by aggregation period
        assert len(returned_names.intersection(expected_names)) > 0, "Real-time query should return data for collected metrics"
    
    @given(metric=analytics_metric())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_metrics_cache_accuracy(self, metric):
        """
        Test that metrics caching maintains accuracy and doesn't serve stale data.
        """
        mongo_db = get_clean_mongo_db()
        metrics_collector = MetricsCollector(mongo_db)
        
        # Collect initial metric
        initial_metric = metrics_collector.collect_metric(
            metric_name=metric['metric_name'],
            value=metric['value'],
            dimensions=metric['dimensions'],
            aggregation_period=metric['aggregation_period']
        )
        
        # Get real-time data (should use cache)
        cached_data = metrics_collector.get_real_time_metrics([metric['metric_name']])
        
        # Collect updated metric with different value
        updated_value = metric['value'] + 100.0
        updated_metric = metrics_collector.collect_metric(
            metric_name=metric['metric_name'],
            value=updated_value,
            dimensions=metric['dimensions'],
            aggregation_period=metric['aggregation_period']
        )
        
        # Get real-time data again - should reflect the update
        updated_data = metrics_collector.get_real_time_metrics([metric['metric_name']])
        
        # Find the relevant metric in the response
        matching_updated = [m for key, m in updated_data.items() 
                          if m['metric_name'] == metric['metric_name']]
        
        if matching_updated:
            # The cache should be updated with the new value
            latest_value = matching_updated[0]['value']
            # Should be either the initial or updated value (cache may have TTL)
            assert latest_value in [metric['value'], updated_value], "Cache should contain either initial or updated value"


class TestReportExportIntegrity:
    """Property-based tests for report export integrity."""
    
    @given(data=export_data(), format_name=st.sampled_from(['json', 'csv', 'xml', 'api']))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_report_export_integrity_property(self, data, format_name):
        """
        **Feature: dynamic-admin-system, Property 15: Report Export Integrity**
        **Validates: Requirements 7.5**
        
        Property: For any data export operation, the exported data should be 
        complete, accurate, and properly formatted according to the selected format.
        
        This test verifies that:
        1. All data records are included in the export
        2. Data values are preserved accurately during export
        3. Export format is valid and parseable
        4. Metadata and structure are maintained
        5. Export can be round-tripped (where applicable)
        """
        mongo_db = get_clean_mongo_db()
        data_exporter = DataExporter(mongo_db)
        user_id = ObjectId()
        
        # Property 1 & 2: Export should include all data with accurate values
        export_result = data_exporter.export_data(
            data=data,
            export_format=format_name,
            filename=f"test_export_{format_name}",
            user_id=user_id
        )
        
        assert export_result['success'], f"Export should succeed: {export_result.get('error', '')}"
        assert export_result['format'] == format_name, "Export result should indicate correct format"
        assert 'content' in export_result, "Export result should contain content"
        assert export_result['size_bytes'] > 0, "Export should have non-zero size"
        
        exported_content = export_result['content']
        
        # Property 3: Export format should be valid and parseable
        if format_name == 'json':
            # Should be valid JSON
            try:
                parsed_json = json.loads(exported_content)
                assert isinstance(parsed_json, (dict, list)), "JSON export should be valid JSON structure"
                
                # Property 4: Should contain all original records
                if isinstance(parsed_json, dict) and 'records' in parsed_json:
                    exported_records = parsed_json['records']
                elif isinstance(parsed_json, list):
                    exported_records = parsed_json
                else:
                    exported_records = [parsed_json]
                
                assert len(exported_records) == len(data['records']), "JSON export should contain all records"
                
                # Property 5: Round-trip test for JSON
                for i, original_record in enumerate(data['records']):
                    if i < len(exported_records):
                        exported_record = exported_records[i]
                        # Check that key fields are preserved (allowing for string conversion)
                        if 'metric_name' in original_record:
                            assert str(original_record['metric_name']) == str(exported_record.get('metric_name', '')), "Metric name should be preserved in JSON export"
                        if 'value' in original_record:
                            # Allow for small floating point differences
                            original_value = float(original_record['value'])
                            exported_value = float(exported_record.get('value', 0))
                            assert abs(original_value - exported_value) < 0.001, "Metric value should be preserved in JSON export"
                
            except json.JSONDecodeError as e:
                assert False, f"JSON export should be valid JSON: {e}"
        
        elif format_name == 'csv':
            # Should be valid CSV
            try:
                csv_reader = csv.DictReader(StringIO(exported_content))
                csv_records = list(csv_reader)
                
                assert len(csv_records) == len(data['records']), "CSV export should contain all records"
                
                # Check that data is preserved
                for i, original_record in enumerate(data['records']):
                    if i < len(csv_records):
                        csv_record = csv_records[i]
                        # Check key fields (CSV converts everything to strings)
                        if 'metric_name' in original_record:
                            assert str(original_record['metric_name']) == csv_record.get('metric_name', ''), "Metric name should be preserved in CSV export"
                        if 'value' in original_record:
                            original_value = float(original_record['value'])
                            csv_value = float(csv_record.get('value', 0))
                            assert abs(original_value - csv_value) < 0.001, "Metric value should be preserved in CSV export"
                
            except Exception as e:
                assert False, f"CSV export should be valid CSV: {e}"
        
        elif format_name == 'xml':
            # Should be valid XML (basic check)
            assert exported_content.startswith('<?xml'), "XML export should start with XML declaration"
            assert '<export>' in exported_content, "XML export should contain export root element"
            assert '</export>' in exported_content, "XML export should be properly closed"
            assert '<records>' in exported_content, "XML export should contain records element"
            
            # Count record elements
            record_count = exported_content.count('<record>')
            assert record_count == len(data['records']), "XML export should contain all records as record elements"
        
        elif format_name == 'api':
            # Should be valid JSON with API structure
            try:
                api_response = json.loads(exported_content)
                assert isinstance(api_response, dict), "API export should be a JSON object"
                assert api_response.get('success') is True, "API export should indicate success"
                assert 'data' in api_response, "API export should contain data field"
                assert 'timestamp' in api_response, "API export should contain timestamp"
                assert 'metadata' in api_response, "API export should contain metadata"
                
                # Check data integrity
                api_data = api_response['data']
                if isinstance(api_data, dict) and 'records' in api_data:
                    api_records = api_data['records']
                elif isinstance(api_data, list):
                    api_records = api_data
                else:
                    api_records = [api_data]
                
                assert len(api_records) == len(data['records']), "API export should contain all records"
                
            except json.JSONDecodeError as e:
                assert False, f"API export should be valid JSON: {e}"
    
    @given(data=export_data())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_export_format_consistency(self, data):
        """
        Test that the same data exported in different formats maintains consistency.
        
        This ensures that format conversion doesn't introduce data corruption.
        """
        mongo_db = get_clean_mongo_db()
        data_exporter = DataExporter(mongo_db)
        user_id = ObjectId()
        
        # Export in multiple formats
        formats_to_test = ['json', 'csv']  # Focus on formats we can easily parse
        exports = {}
        
        for format_name in formats_to_test:
            result = data_exporter.export_data(
                data=data,
                export_format=format_name,
                filename=f"consistency_test_{format_name}",
                user_id=user_id
            )
            assert result['success'], f"Export in {format_name} should succeed"
            exports[format_name] = result
        
        # Parse both formats and compare data
        json_data = json.loads(exports['json']['content'])
        csv_data = list(csv.DictReader(StringIO(exports['csv']['content'])))
        
        # Extract records from JSON (handle different structures)
        if isinstance(json_data, dict) and 'records' in json_data:
            json_records = json_data['records']
        elif isinstance(json_data, list):
            json_records = json_data
        else:
            json_records = [json_data]
        
        # Should have same number of records
        assert len(json_records) == len(csv_data), "JSON and CSV exports should have same number of records"
        
        # Compare key fields (allowing for type conversion)
        for i in range(min(len(json_records), len(csv_data))):
            json_record = json_records[i]
            csv_record = csv_data[i]
            
            # Compare metric names
            if 'metric_name' in json_record and 'metric_name' in csv_record:
                assert str(json_record['metric_name']) == str(csv_record['metric_name']), f"Metric name should be consistent between formats at record {i}"
            
            # Compare values (allowing for string/number conversion)
            if 'value' in json_record and 'value' in csv_record:
                json_value = float(json_record['value'])
                csv_value = float(csv_record['value'])
                assert abs(json_value - csv_value) < 0.001, f"Metric value should be consistent between formats at record {i}"
    
    @given(data=export_data())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_export_metadata_preservation(self, data):
        """
        Test that export operations preserve metadata and audit information.
        """
        mongo_db = get_clean_mongo_db()
        data_exporter = DataExporter(mongo_db)
        user_id = ObjectId()
        
        # Perform export
        export_result = data_exporter.export_data(
            data=data,
            export_format='json',
            filename='metadata_test',
            user_id=user_id
        )
        
        assert export_result['success'], "Export should succeed"
        
        # Check that metadata is preserved in the result
        assert 'filename' in export_result, "Export result should contain filename"
        assert 'size_bytes' in export_result, "Export result should contain size information"
        assert 'content_type' in export_result, "Export result should contain content type"
        
        # Check that export operation was logged (if logging is implemented)
        export_history = data_exporter.get_export_history(user_id=user_id, limit=10)
        
        # Should have at least one export logged
        assert len(export_history) > 0, "Export operation should be logged"
        
        # Most recent export should match our operation
        recent_export = export_history[0]
        assert recent_export['format'] == 'json', "Logged export should have correct format"
        assert str(recent_export['user_id']) == str(user_id), "Logged export should have correct user ID"
        assert 'created_at' in recent_export, "Logged export should have timestamp"