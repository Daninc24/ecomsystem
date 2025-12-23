"""
Authentication manager for session management and user authentication
"""

import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Tuple, List
from bson import ObjectId

from .base_service import BaseService
from ..models.user import User, UserSession, UserStatus


class AuthenticationManager(BaseService):
    """Service for managing user authentication and sessions."""
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'user_sessions'
    
    def __init__(self, db, user_manager=None, audit_logger=None):
        super().__init__(db)
        self.user_manager = user_manager
        self.audit_logger = audit_logger
        self.sessions_collection = db.user_sessions
        self.users_collection = db.users
        
        # Configuration
        self.session_timeout_hours = 24
        self.max_login_attempts = 5
        self.lockout_duration_hours = 1
        self.session_cleanup_interval = 3600  # 1 hour in seconds
    
    def authenticate_user(self, username_or_email: str, password: str, ip_address: str = '', user_agent: str = '') -> Tuple[Optional[User], Optional[UserSession], str]:
        """
        Authenticate user and create session.
        Returns (user, session, message)
        """
        try:
            # Find user by username or email
            user = None
            if '@' in username_or_email:
                user = self.user_manager.get_user_by_email(username_or_email) if self.user_manager else None
            else:
                user = self.user_manager.get_user_by_username(username_or_email) if self.user_manager else None
            
            if not user:
                # Log failed attempt
                if self.audit_logger:
                    self.audit_logger.log_activity(
                        user_id=None,
                        action='login_failed',
                        resource_type='authentication',
                        resource_id=username_or_email,
                        details={
                            'reason': 'user_not_found',
                            'ip_address': ip_address,
                            'user_agent': user_agent
                        },
                        success=False
                    )
                return None, None, "Invalid username/email or password"
            
            # Check if account is locked
            if user.is_locked():
                if self.audit_logger:
                    self.audit_logger.log_activity(
                        user_id=user.id,
                        action='login_failed',
                        resource_type='authentication',
                        resource_id=str(user.id),
                        details={
                            'reason': 'account_locked',
                            'locked_until': user.locked_until.isoformat() if user.locked_until else None,
                            'ip_address': ip_address
                        },
                        success=False
                    )
                return None, None, f"Account is locked until {user.locked_until}"
            
            # Check if account is active
            if not user.is_active():
                if self.audit_logger:
                    self.audit_logger.log_activity(
                        user_id=user.id,
                        action='login_failed',
                        resource_type='authentication',
                        resource_id=str(user.id),
                        details={
                            'reason': 'account_inactive',
                            'status': user.status.value,
                            'ip_address': ip_address
                        },
                        success=False
                    )
                return None, None, f"Account is {user.status.value}"
            
            # Verify password
            if not self.user_manager.verify_password(user, password):
                # Increment login attempts
                attempts = self.user_manager.increment_login_attempts(user.id)
                
                # Lock account if too many attempts
                if attempts >= self.max_login_attempts:
                    self.user_manager.lock_user_account(user.id, self.lockout_duration_hours)
                    message = f"Account locked due to {self.max_login_attempts} failed login attempts"
                else:
                    remaining = self.max_login_attempts - attempts
                    message = f"Invalid password. {remaining} attempts remaining"
                
                # Log failed attempt
                if self.audit_logger:
                    self.audit_logger.log_activity(
                        user_id=user.id,
                        action='login_failed',
                        resource_type='authentication',
                        resource_id=str(user.id),
                        details={
                            'reason': 'invalid_password',
                            'login_attempts': attempts,
                            'ip_address': ip_address
                        },
                        success=False
                    )
                
                return None, None, message
            
            # Authentication successful - create session
            session = self._create_session(user.id, ip_address, user_agent)
            
            # Update user's last login
            self.user_manager.update_last_login(user.id)
            
            # Log successful login
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=user.id,
                    action='login_successful',
                    resource_type='authentication',
                    resource_id=str(user.id),
                    details={
                        'session_id': str(session.id),
                        'ip_address': ip_address,
                        'user_agent': user_agent
                    }
                )
            
            return user, session, "Login successful"
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=None,
                    action='login_error',
                    resource_type='authentication',
                    resource_id=username_or_email,
                    details={
                        'error': str(e),
                        'ip_address': ip_address
                    },
                    success=False
                )
            raise
    
    def _create_session(self, user_id: ObjectId, ip_address: str = '', user_agent: str = '') -> UserSession:
        """Create a new user session."""
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=self.session_timeout_hours)
        
        session = UserSession(
            user_id=user_id,
            session_token=session_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
            is_active=True,
            last_activity=datetime.utcnow(),
            login_method='password'
        )
        
        result = self.sessions_collection.insert_one(session.to_dict())
        session.id = result.inserted_id
        
        return session
    
    def validate_session(self, session_token: str) -> Tuple[Optional[User], Optional[UserSession]]:
        """Validate session token and return user and session if valid."""
        try:
            # Find session
            session_data = self.sessions_collection.find_one({'session_token': session_token})
            if not session_data:
                return None, None
            
            session_data['id'] = session_data.pop('_id')
            session = UserSession(**session_data)
            
            # Check if session is valid
            if not session.is_valid():
                # Deactivate expired session
                if session.is_expired():
                    self.deactivate_session(session.id)
                return None, None
            
            # Get user
            user = self.user_manager.get_user(session.user_id) if self.user_manager else None
            if not user or not user.is_active():
                # Deactivate session for inactive user
                self.deactivate_session(session.id)
                return None, None
            
            # Update last activity
            self._update_session_activity(session.id)
            
            return user, session
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=None,
                    action='session_validation_error',
                    resource_type='authentication',
                    resource_id=session_token[:8] + '...',
                    details={'error': str(e)},
                    success=False
                )
            return None, None
    
    def _update_session_activity(self, session_id: ObjectId) -> None:
        """Update session's last activity timestamp."""
        self.sessions_collection.update_one(
            {'_id': session_id},
            {'$set': {'last_activity': datetime.utcnow()}}
        )
    
    def extend_session(self, session_token: str, hours: int = None) -> bool:
        """Extend session expiration time."""
        try:
            hours = hours or self.session_timeout_hours
            new_expires_at = datetime.utcnow() + timedelta(hours=hours)
            
            result = self.sessions_collection.update_one(
                {'session_token': session_token, 'is_active': True},
                {
                    '$set': {
                        'expires_at': new_expires_at,
                        'last_activity': datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=None,
                    action='session_extend_error',
                    resource_type='authentication',
                    resource_id=session_token[:8] + '...',
                    details={'error': str(e)},
                    success=False
                )
            return False
    
    def logout_user(self, session_token: str) -> bool:
        """Logout user by deactivating session."""
        try:
            # Get session info for logging
            session_data = self.sessions_collection.find_one({'session_token': session_token})
            
            result = self.sessions_collection.update_one(
                {'session_token': session_token},
                {'$set': {'is_active': False}}
            )
            
            if result.modified_count > 0 and session_data:
                # Log logout
                if self.audit_logger:
                    self.audit_logger.log_activity(
                        user_id=session_data.get('user_id'),
                        action='logout',
                        resource_type='authentication',
                        resource_id=str(session_data.get('_id')),
                        details={'session_token': session_token[:8] + '...'}
                    )
                return True
            
            return False
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=None,
                    action='logout_error',
                    resource_type='authentication',
                    resource_id=session_token[:8] + '...',
                    details={'error': str(e)},
                    success=False
                )
            return False
    
    def deactivate_session(self, session_id: ObjectId) -> bool:
        """Deactivate a specific session."""
        result = self.sessions_collection.update_one(
            {'_id': session_id},
            {'$set': {'is_active': False}}
        )
        return result.modified_count > 0
    
    def deactivate_all_user_sessions(self, user_id: ObjectId, except_session_id: Optional[ObjectId] = None) -> int:
        """Deactivate all sessions for a user, optionally except one."""
        query = {'user_id': user_id}
        if except_session_id:
            query['_id'] = {'$ne': except_session_id}
        
        result = self.sessions_collection.update_many(
            query,
            {'$set': {'is_active': False}}
        )
        
        # Log the action
        if self.audit_logger and result.modified_count > 0:
            self.audit_logger.log_activity(
                user_id=user_id,
                action='sessions_deactivated',
                resource_type='authentication',
                resource_id=str(user_id),
                details={
                    'deactivated_count': result.modified_count,
                    'except_session': str(except_session_id) if except_session_id else None
                }
            )
        
        return result.modified_count
    
    def get_user_sessions(self, user_id: ObjectId, active_only: bool = True) -> List[UserSession]:
        """Get all sessions for a user."""
        query = {'user_id': user_id}
        if active_only:
            query['is_active'] = True
        
        cursor = self.sessions_collection.find(query).sort('last_activity', -1)
        
        sessions = []
        for session_data in cursor:
            session_data['id'] = session_data.pop('_id')
            sessions.append(UserSession(**session_data))
        
        return sessions
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions from database."""
        result = self.sessions_collection.delete_many({
            '$or': [
                {'expires_at': {'$lt': datetime.utcnow()}},
                {'is_active': False, 'last_activity': {'$lt': datetime.utcnow() - timedelta(days=7)}}
            ]
        })
        
        if self.audit_logger and result.deleted_count > 0:
            self.audit_logger.log_activity(
                user_id=None,
                action='sessions_cleaned',
                resource_type='system',
                resource_id='session_cleanup',
                details={'cleaned_count': result.deleted_count}
            )
        
        return result.deleted_count
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get session statistics."""
        now = datetime.utcnow()
        
        total_sessions = self.sessions_collection.count_documents({})
        active_sessions = self.sessions_collection.count_documents({'is_active': True})
        expired_sessions = self.sessions_collection.count_documents({'expires_at': {'$lt': now}})
        
        # Recent activity (last 24 hours)
        recent_logins = self.sessions_collection.count_documents({
            'created_at': {'$gte': now - timedelta(hours=24)}
        })
        
        return {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'expired_sessions': expired_sessions,
            'recent_logins_24h': recent_logins,
            'cleanup_needed': expired_sessions > 0
        }
    
    def force_password_reset(self, user_id: ObjectId, reset_by: Optional[ObjectId] = None) -> bool:
        """Force password reset by deactivating all sessions and marking user."""
        try:
            # Deactivate all user sessions
            deactivated = self.deactivate_all_user_sessions(user_id)
            
            # Mark user as requiring password reset (could be implemented as a flag)
            # For now, we'll just log the action
            
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=reset_by,
                    action='password_reset_forced',
                    resource_type='user',
                    resource_id=str(user_id),
                    details={'sessions_deactivated': deactivated}
                )
            
            return True
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=reset_by,
                    action='password_reset_force_failed',
                    resource_type='user',
                    resource_id=str(user_id),
                    details={'error': str(e)},
                    success=False
                )
            return False