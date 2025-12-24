"""
User Management Service for SQLite
Handles user operations and management with advanced features
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from models_sqlite import User, Role, ActivityLog, db
from werkzeug.security import generate_password_hash
import re


class UserManager:
    """Advanced service for managing users and roles."""
    
    def __init__(self, database):
        self.db = database
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID with detailed information."""
        user = User.query.get(user_id)
        if user:
            user_data = user.to_dict()
            # Add additional computed fields
            user_data['total_orders'] = user.orders.count() if hasattr(user, 'orders') else 0
            user_data['account_age_days'] = (datetime.now(timezone.utc) - user.created_at).days
            user_data['is_online'] = self._is_user_online(user)
            return user_data
        return None
    
    def list_users(self, page: int = 1, per_page: int = 50, role: str = None, 
                   status: str = None, search: str = None) -> Dict[str, Any]:
        """List all users with advanced filtering and pagination."""
        query = User.query
        
        # Apply filters
        if role:
            query = query.filter(User.roles.any(Role.name == role))
        
        if status == 'active':
            query = query.filter_by(is_active=True)
        elif status == 'inactive':
            query = query.filter_by(is_active=False)
        elif status == 'verified':
            query = query.filter_by(is_verified=True)
        elif status == 'unverified':
            query = query.filter_by(is_verified=False)
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                db.or_(
                    User.username.ilike(search_filter),
                    User.email.ilike(search_filter),
                    User.first_name.ilike(search_filter),
                    User.last_name.ilike(search_filter)
                )
            )
        
        # Paginate results
        users = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # Enhance user data
        user_list = []
        for user in users.items:
            user_data = user.to_dict()
            user_data['total_orders'] = user.orders.count() if hasattr(user, 'orders') else 0
            user_data['account_age_days'] = (datetime.now(timezone.utc) - user.created_at).days
            user_data['is_online'] = self._is_user_online(user)
            user_list.append(user_data)
        
        return {
            'users': user_list,
            'pagination': {
                'page': users.page,
                'pages': users.pages,
                'per_page': users.per_page,
                'total': users.total,
                'has_next': users.has_next,
                'has_prev': users.has_prev
            },
            'filters': {
                'role': role,
                'status': status,
                'search': search
            }
        }
    
    def create_user(self, user_data: Dict[str, Any], created_by: Optional[int] = None) -> Dict[str, Any]:
        """Create a new user with validation."""
        try:
            # Validate user data
            validation = self.validate_user_data(user_data)
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors']
                }
            
            # Check for existing users
            if User.query.filter_by(email=user_data['email']).first():
                return {
                    'success': False,
                    'errors': ['Email already exists']
                }
            
            if User.query.filter_by(username=user_data['username']).first():
                return {
                    'success': False,
                    'errors': ['Username already exists']
                }
            
            # Create user
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                phone=user_data.get('phone'),
                is_active=user_data.get('is_active', True),
                is_verified=user_data.get('is_verified', False),
                is_vendor=user_data.get('is_vendor', False)
            )
            user.set_password(user_data['password'])
            
            # Assign roles
            if 'roles' in user_data:
                for role_name in user_data['roles']:
                    role = Role.query.filter_by(name=role_name).first()
                    if role:
                        user.roles.append(role)
            else:
                # Assign default role
                default_role = Role.query.filter_by(is_default=True).first()
                if default_role:
                    user.roles.append(default_role)
            
            db.session.add(user)
            db.session.commit()
            
            # Log user creation
            self._log_user_action('create', user.id, created_by, {
                'username': user.username,
                'email': user.email,
                'roles': [role.name for role in user.roles]
            })
            
            return {
                'success': True,
                'user': user.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def update_user(self, user_id: int, user_data: Dict[str, Any], 
                   updated_by: Optional[int] = None) -> Dict[str, Any]:
        """Update user information with validation."""
        try:
            user = User.query.get(user_id)
            if not user:
                return {
                    'success': False,
                    'errors': ['User not found']
                }
            
            # Store old values for logging
            old_values = {
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'roles': [role.name for role in user.roles]
            }
            
            # Validate updates
            validation = self.validate_user_data(user_data, user_id)
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors']
                }
            
            # Update basic fields
            for key, value in user_data.items():
                if key == 'password':
                    user.set_password(value)
                elif key == 'roles':
                    # Update roles
                    user.roles.clear()
                    for role_name in value:
                        role = Role.query.filter_by(name=role_name).first()
                        if role:
                            user.roles.append(role)
                elif hasattr(user, key) and key not in ['id', 'created_at', 'password_hash']:
                    setattr(user, key, value)
            
            user.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            # Log user update
            new_values = {
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'roles': [role.name for role in user.roles]
            }
            
            self._log_user_action('update', user.id, updated_by, {
                'old_values': old_values,
                'new_values': new_values,
                'changed_fields': list(user_data.keys())
            })
            
            return {
                'success': True,
                'user': user.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def delete_user(self, user_id: int, deleted_by: Optional[int] = None) -> Dict[str, Any]:
        """Delete a user with safety checks."""
        try:
            user = User.query.get(user_id)
            if not user:
                return {
                    'success': False,
                    'errors': ['User not found']
                }
            
            # Safety check: don't delete the last admin
            if user.has_role('admin'):
                admin_count = User.query.filter(User.roles.any(Role.name == 'admin')).count()
                if admin_count <= 1:
                    return {
                        'success': False,
                        'errors': ['Cannot delete the last admin user']
                    }
            
            # Store user data for logging
            user_data = {
                'username': user.username,
                'email': user.email,
                'roles': [role.name for role in user.roles]
            }
            
            db.session.delete(user)
            db.session.commit()
            
            # Log user deletion
            self._log_user_action('delete', user_id, deleted_by, user_data)
            
            return {
                'success': True,
                'message': 'User deleted successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def validate_user_data(self, user_data: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        """Validate user data before creating or updating."""
        errors = []
        
        # Username validation
        if 'username' in user_data:
            username = user_data['username']
            if not username or len(username) < 3:
                errors.append('Username must be at least 3 characters long')
            elif len(username) > 50:
                errors.append('Username must be less than 50 characters')
            elif not re.match(r'^[a-zA-Z0-9_]+$', username):
                errors.append('Username can only contain letters, numbers, and underscores')
            else:
                # Check for existing username (excluding current user if updating)
                existing = User.query.filter_by(username=username)
                if user_id:
                    existing = existing.filter(User.id != user_id)
                if existing.first():
                    errors.append('Username already exists')
        
        # Email validation
        if 'email' in user_data:
            email = user_data['email']
            if not email:
                errors.append('Email is required')
            elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                errors.append('Invalid email format')
            else:
                # Check for existing email (excluding current user if updating)
                existing = User.query.filter_by(email=email)
                if user_id:
                    existing = existing.filter(User.id != user_id)
                if existing.first():
                    errors.append('Email already exists')
        
        # Password validation
        if 'password' in user_data:
            password = user_data['password']
            if not password or len(password) < 6:
                errors.append('Password must be at least 6 characters long')
            elif len(password) > 128:
                errors.append('Password must be less than 128 characters')
        
        # Phone validation
        if 'phone' in user_data and user_data['phone']:
            phone = user_data['phone']
            if not re.match(r'^\+?[\d\s\-\(\)]+$', phone):
                errors.append('Invalid phone number format')
        
        # Role validation
        if 'roles' in user_data:
            roles = user_data['roles']
            if not isinstance(roles, list):
                errors.append('Roles must be a list')
            else:
                valid_roles = [role.name for role in Role.query.all()]
                for role in roles:
                    if role not in valid_roles:
                        errors.append(f'Invalid role: {role}')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def get_user_activity(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user activity history."""
        activities = ActivityLog.query.filter_by(user_id=user_id)\
                                     .order_by(ActivityLog.created_at.desc())\
                                     .limit(limit).all()
        
        return [
            {
                'id': activity.id,
                'action': activity.action,
                'resource_type': activity.resource_type,
                'resource_id': activity.resource_id,
                'details': activity.get_details(),
                'success': activity.success,
                'created_at': activity.created_at.isoformat(),
                'ip_address': activity.ip_address
            }
            for activity in activities
        ]
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """Get user statistics for dashboard."""
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        verified_users = User.query.filter_by(is_verified=True).count()
        vendor_users = User.query.filter_by(is_vendor=True).count()
        
        # Users registered in the last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - datetime.timedelta(days=30)
        new_users = User.query.filter(User.created_at >= thirty_days_ago).count()
        
        # Role distribution
        role_stats = {}
        for role in Role.query.all():
            role_stats[role.name] = User.query.filter(User.roles.any(Role.id == role.id)).count()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'verified_users': verified_users,
            'vendor_users': vendor_users,
            'new_users_30_days': new_users,
            'role_distribution': role_stats,
            'activity_rate': round((active_users / total_users * 100) if total_users > 0 else 0, 2)
        }
    
    def _is_user_online(self, user: User) -> bool:
        """Check if user is currently online (placeholder)."""
        # This would integrate with session tracking or WebSocket connections
        # For now, consider users online if they logged in within the last 15 minutes
        if user.last_login:
            return (datetime.now(timezone.utc) - user.last_login).seconds < 900
        return False
    
    def _log_user_action(self, action: str, user_id: int, performed_by: Optional[int], details: Dict[str, Any]):
        """Log user management actions."""
        try:
            log = ActivityLog(
                user_id=performed_by,
                action=f'user_{action}',
                resource_type='user',
                resource_id=str(user_id),
                success=True
            )
            log.set_details(details)
            db.session.add(log)
            db.session.commit()
        except Exception:
            pass  # Don't fail the main operation if logging fails