"""
Property-based tests for system monitoring components
**Feature: dynamic-admin-system, Property 16: Alert Generation Reliability**
**Validates: Requirements 7.3, 8.3**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timedelta
from bson import ObjectId

from admin.services.system_monitor import SystemMonitor
from admin.services.security_monitor import SecurityMonitor
from admin.models.system import (
    SystemHealthStatus, ThreatLevel, AlertSeverity,
    SystemHealth, SecurityEvent
)


class TestAlertGenerationReliability:
    """Test alert generation reliability across system monitoring components."""
    
    @given(
        cpu_usage=st.floats(min_value=0.0, max_value=100.0),
        memory_usage=st.floats(min_value=0.0, max_value=100.0),
        disk_usage=st.floats(min_value=0.0, max_value=100.0)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    def test_system_health_alerts_generated_for_threshold_violations(
        self, mongo_db, cpu_usage, memory_usage, disk_usage
    ):
        """
        **Feature: dynamic-admin-system, Property 16: Alert Generation Reliability**
        *For any* system metric that exceeds defined thresholds, 
        appropriate alerts should be generated and delivered to administrators
        **Validates: Requirements 7.3, 8.3**
        """
        monitor = SystemMonitor(mongo_db)
        
        # Clear any existing alerts to ensure clean test state
        mongo_db.system_alerts.delete_many({})
        
        # Create health status with the generated metrics
        health_status = {
            'cpu': SystemHealth(
                component='cpu',
                status=monitor._determine_health_status('cpu_usage', cpu_usage),
                message=f"CPU usage: {cpu_usage:.1f}%",
                details={'usage': cpu_usage, 'threshold': monitor.thresholds['cpu_usage']}
            ),
            'memory': SystemHealth(
                component='memory', 
                status=monitor._determine_health_status('memory_usage', memory_usage),
                message=f"Memory usage: {memory_usage:.1f}%",
                details={'usage': memory_usage, 'threshold': monitor.thresholds['memory_usage']}
            ),
            'disk': SystemHealth(
                component='disk',
                status=monitor._determine_health_status('disk_usage', disk_usage),
                message=f"Disk usage: {disk_usage:.1f}%", 
                details={'usage': disk_usage, 'threshold': monitor.thresholds['disk_usage']}
            )
        }
        
        # Generate alerts based on health status
        alert_ids = monitor.generate_alerts(health_status)
        
        # Count components that should trigger alerts
        expected_alerts = 0
        for component, health in health_status.items():
            if health.status in [SystemHealthStatus.WARNING, SystemHealthStatus.CRITICAL]:
                expected_alerts += 1
        
        # Property: Alert count should match the number of components in warning/critical state
        assert len(alert_ids) == expected_alerts
        
        # Property: Each alert should be properly stored and retrievable
        for alert_id in alert_ids:
            alert = mongo_db.system_alerts.find_one({'_id': alert_id})
            assert alert is not None
            assert alert['alert_type'] == 'system_health'
            assert alert['resolved'] is False
            assert 'source_component' in alert
            assert alert['source_component'] in ['cpu', 'memory', 'disk']
    @given(
        threat_level=st.sampled_from([ThreatLevel.HIGH, ThreatLevel.CRITICAL]),
        ip_address=st.text(min_size=7, max_size=15, alphabet='0123456789.').filter(lambda x: x.count('.') >= 1),
        event_type=st.sampled_from(['login_failure', 'suspicious_request', 'brute_force'])
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much], deadline=None)
    def test_security_alerts_generated_for_high_threats(
        self, mongo_db, threat_level, ip_address, event_type
    ):
        """
        **Feature: dynamic-admin-system, Property 16: Alert Generation Reliability**
        *For any* security event with high or critical threat level,
        appropriate security alerts should be generated immediately
        **Validates: Requirements 7.3, 8.3**
        """
        security_monitor = SecurityMonitor(mongo_db)
        
        # Clear any existing alerts to ensure clean test state
        mongo_db.system_alerts.delete_many({})
        
        # Create a high-threat security event
        security_event = SecurityEvent(
            event_type=event_type,
            threat_level=threat_level,
            source_ip=ip_address,
            user_agent="test-agent",
            description=f"Test {event_type} event"
        )
        
        # Store the event
        event_id = security_monitor.create(security_event.to_dict())
        
        # Generate alert for the event
        alert_id = security_monitor._generate_security_alert(event_id, security_event)
        
        # Property: Alert should be generated for high/critical threats
        assert alert_id is not None
        
        # Property: Alert should be properly stored with correct attributes
        alert = mongo_db.system_alerts.find_one({'_id': alert_id})
        assert alert is not None
        assert alert['alert_type'] == 'security_threat'
        assert alert['resolved'] is False
        assert alert['source_component'] == 'security_monitor'
        
        # Property: Alert severity should match threat level
        expected_severity = AlertSeverity.HIGH if threat_level == ThreatLevel.HIGH else AlertSeverity.CRITICAL
        assert alert['severity'] == expected_severity.value
        
        # Property: Alert should reference the original security event
        assert str(event_id) in alert['metadata']['security_event_id']

    @given(
        failed_attempts=st.integers(min_value=1, max_value=20),
        time_window_minutes=st.integers(min_value=1, max_value=60)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    def test_brute_force_detection_generates_alerts(
        self, mongo_db, failed_attempts, time_window_minutes
    ):
        """
        **Feature: dynamic-admin-system, Property 16: Alert Generation Reliability**
        *For any* IP address that exceeds failed login thresholds,
        brute force alerts should be generated reliably
        **Validates: Requirements 7.3, 8.3**
        """
        security_monitor = SecurityMonitor(mongo_db)
        test_ip = "192.168.1.100"
        
        # Create multiple failed login attempts
        base_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        for i in range(failed_attempts):
            event_time = base_time + timedelta(minutes=i * (time_window_minutes / failed_attempts))
            
            security_event = SecurityEvent(
                event_type="login_failure",
                threat_level=ThreatLevel.LOW,
                source_ip=test_ip,
                user_agent="test-browser",
                description="Failed login attempt",
                created_at=event_time
            )
            
            event_data = security_event.to_dict()
            event_data['created_at'] = event_time
            security_monitor.collection.insert_one(event_data)
        
        # Check if brute force detection triggers
        is_brute_force = security_monitor._is_brute_force_attempt(test_ip)
        
        # Property: Brute force should be detected when threshold is exceeded
        threshold_exceeded = failed_attempts >= security_monitor.thresholds['failed_login_attempts']
        within_time_window = time_window_minutes <= 60  # Within 1 hour window
        
        if threshold_exceeded and within_time_window:
            assert is_brute_force is True
        else:
            # May or may not be detected depending on timing
            assert isinstance(is_brute_force, bool)

    @given(
        metric_values=st.lists(
            st.floats(min_value=0.0, max_value=100.0),
            min_size=1,
            max_size=10
        ),
        metric_name=st.sampled_from(['cpu_usage', 'memory_usage', 'disk_usage'])
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    def test_alert_deduplication_prevents_spam(
        self, mongo_db, metric_values, metric_name
    ):
        """
        **Feature: dynamic-admin-system, Property 16: Alert Generation Reliability**
        *For any* repeated threshold violations on the same component,
        duplicate alerts should not be generated until the first is resolved
        **Validates: Requirements 7.3, 8.3**
        """
        monitor = SystemMonitor(mongo_db)
        
        # Clear any existing alerts to ensure clean test state
        mongo_db.system_alerts.delete_many({})
        
        alert_ids = []
        
        # Generate multiple health checks with the same problematic metric
        for value in metric_values:
            if value >= monitor.thresholds.get(metric_name, 100.0):
                health_status = {
                    metric_name.split('_')[0]: SystemHealth(
                        component=metric_name.split('_')[0],
                        status=SystemHealthStatus.CRITICAL,
                        message=f"{metric_name}: {value:.1f}%",
                        details={'usage': value, 'threshold': monitor.thresholds[metric_name]}
                    )
                }
                
                new_alert_ids = monitor.generate_alerts(health_status)
                alert_ids.extend(new_alert_ids)
        
        # Property: Only one alert should exist for the same component issue
        # (due to deduplication logic in generate_alerts)
        component_name = metric_name.split('_')[0]
        active_alerts = list(mongo_db.system_alerts.find({
            'source_component': component_name,
            'resolved': False
        }))
        
        # Should have at most 1 active alert per component
        assert len(active_alerts) <= 1
        
        # If any metric exceeded threshold, should have exactly 1 alert
        threshold_exceeded = any(v >= monitor.thresholds.get(metric_name, 100.0) for v in metric_values)
        if threshold_exceeded:
            assert len(active_alerts) == 1