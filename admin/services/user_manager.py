"""
User management service for comprehensive user CRUD operations
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from .base_service import BaseService
from ..models.user import User, UserRole, UserStatus, Permission
from ..models.audit import ActivityLog


class UserManager(BaseService):
    """Service for managing users with comprehensive CRUD operations."""
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'users'
    
    def __init__(self, db, audit_logger=None, permission_engine=None):
        super().__init__(db)
        self.audit_logger = audit_logger
        self.permission_engine = permission_engine
        self.collection = db.users
        self.sessions_collection = db.user_sessions
    
    def create_user(self, user_data: Dict[str, Any], created_by: Optional[ObjectId] = None) -> User:
        """Create a new user with validation and audit logging."""
        try:
            # Validate required fields
            required_fields = ['username', 'email', 'password']
            for field in required_fields:
                if not user_data.get(field):
                    raise ValueError(f"Missing required field: {field}")
            
            # Check for existing username or email
            existing_user = self.collection.find_one({
                '$or': [
                    {'username': user_data['username']},
                    {'email': user_data['email']}
                ]
            })
            
            if existing_user:
                if existing_user['username'] == user_data['username']:
                    raise ValueError("Username already exists")
                if existing_user['email'] == user_data['email']:
                    raise ValueError("Email already exists")
            
            # Hash password
            password_hash = self._hash_password(user_data['password'])
            user_data['password_hash'] = password_hash
            del user_data['password']  # Remove plain password
            
            # Set default values
            user_data.setdefault('role', UserRole.CUSTOMER.value)
            user_data.setdefault('status', UserStatus.ACTIVE.value)
            user_data.setdefault('created_by', created_by)
            user_data.setdefault('email_verified', False)
            user_data.setdefault('login_attempts', 0)
            
            # Get role permissions if permission engine is available
            role = UserRole(user_data['role'])
            if hasattr(self, 'permission_engine') and self.permission_engine:
                role_permissions = self.permission_engine.get_role_permissions(role)
                user_data['permissions'] = [p.value for p in role_permissions]
            else:
                user_data.setdefault('permissions', [])
            
            # Create user object
            user = User(**user_data)
            
            # Insert into database
            result = self.collection.insert_one(user.to_dict())
            user.id = result.inserted_id
            
            # Log the action
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=user.id,  # Log for the created user
                    action='user_created',
                    resource_type='user',
                    resource_id=str(user.id),
                    details={
                        'username': user.username,
                        'email': user.email,
                        'role': user.role.value,
                        'created_by': str(created_by) if created_by else None
                    }
                )
            
            return user
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=created_by,
                    action='user_create_failed',
                    resource_type='user',
                    resource_id=None,
                    details={'error': str(e), 'username': user_data.get('username')},
                    success=False
                )
            raise
    
    def get_user(self, user_id: ObjectId) -> Optional[User]:
        """Get user by ID."""
        user_data = self.collection.find_one({'_id': user_id})
        if user_data:
            user_data['id'] = user_data.pop('_id')
            return User(**user_data)
        return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        user_data = self.collection.find_one({'username': username})
        if user_data:
            user_data['id'] = user_data.pop('_id')
            return User(**user_data)
        return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        user_data = self.collection.find_one({'email': email})
        if user_data:
            user_data['id'] = user_data.pop('_id')
            return User(**user_data)
        return None
    
    def update_user(self, user_id: ObjectId, updates: Dict[str, Any], updated_by: Optional[ObjectId] = None) -> bool:
        """Update user with validation and audit logging."""
        try:
            # Get existing user
            existing_user = self.get_user(user_id)
            if not existing_user:
                raise ValueError("User not found")
            
            # Handle password update
            if 'password' in updates:
                updates['password_hash'] = self._hash_password(updates['password'])
                del updates['password']
            
            # Update timestamp
            updates['updated_at'] = datetime.utcnow()
            if updated_by:
                updates['updated_by'] = updated_by
            
            # Perform update
            result = self.collection.update_one(
                {'_id': user_id},
                {'$set': updates}
            )
            
            if result.modified_count > 0:
                # Log the action
                if self.audit_logger:
                    self.audit_logger.log_activity(
                        user_id=updated_by,
                        action='user_updated',
                        resource_type='user',
                        resource_id=str(user_id),
                        details={
                            'updated_fields': list(updates.keys()),
                            'username': existing_user.username
                        }
                    )
                return True
            
            return False
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=updated_by,
                    action='user_update_failed',
                    resource_type='user',
                    resource_id=str(user_id),
                    details={'error': str(e)},
                    success=False
                )
            raise
    
    def delete_user(self, user_id: ObjectId, deleted_by: Optional[ObjectId] = None) -> bool:
        """Delete user with audit logging."""
        try:
            # Get user info for logging
            user = self.get_user(user_id)
            if not user:
                raise ValueError("User not found")
            
            # Delete user
            result = self.collection.delete_one({'_id': user_id})
            
            if result.deleted_count > 0:
                # Also delete user sessions
                self.sessions_collection.delete_many({'user_id': user_id})
                
                # Log the action
                if self.audit_logger:
                    self.audit_logger.log_activity(
                        user_id=deleted_by,
                        action='user_deleted',
                        resource_type='user',
                        resource_id=str(user_id),
                        details={
                            'username': user.username,
                            'email': user.email
                        }
                    )
                return True
            
            return False
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=deleted_by,
                    action='user_delete_failed',
                    resource_type='user',
                    resource_id=str(user_id),
                    details={'error': str(e)},
                    success=False
                )
            raise
    
    def suspend_user(self, user_id: ObjectId, reason: str, suspended_by: Optional[ObjectId] = None, duration_hours: Optional[int] = None) -> bool:
        """Suspend user account with optional duration."""
        try:
            updates = {
                'status': UserStatus.SUSPENDED.value,
                'updated_at': datetime.utcnow(),
                'updated_by': suspended_by
            }
            
            # Set suspension end time if duration provided
            if duration_hours:
                updates['locked_until'] = datetime.utcnow() + timedelta(hours=duration_hours)
            
            result = self.collection.update_one(
                {'_id': user_id},
                {'$set': updates}
            )
            
            if result.modified_count > 0:
                # Invalidate all user sessions
                self.sessions_collection.update_many(
                    {'user_id': user_id},
                    {'$set': {'is_active': False}}
                )
                
                # Log the action
                if self.audit_logger:
                    user = self.get_user(user_id)
                    self.audit_logger.log_activity(
                        user_id=suspended_by,
                        action='user_suspended',
                        resource_type='user',
                        resource_id=str(user_id),
                        details={
                            'reason': reason,
                            'duration_hours': duration_hours,
                            'username': user.username if user else 'unknown'
                        }
                    )
                return True
            
            return False
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=suspended_by,
                    action='user_suspend_failed',
                    resource_type='user',
                    resource_id=str(user_id),
                    details={'error': str(e), 'reason': reason},
                    success=False
                )
            raise
    
    def activate_user(self, user_id: ObjectId, activated_by: Optional[ObjectId] = None) -> bool:
        """Activate user account."""
        try:
            updates = {
                'status': UserStatus.ACTIVE.value,
                'locked_until': None,
                'login_attempts': 0,
                'updated_at': datetime.utcnow(),
                'updated_by': activated_by
            }
            
            result = self.collection.update_one(
                {'_id': user_id},
                {'$set': updates, '$unset': {'locked_until': ''}}
            )
            
            if result.modified_count > 0:
                # Log the action
                if self.audit_logger:
                    user = self.get_user(user_id)
                    self.audit_logger.log_activity(
                        user_id=activated_by,
                        action='user_activated',
                        resource_type='user',
                        resource_id=str(user_id),
                        details={
                            'username': user.username if user else 'unknown'
                        }
                    )
                return True
            
            return False
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=activated_by,
                    action='user_activate_failed',
                    resource_type='user',
                    resource_id=str(user_id),
                    details={'error': str(e)},
                    success=False
                )
            raise
    
    def list_users(self, filters: Optional[Dict[str, Any]] = None, limit: int = 50, skip: int = 0) -> List[User]:
        """List users with optional filtering."""
        query = filters or {}
        cursor = self.collection.find(query).limit(limit).skip(skip).sort('created_at', -1)
        
        users = []
        for user_data in cursor:
            user_data['id'] = user_data.pop('_id')
            users.append(User(**user_data))
        
        return users
    
    def count_users(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count users with optional filtering."""
        query = filters or {}
        return self.collection.count_documents(query)
    
    def verify_password(self, user: User, password: str) -> bool:
        """Verify user password."""
        return self._verify_password(password, user.password_hash)
    
    def update_last_login(self, user_id: ObjectId) -> None:
        """Update user's last login timestamp."""
        self.collection.update_one(
            {'_id': user_id},
            {
                '$set': {
                    'last_login': datetime.utcnow(),
                    'login_attempts': 0
                }
            }
        )
    
    def increment_login_attempts(self, user_id: ObjectId) -> int:
        """Increment failed login attempts and return new count."""
        result = self.collection.update_one(
            {'_id': user_id},
            {'$inc': {'login_attempts': 1}}
        )
        
        # Get updated count
        user = self.get_user(user_id)
        return user.login_attempts if user else 0
    
    def lock_user_account(self, user_id: ObjectId, hours: int = 1) -> None:
        """Lock user account for specified hours."""
        lock_until = datetime.utcnow() + timedelta(hours=hours)
        self.collection.update_one(
            {'_id': user_id},
            {'$set': {'locked_until': lock_until}}
        )
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash."""
        try:
            salt, password_hash = stored_hash.split(':')
            computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return computed_hash == password_hash
        except ValueError:
            return False