"""
Session Security Manager
Enhanced session management with security measures and timeout handling
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from bson import ObjectId

from .base_service import BaseService
from ..models.user import UserSession


class SessionSecurityManager(BaseService):
    """Enhanced session security manager with comprehensive security measures."""
    
    def _get_collection_name(self) -> str:
        return "user_sessions"
    
    def __init__(self, db, audit_logger=None):
        super().__init__(db)
        self.audit_logger = audit_logger
        
        # Security configuration
        self.config = {
            'session_timeout_hours': 24,
            'idle_timeout_minutes': 30,
            'max_sessions_per_user': 5,
            'session_token_length': 32,
            'require_ip_consistency': True,
            'require_user_agent_consistency': True,
            'enable_session_rotation': True,
            'rotation_interval_hours': 4,
            'suspicious_activity_threshold': 10,
            'max_concurrent_logins': 3,
            'session_cleanup_interval_hours': 1
        }
        
        # Track suspicious activities
        self.suspicious_activities = {}
    
    def create_secure_session(self, 
                            user_id: ObjectId, 
                            ip_address: str, 
                            user_agent: str,
                            device_fingerprint: Optional[str] = None,
                            login_method: str = 'password') -> UserSession:
        """Create a new secure session with enhanced security measures."""
        
        # Check for too many concurrent sessions
        self._enforce_session_limits(user_id)
        
        # Generate secure session token
        session_token = self._generate_secure_token()
        
        # Calculate expiration times
        expires_at = datetime.utcnow() + timedelta(hours=self.config['session_timeout_hours'])
        idle_expires_at = datetime.utcnow() + timedelta(minutes=self.config['idle_timeout_minutes'])
        
        # Create session with security metadata
        session = UserSession(
            user_id=user_id,
            session_token=session_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
            is_active=True,
            last_activity=datetime.utcnow(),
            login_method=login_method,
            device_info={
                'fingerprint': device_fingerprint,
                'ip_hash': self._hash_ip(ip_address),
                'user_agent_hash': self._hash_user_agent(user_agent),
                'created_at': datetime.utcnow(),
                'idle_expires_at': idle_expires_at,
                'rotation_due_at': datetime.utcnow() + timedelta(hours=self.config['rotation_interval_hours']),
                'security_flags': {
                    'ip_locked': self.config['require_ip_consistency'],
                    'user_agent_locked': self.config['require_user_agent_consistency'],
                    'requires_rotation': self.config['enable_session_rotation']
                }
            }
        )
        
        # Store session
        session_id = self.create(session.to_dict())
        session.id = session_id
        
        # Log session creation
        if self.audit_logger:
            self.audit_logger.log_activity(
                user_id=user_id,
                action='secure_session_created',
                resource_type='session',
                resource_id=str(session_id),
                details={
                    'ip_address': ip_address,
                    'user_agent': user_agent[:100],  # Truncate for logging
                    'login_method': login_method,
                    'expires_at': expires_at.isoformat(),
                    'security_features': list(session.device_info['security_flags'].keys())
                }
            )
        
        return session
    
    def validate_session_security(self, 
                                session_token: str, 
                                current_ip: str, 
                                current_user_agent: str) -> Tuple[Optional[UserSession], List[str]]:
        """
        Validate session with comprehensive security checks.
        
        Returns:
            Tuple of (session, security_warnings)
        """
        security_warnings = []
        
        # Find session
        session_data = self.collection.find_one({'session_token': session_token})
        if not session_data:
            return None, ['Session not found']
        
        session_data['id'] = session_data.pop('_id')
        session = UserSession(**session_data)
        
        # Basic validity checks
        if not session.is_active:
            return None, ['Session is inactive']
        
        if session.is_expired():
            self._deactivate_session(session.id, 'expired')
            return None, ['Session expired']
        
        # Check idle timeout
        idle_expires_at = session.device_info.get('idle_expires_at')
        if idle_expires_at and datetime.utcnow() > idle_expires_at:
            self._deactivate_session(session.id, 'idle_timeout')
            return None, ['Session idle timeout']
        
        # Security validations
        if self.config['require_ip_consistency']:
            if self._hash_ip(current_ip) != session.device_info.get('ip_hash'):
                security_warnings.append('IP address changed')
                self._log_suspicious_activity(session.user_id, 'ip_change', {
                    'original_ip_hash': session.device_info.get('ip_hash'),
                    'current_ip_hash': self._hash_ip(current_ip)
                })
        
        if self.config['require_user_agent_consistency']:
            if self._hash_user_agent(current_user_agent) != session.device_info.get('user_agent_hash'):
                security_warnings.append('User agent changed')
                self._log_suspicious_activity(session.user_id, 'user_agent_change', {
                    'original_ua_hash': session.device_info.get('user_agent_hash'),
                    'current_ua_hash': self._hash_user_agent(current_user_agent)
                })
        
        # Check if session rotation is due
        rotation_due_at = session.device_info.get('rotation_due_at')
        if rotation_due_at and datetime.utcnow() > rotation_due_at:
            security_warnings.append('Session rotation required')
        
        # Update last activity and idle timeout
        self._update_session_activity(session.id)
        
        return session, security_warnings
    
    def rotate_session_token(self, session_id: ObjectId) -> Optional[str]:
        """Rotate session token for enhanced security."""
        try:
            # Generate new token
            new_token = self._generate_secure_token()
            
            # Update session
            update_result = self.collection.update_one(
                {'_id': session_id},
                {
                    '$set': {
                        'session_token': new_token,
                        'device_info.rotation_due_at': datetime.utcnow() + timedelta(hours=self.config['rotation_interval_hours']),
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if update_result.modified_count > 0:
                # Log rotation
                if self.audit_logger:
                    self.audit_logger.log_activity(
                        user_id=None,  # Will be filled by caller
                        action='session_token_rotated',
                        resource_type='session',
                        resource_id=str(session_id),
                        details={'new_token_prefix': new_token[:8]}
                    )
                
                return new_token
            
            return None
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=None,
                    action='session_rotation_failed',
                    resource_type='session',
                    resource_id=str(session_id),
                    details={'error': str(e)},
                    success=False
                )
            return None
    
    def force_session_security_upgrade(self, user_id: ObjectId, reason: str) -> int:
        """Force security upgrade for all user sessions."""
        try:
            # Deactivate all existing sessions
            result = self.collection.update_many(
                {'user_id': user_id, 'is_active': True},
                {
                    '$set': {
                        'is_active': False,
                        'deactivation_reason': f'security_upgrade: {reason}',
                        'deactivated_at': datetime.utcnow()
                    }
                }
            )
            
            # Log the upgrade
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=user_id,
                    action='session_security_upgrade',
                    resource_type='user_sessions',
                    resource_id=str(user_id),
                    details={
                        'reason': reason,
                        'sessions_deactivated': result.modified_count
                    }
                )
            
            return result.modified_count
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=user_id,
                    action='session_security_upgrade_failed',
                    resource_type='user_sessions',
                    resource_id=str(user_id),
                    details={'error': str(e), 'reason': reason},
                    success=False
                )
            return 0
    
    def detect_session_anomalies(self, user_id: ObjectId) -> List[Dict[str, Any]]:
        """Detect anomalies in user session patterns."""
        anomalies = []
        
        # Get recent sessions
        recent_sessions = list(self.collection.find({
            'user_id': user_id,
            'created_at': {'$gte': datetime.utcnow() - timedelta(days=7)}
        }).sort('created_at', -1))
        
        if len(recent_sessions) < 2:
            return anomalies
        
        # Analyze IP patterns
        ip_hashes = [s.get('device_info', {}).get('ip_hash') for s in recent_sessions if s.get('device_info', {}).get('ip_hash')]
        unique_ips = len(set(ip_hashes))
        
        if unique_ips > 5:  # More than 5 different IPs in a week
            anomalies.append({
                'type': 'multiple_ip_addresses',
                'severity': 'medium',
                'details': {'unique_ip_count': unique_ips},
                'description': f'User accessed from {unique_ips} different IP addresses'
            })
        
        # Analyze time patterns
        login_hours = [s['created_at'].hour for s in recent_sessions]
        off_hours_logins = sum(1 for hour in login_hours if hour < 6 or hour > 22)
        
        if off_hours_logins > len(recent_sessions) * 0.7:  # More than 70% off-hours
            anomalies.append({
                'type': 'unusual_login_times',
                'severity': 'low',
                'details': {'off_hours_percentage': (off_hours_logins / len(recent_sessions)) * 100},
                'description': 'Unusual login time patterns detected'
            })
        
        # Analyze session duration patterns
        durations = []
        for session in recent_sessions:
            if session.get('deactivated_at'):
                duration = (session['deactivated_at'] - session['created_at']).total_seconds() / 3600
                durations.append(duration)
        
        if durations:
            avg_duration = sum(durations) / len(durations)
            if avg_duration < 0.1:  # Very short sessions (< 6 minutes)
                anomalies.append({
                    'type': 'very_short_sessions',
                    'severity': 'medium',
                    'details': {'average_duration_hours': avg_duration},
                    'description': 'Unusually short session durations detected'
                })
        
        return anomalies
    
    def get_session_security_report(self, user_id: Optional[ObjectId] = None) -> Dict[str, Any]:
        """Generate comprehensive session security report."""
        query = {}
        if user_id:
            query['user_id'] = user_id
        
        # Basic statistics
        total_sessions = self.collection.count_documents(query)
        active_sessions = self.collection.count_documents({**query, 'is_active': True})
        
        # Recent activity (last 24 hours)
        recent_query = {
            **query,
            'created_at': {'$gte': datetime.utcnow() - timedelta(hours=24)}
        }
        recent_sessions = self.collection.count_documents(recent_query)
        
        # Security events
        security_events = []
        if user_id:
            user_anomalies = self.detect_session_anomalies(user_id)
            security_events.extend(user_anomalies)
        
        # Session distribution by login method
        pipeline = [
            {'$match': query},
            {'$group': {'_id': '$login_method', 'count': {'$sum': 1}}}
        ]
        login_methods = {result['_id']: result['count'] for result in self.collection.aggregate(pipeline)}
        
        # Expired sessions needing cleanup
        expired_sessions = self.collection.count_documents({
            **query,
            'expires_at': {'$lt': datetime.utcnow()}
        })
        
        return {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'recent_sessions_24h': recent_sessions,
            'expired_sessions_needing_cleanup': expired_sessions,
            'login_method_distribution': login_methods,
            'security_events': security_events,
            'security_configuration': self.config,
            'report_generated_at': datetime.utcnow().isoformat()
        }
    
    def cleanup_expired_sessions(self) -> Dict[str, int]:
        """Clean up expired and inactive sessions."""
        now = datetime.utcnow()
        
        # Remove expired sessions
        expired_result = self.collection.delete_many({
            'expires_at': {'$lt': now}
        })
        
        # Remove old inactive sessions (older than 7 days)
        old_inactive_result = self.collection.delete_many({
            'is_active': False,
            'updated_at': {'$lt': now - timedelta(days=7)}
        })
        
        # Deactivate idle sessions
        idle_cutoff = now - timedelta(minutes=self.config['idle_timeout_minutes'])
        idle_result = self.collection.update_many(
            {
                'is_active': True,
                'last_activity': {'$lt': idle_cutoff}
            },
            {
                '$set': {
                    'is_active': False,
                    'deactivation_reason': 'idle_timeout',
                    'deactivated_at': now
                }
            }
        )
        
        cleanup_stats = {
            'expired_sessions_deleted': expired_result.deleted_count,
            'old_inactive_sessions_deleted': old_inactive_result.deleted_count,
            'idle_sessions_deactivated': idle_result.modified_count
        }
        
        # Log cleanup if significant
        total_cleaned = sum(cleanup_stats.values())
        if total_cleaned > 0 and self.audit_logger:
            self.audit_logger.log_activity(
                user_id=None,
                action='session_cleanup_completed',
                resource_type='system',
                resource_id='session_manager',
                details=cleanup_stats
            )
        
        return cleanup_stats
    
    def _generate_secure_token(self) -> str:
        """Generate a cryptographically secure session token."""
        return secrets.token_urlsafe(self.config['session_token_length'])
    
    def _hash_ip(self, ip_address: str) -> str:
        """Hash IP address for privacy while maintaining consistency checks."""
        return hashlib.sha256(ip_address.encode()).hexdigest()[:16]
    
    def _hash_user_agent(self, user_agent: str) -> str:
        """Hash user agent for privacy while maintaining consistency checks."""
        return hashlib.sha256(user_agent.encode()).hexdigest()[:16]
    
    def _enforce_session_limits(self, user_id: ObjectId) -> None:
        """Enforce maximum sessions per user."""
        active_sessions = list(self.collection.find({
            'user_id': user_id,
            'is_active': True
        }).sort('last_activity', 1))  # Oldest first
        
        if len(active_sessions) >= self.config['max_sessions_per_user']:
            # Deactivate oldest sessions
            sessions_to_remove = len(active_sessions) - self.config['max_sessions_per_user'] + 1
            
            for session in active_sessions[:sessions_to_remove]:
                self._deactivate_session(session['_id'], 'session_limit_exceeded')
    
    def _deactivate_session(self, session_id: ObjectId, reason: str) -> None:
        """Deactivate a session with reason."""
        self.collection.update_one(
            {'_id': session_id},
            {
                '$set': {
                    'is_active': False,
                    'deactivation_reason': reason,
                    'deactivated_at': datetime.utcnow()
                }
            }
        )
    
    def _update_session_activity(self, session_id: ObjectId) -> None:
        """Update session activity timestamp and idle timeout."""
        new_idle_expires = datetime.utcnow() + timedelta(minutes=self.config['idle_timeout_minutes'])
        
        self.collection.update_one(
            {'_id': session_id},
            {
                '$set': {
                    'last_activity': datetime.utcnow(),
                    'device_info.idle_expires_at': new_idle_expires
                }
            }
        )
    
    def _log_suspicious_activity(self, user_id: ObjectId, activity_type: str, details: Dict[str, Any]) -> None:
        """Log suspicious session activity."""
        if self.audit_logger:
            self.audit_logger.log_activity(
                user_id=user_id,
                action=f'suspicious_session_activity_{activity_type}',
                resource_type='session_security',
                resource_id=str(user_id),
                details=details,
                severity='warning'
            )
        
        # Track for pattern analysis
        user_key = str(user_id)
        if user_key not in self.suspicious_activities:
            self.suspicious_activities[user_key] = []
        
        self.suspicious_activities[user_key].append({
            'type': activity_type,
            'timestamp': datetime.utcnow(),
            'details': details
        })
        
        # Clean old entries (keep last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.suspicious_activities[user_key] = [
            activity for activity in self.suspicious_activities[user_key]
            if activity['timestamp'] > cutoff
        ]