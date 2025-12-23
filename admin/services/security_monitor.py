"""
Security monitoring service for login tracking and threat detection
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from bson import ObjectId
from collections import defaultdict, Counter

from .base_service import BaseService
from ..models.system import SecurityEvent, ThreatLevel, SystemAlert, AlertSeverity


class SecurityMonitor(BaseService):
    """Service for monitoring security events and detecting threats."""
    
    def _get_collection_name(self) -> str:
        return "security_events"
    
    def __init__(self, mongo_db):
        super().__init__(mongo_db)
        self.alert_collection = self.db.system_alerts
        
        # Security thresholds
        self.thresholds = {
            'failed_login_attempts': 5,  # per IP per hour
            'rapid_requests': 100,  # requests per minute
            'suspicious_user_agents': 10,  # different UAs per IP per hour
            'geographic_anomaly_distance': 1000,  # km
            'session_duration_hours': 24
        }
        
        # Known malicious patterns
        self.malicious_patterns = [
            r'(?i)(union|select|insert|delete|drop|create|alter)\s+',  # SQL injection
            r'(?i)<script[^>]*>.*?</script>',  # XSS
            r'(?i)javascript:',  # JavaScript injection
            r'(?i)\.\./.*\.\.',  # Path traversal
            r'(?i)(cmd|exec|system|eval)\s*\(',  # Command injection
        ]
        
        # Suspicious user agents
        self.suspicious_user_agents = [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'zap', 'burp',
            'wget', 'curl', 'python-requests', 'bot', 'crawler'
        ]
    
    def log_login_attempt(self, user_id: Optional[ObjectId], ip_address: str, 
                         user_agent: str, success: bool, details: Dict[str, Any] = None) -> ObjectId:
        """Log a login attempt and analyze for threats."""
        event_type = "login_success" if success else "login_failure"
        threat_level = ThreatLevel.NONE if success else ThreatLevel.LOW
        
        # Analyze threat level for failed attempts
        if not success:
            threat_level = self._analyze_login_threat(ip_address, user_agent)
        
        security_event = SecurityEvent(
            event_type=event_type,
            threat_level=threat_level,
            source_ip=ip_address,
            user_agent=user_agent,
            user_id=user_id,
            description=f"{'Successful' if success else 'Failed'} login attempt",
            details=details or {}
        )
        
        event_id = self.create(security_event.to_dict())
        
        # Generate alerts if necessary
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            self._generate_security_alert(event_id, security_event)
        
        return event_id
    
    def _analyze_login_threat(self, ip_address: str, user_agent: str) -> ThreatLevel:
        """Analyze login attempt for threat indicators."""
        threat_level = ThreatLevel.LOW
        
        # Check for brute force attempts
        if self._is_brute_force_attempt(ip_address):
            threat_level = ThreatLevel.HIGH
        
        # Check for suspicious user agent
        if self._is_suspicious_user_agent(user_agent):
            threat_level = max(threat_level, ThreatLevel.MEDIUM)
        
        # Check for rapid failed attempts
        if self._has_rapid_failed_attempts(ip_address):
            threat_level = max(threat_level, ThreatLevel.HIGH)
        
        return threat_level
    
    def _is_brute_force_attempt(self, ip_address: str) -> bool:
        """Check if IP has exceeded failed login threshold."""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        failed_attempts = self.count({
            'source_ip': ip_address,
            'event_type': 'login_failure',
            'created_at': {'$gte': one_hour_ago}
        })
        
        return failed_attempts >= self.thresholds['failed_login_attempts']
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious."""
        user_agent_lower = user_agent.lower()
        return any(suspicious in user_agent_lower for suspicious in self.suspicious_user_agents)
    
    def _has_rapid_failed_attempts(self, ip_address: str) -> bool:
        """Check for rapid succession of failed attempts."""
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        
        recent_failures = self.count({
            'source_ip': ip_address,
            'event_type': 'login_failure',
            'created_at': {'$gte': five_minutes_ago}
        })
        
        return recent_failures >= 10  # 10 failures in 5 minutes
    
    def log_request(self, ip_address: str, user_agent: str, request_path: str, 
                   request_method: str, user_id: Optional[ObjectId] = None,
                   request_data: str = "") -> Optional[ObjectId]:
        """Log and analyze a web request for security threats."""
        threat_level = self._analyze_request_threat(request_path, request_data, user_agent)
        
        if threat_level != ThreatLevel.NONE:
            security_event = SecurityEvent(
                event_type="suspicious_request",
                threat_level=threat_level,
                source_ip=ip_address,
                user_agent=user_agent,
                user_id=user_id,
                description=f"Suspicious {request_method} request to {request_path}",
                details={
                    'request_path': request_path,
                    'request_method': request_method,
                    'request_data': request_data[:1000]  # Limit data size
                }
            )
            
            event_id = self.create(security_event.to_dict())
            
            # Generate alert for high/critical threats
            if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                self._generate_security_alert(event_id, security_event)
            
            return event_id
        
        return None
    
    def _analyze_request_threat(self, request_path: str, request_data: str, user_agent: str) -> ThreatLevel:
        """Analyze request for threat indicators."""
        threat_level = ThreatLevel.NONE
        
        # Check for malicious patterns in path and data
        combined_data = f"{request_path} {request_data}"
        
        for pattern in self.malicious_patterns:
            if re.search(pattern, combined_data):
                threat_level = ThreatLevel.HIGH
                break
        
        # Check for suspicious user agent
        if self._is_suspicious_user_agent(user_agent):
            threat_level = max(threat_level, ThreatLevel.MEDIUM)
        
        # Check for common attack paths
        suspicious_paths = [
            '/admin', '/wp-admin', '/phpmyadmin', '/config',
            '/.env', '/backup', '/test', '/debug'
        ]
        
        if any(path in request_path.lower() for path in suspicious_paths):
            threat_level = max(threat_level, ThreatLevel.MEDIUM)
        
        return threat_level
    
    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect security anomalies in recent activity."""
        anomalies = []
        
        # Check for IP address anomalies
        ip_anomalies = self._detect_ip_anomalies()
        anomalies.extend(ip_anomalies)
        
        # Check for user behavior anomalies
        user_anomalies = self._detect_user_anomalies()
        anomalies.extend(user_anomalies)
        
        # Check for time-based anomalies
        time_anomalies = self._detect_time_anomalies()
        anomalies.extend(time_anomalies)
        
        return anomalies
    
    def _detect_ip_anomalies(self) -> List[Dict[str, Any]]:
        """Detect IP-based anomalies."""
        anomalies = []
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        # Find IPs with high activity
        pipeline = [
            {'$match': {'created_at': {'$gte': one_hour_ago}}},
            {'$group': {
                '_id': '$source_ip',
                'event_count': {'$sum': 1},
                'unique_user_agents': {'$addToSet': '$user_agent'},
                'threat_levels': {'$push': '$threat_level'}
            }},
            {'$match': {'event_count': {'$gte': 50}}}  # High activity threshold
        ]
        
        high_activity_ips = list(self.collection.aggregate(pipeline))
        
        for ip_data in high_activity_ips:
            ip_address = ip_data['_id']
            event_count = ip_data['event_count']
            unique_uas = len(ip_data['unique_user_agents'])
            
            anomaly = {
                'type': 'high_activity_ip',
                'ip_address': ip_address,
                'event_count': event_count,
                'unique_user_agents': unique_uas,
                'severity': 'high' if event_count > 100 else 'medium'
            }
            anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_user_anomalies(self) -> List[Dict[str, Any]]:
        """Detect user behavior anomalies."""
        anomalies = []
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        
        # Find users with unusual activity patterns
        pipeline = [
            {'$match': {
                'user_id': {'$ne': None},
                'created_at': {'$gte': one_day_ago}
            }},
            {'$group': {
                '_id': '$user_id',
                'event_count': {'$sum': 1},
                'unique_ips': {'$addToSet': '$source_ip'},
                'failed_logins': {
                    '$sum': {'$cond': [{'$eq': ['$event_type', 'login_failure']}, 1, 0]}
                }
            }}
        ]
        
        user_activity = list(self.collection.aggregate(pipeline))
        
        for user_data in user_activity:
            user_id = user_data['_id']
            unique_ips = len(user_data['unique_ips'])
            failed_logins = user_data['failed_logins']
            
            # Check for multiple IP addresses (possible account sharing/compromise)
            if unique_ips > 5:
                anomaly = {
                    'type': 'multiple_ip_user',
                    'user_id': str(user_id),
                    'unique_ips': unique_ips,
                    'severity': 'high' if unique_ips > 10 else 'medium'
                }
                anomalies.append(anomaly)
            
            # Check for high failed login rate
            if failed_logins > 10:
                anomaly = {
                    'type': 'high_failed_logins',
                    'user_id': str(user_id),
                    'failed_logins': failed_logins,
                    'severity': 'high'
                }
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_time_anomalies(self) -> List[Dict[str, Any]]:
        """Detect time-based anomalies."""
        anomalies = []
        
        # Check for unusual activity during off-hours (assuming business hours 9-17 UTC)
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        
        off_hours_events = self.count({
            'created_at': {'$gte': one_day_ago},
            '$expr': {
                '$or': [
                    {'$lt': [{'$hour': '$created_at'}, 9]},
                    {'$gt': [{'$hour': '$created_at'}, 17]}
                ]
            }
        })
        
        total_events = self.count({'created_at': {'$gte': one_day_ago}})
        
        if total_events > 0:
            off_hours_percentage = (off_hours_events / total_events) * 100
            
            if off_hours_percentage > 70:  # More than 70% activity off-hours
                anomaly = {
                    'type': 'off_hours_activity',
                    'off_hours_percentage': off_hours_percentage,
                    'total_events': total_events,
                    'severity': 'medium'
                }
                anomalies.append(anomaly)
        
        return anomalies
    
    def _generate_security_alert(self, event_id: ObjectId, security_event: SecurityEvent) -> ObjectId:
        """Generate a security alert for a high-threat event."""
        severity_map = {
            ThreatLevel.HIGH: AlertSeverity.HIGH,
            ThreatLevel.CRITICAL: AlertSeverity.CRITICAL
        }
        
        alert = SystemAlert(
            alert_type='security_threat',
            severity=severity_map.get(security_event.threat_level, AlertSeverity.MEDIUM),
            title=f"Security Threat Detected: {security_event.event_type}",
            message=f"{security_event.description} from IP {security_event.source_ip}",
            source_component='security_monitor',
            metadata={
                'security_event_id': str(event_id),
                'threat_level': security_event.threat_level.value,
                'source_ip': security_event.source_ip
            }
        )
        
        alert_id = ObjectId()
        alert_data = alert.to_dict()
        alert_data['_id'] = alert_id
        
        self.alert_collection.insert_one(alert_data)
        return alert_id
    
    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security summary for the specified time period."""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Count events by type
        event_counts = {}
        pipeline = [
            {'$match': {'created_at': {'$gte': start_time}}},
            {'$group': {'_id': '$event_type', 'count': {'$sum': 1}}}
        ]
        
        for result in self.collection.aggregate(pipeline):
            event_counts[result['_id']] = result['count']
        
        # Count by threat level
        threat_counts = {}
        pipeline = [
            {'$match': {'created_at': {'$gte': start_time}}},
            {'$group': {'_id': '$threat_level', 'count': {'$sum': 1}}}
        ]
        
        for result in self.collection.aggregate(pipeline):
            threat_counts[result['_id']] = result['count']
        
        # Get top source IPs
        top_ips = []
        pipeline = [
            {'$match': {'created_at': {'$gte': start_time}}},
            {'$group': {'_id': '$source_ip', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]
        
        for result in self.collection.aggregate(pipeline):
            top_ips.append({'ip': result['_id'], 'events': result['count']})
        
        # Get active alerts
        active_alerts = list(self.alert_collection.find({
            'alert_type': 'security_threat',
            'resolved': False
        }).sort('created_at', -1))
        
        return {
            'time_period_hours': hours,
            'total_events': sum(event_counts.values()),
            'event_counts': event_counts,
            'threat_counts': threat_counts,
            'top_source_ips': top_ips,
            'active_security_alerts': len(active_alerts),
            'recent_anomalies': self.detect_anomalies()
        }
    
    def block_ip(self, ip_address: str, reason: str, user_id: ObjectId, duration_hours: int = 24) -> bool:
        """Block an IP address (this would integrate with firewall/proxy)."""
        # This is a placeholder for IP blocking logic
        # In a real implementation, this would integrate with iptables, nginx, cloudflare, etc.
        
        # Log the blocking action
        security_event = SecurityEvent(
            event_type="ip_blocked",
            threat_level=ThreatLevel.HIGH,
            source_ip=ip_address,
            user_agent="system",
            description=f"IP blocked: {reason}",
            details={
                'reason': reason,
                'duration_hours': duration_hours,
                'blocked_by': str(user_id)
            }
        )
        
        self.create(security_event.to_dict(), user_id)
        print(f"IP {ip_address} blocked for {duration_hours} hours: {reason}")
        return True