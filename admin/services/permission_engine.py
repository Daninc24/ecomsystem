"""
Permission engine for role-based access control
"""

from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from bson import ObjectId

from .base_service import BaseService
from ..models.user import User, UserRole, Permission, RolePermissionMapping


class PermissionEngine(BaseService):
    """Service for managing role-based access control and permissions."""
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'role_permissions'
    
    def __init__(self, db, audit_logger=None):
        super().__init__(db)
        self.audit_logger = audit_logger
        self.users_collection = db.users
        self.role_permissions_collection = db.role_permissions
        self.permission_cache = {}
        self._initialize_default_permissions()
    
    def _initialize_default_permissions(self) -> None:
        """Initialize default role-permission mappings."""
        default_mappings = {
            UserRole.ADMIN: [
                # Full access to everything
                Permission.CONFIG_READ, Permission.CONFIG_WRITE,
                Permission.CONTENT_READ, Permission.CONTENT_WRITE, Permission.CONTENT_PUBLISH,
                Permission.USER_READ, Permission.USER_WRITE, Permission.USER_DELETE, Permission.USER_SUSPEND,
                Permission.PRODUCT_READ, Permission.PRODUCT_WRITE, Permission.PRODUCT_DELETE,
                Permission.ORDER_READ, Permission.ORDER_WRITE, Permission.ORDER_REFUND,
                Permission.ANALYTICS_READ, Permission.ANALYTICS_EXPORT,
                Permission.SYSTEM_MONITOR, Permission.SYSTEM_BACKUP, Permission.SYSTEM_MAINTENANCE
            ],
            UserRole.MODERATOR: [
                # Content and user management
                Permission.CONFIG_READ,
                Permission.CONTENT_READ, Permission.CONTENT_WRITE, Permission.CONTENT_PUBLISH,
                Permission.USER_READ, Permission.USER_WRITE, Permission.USER_SUSPEND,
                Permission.PRODUCT_READ, Permission.PRODUCT_WRITE,
                Permission.ORDER_READ, Permission.ORDER_WRITE,
                Permission.ANALYTICS_READ
            ],
            UserRole.VENDOR: [
                # Own products and orders
                Permission.PRODUCT_READ, Permission.PRODUCT_WRITE,
                Permission.ORDER_READ, Permission.ORDER_WRITE,
                Permission.ANALYTICS_READ
            ],
            UserRole.CUSTOMER: [
                # Basic read access
                Permission.PRODUCT_READ,
                Permission.ORDER_READ
            ],
            UserRole.GUEST: [
                # Minimal access
                Permission.PRODUCT_READ
            ]
        }
        
        for role, permissions in default_mappings.items():
            existing = self.role_permissions_collection.find_one({'role': role.value})
            if not existing:
                mapping = RolePermissionMapping(
                    role=role,
                    permissions=permissions,
                    is_default=True,
                    description=f"Default permissions for {role.value} role"
                )
                self.role_permissions_collection.insert_one(mapping.to_dict())
    
    def get_role_permissions(self, role: UserRole) -> List[Permission]:
        """Get permissions for a specific role."""
        # Check cache first
        cache_key = f"role_{role.value}"
        if cache_key in self.permission_cache:
            return self.permission_cache[cache_key]
        
        # Query database
        mapping_data = self.role_permissions_collection.find_one({'role': role.value})
        if mapping_data:
            permissions = [Permission(p) for p in mapping_data['permissions']]
            self.permission_cache[cache_key] = permissions
            return permissions
        
        return []
    
    def update_role_permissions(self, role: UserRole, permissions: List[Permission], updated_by: Optional[ObjectId] = None) -> bool:
        """Update permissions for a role."""
        try:
            permission_values = [p.value for p in permissions]
            
            result = self.role_permissions_collection.update_one(
                {'role': role.value},
                {
                    '$set': {
                        'permissions': permission_values,
                        'updated_at': datetime.utcnow(),
                        'updated_by': updated_by
                    }
                },
                upsert=True
            )
            
            # Clear cache
            cache_key = f"role_{role.value}"
            if cache_key in self.permission_cache:
                del self.permission_cache[cache_key]
            
            # Update all users with this role to have immediate effect
            self._propagate_role_permissions(role, permissions, updated_by)
            
            # Log the action
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=updated_by,
                    action='role_permissions_updated',
                    resource_type='role',
                    resource_id=role.value,
                    details={
                        'permissions': permission_values,
                        'permission_count': len(permissions)
                    }
                )
            
            return result.modified_count > 0 or result.upserted_id is not None
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=updated_by,
                    action='role_permissions_update_failed',
                    resource_type='role',
                    resource_id=role.value,
                    details={'error': str(e)},
                    success=False
                )
            raise
    
    def _propagate_role_permissions(self, role: UserRole, permissions: List[Permission], updated_by: Optional[ObjectId] = None) -> None:
        """Propagate role permission changes to all users with that role."""
        permission_values = [p.value for p in permissions]
        
        # Update all users with this role
        result = self.users_collection.update_many(
            {'role': role.value},
            {
                '$set': {
                    'permissions': permission_values,
                    'updated_at': datetime.utcnow(),
                    'updated_by': updated_by
                }
            }
        )
        
        # Log the propagation
        if self.audit_logger and result.modified_count > 0:
            self.audit_logger.log_activity(
                user_id=updated_by,
                action='permissions_propagated',
                resource_type='role',
                resource_id=role.value,
                details={
                    'affected_users': result.modified_count,
                    'permissions': permission_values
                }
            )
    
    def assign_user_permissions(self, user_id: ObjectId, permissions: List[Permission], assigned_by: Optional[ObjectId] = None) -> bool:
        """Assign specific permissions to a user (overrides role permissions)."""
        try:
            permission_values = [p.value for p in permissions]
            
            result = self.users_collection.update_one(
                {'_id': user_id},
                {
                    '$set': {
                        'permissions': permission_values,
                        'updated_at': datetime.utcnow(),
                        'updated_by': assigned_by
                    }
                }
            )
            
            if result.modified_count > 0:
                # Log the action
                if self.audit_logger:
                    self.audit_logger.log_activity(
                        user_id=assigned_by,
                        action='user_permissions_assigned',
                        resource_type='user',
                        resource_id=str(user_id),
                        details={
                            'permissions': permission_values,
                            'permission_count': len(permissions)
                        }
                    )
                return True
            
            return False
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=assigned_by,
                    action='user_permissions_assign_failed',
                    resource_type='user',
                    resource_id=str(user_id),
                    details={'error': str(e)},
                    success=False
                )
            raise
    
    def add_user_permission(self, user_id: ObjectId, permission: Permission, added_by: Optional[ObjectId] = None) -> bool:
        """Add a single permission to a user."""
        try:
            # Get current user data
            user_data = self.users_collection.find_one({'_id': user_id})
            if not user_data:
                return False
            
            # Get current permissions
            current_permissions = user_data.get('permissions', [])
            
            # Add permission if not already present
            if permission.value not in current_permissions:
                current_permissions.append(permission.value)
                
                # Update the user with new permissions
                result = self.users_collection.update_one(
                    {'_id': user_id},
                    {
                        '$set': {
                            'permissions': current_permissions,
                            'updated_at': datetime.utcnow(),
                            'updated_by': added_by
                        }
                    }
                )
                
                if result.modified_count > 0:
                    # Log the action
                    if self.audit_logger:
                        self.audit_logger.log_activity(
                            user_id=added_by,
                            action='user_permission_added',
                            resource_type='user',
                            resource_id=str(user_id),
                            details={'permission': permission.value}
                        )
                    return True
            else:
                # Permission already exists, consider it successful
                return True
            
            return False
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=added_by,
                    action='user_permission_add_failed',
                    resource_type='user',
                    resource_id=str(user_id),
                    details={'error': str(e), 'permission': permission.value},
                    success=False
                )
            raise
    
    def remove_user_permission(self, user_id: ObjectId, permission: Permission, removed_by: Optional[ObjectId] = None) -> bool:
        """Remove a single permission from a user."""
        try:
            # Get current user data
            user_data = self.users_collection.find_one({'_id': user_id})
            if not user_data:
                return False
            
            # Get current permissions
            current_permissions = user_data.get('permissions', [])
            
            # Remove permission if present
            if permission.value in current_permissions:
                current_permissions.remove(permission.value)
                
                # Update the user with new permissions
                result = self.users_collection.update_one(
                    {'_id': user_id},
                    {
                        '$set': {
                            'permissions': current_permissions,
                            'updated_at': datetime.utcnow(),
                            'updated_by': removed_by
                        }
                    }
                )
                
                if result.modified_count > 0:
                    # Log the action
                    if self.audit_logger:
                        self.audit_logger.log_activity(
                            user_id=removed_by,
                            action='user_permission_removed',
                            resource_type='user',
                            resource_id=str(user_id),
                            details={'permission': permission.value}
                        )
                    return True
            else:
                # Permission doesn't exist, consider it successful
                return True
            
            return False
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=removed_by,
                    action='user_permission_remove_failed',
                    resource_type='user',
                    resource_id=str(user_id),
                    details={'error': str(e), 'permission': permission.value},
                    success=False
                )
            raise
    
    def check_user_permission(self, user_id: ObjectId, permission: Permission) -> bool:
        """Check if a user has a specific permission."""
        user_data = self.users_collection.find_one({'_id': user_id})
        if not user_data:
            return False
        
        user_permissions = user_data.get('permissions', [])
        return permission.value in user_permissions
    
    def get_user_permissions(self, user_id: ObjectId) -> List[Permission]:
        """Get all permissions for a user."""
        user_data = self.users_collection.find_one({'_id': user_id})
        if not user_data:
            return []
        
        permission_values = user_data.get('permissions', [])
        return [Permission(p) for p in permission_values if p in [perm.value for perm in Permission]]
    
    def check_multiple_permissions(self, user_id: ObjectId, permissions: List[Permission]) -> Dict[Permission, bool]:
        """Check multiple permissions for a user at once."""
        user_data = self.users_collection.find_one({'_id': user_id})
        if not user_data:
            return {perm: False for perm in permissions}
        
        user_permissions = set(user_data.get('permissions', []))
        return {perm: perm.value in user_permissions for perm in permissions}
    
    def get_users_with_permission(self, permission: Permission) -> List[ObjectId]:
        """Get all users who have a specific permission."""
        cursor = self.users_collection.find(
            {'permissions': permission.value},
            {'_id': 1}
        )
        return [doc['_id'] for doc in cursor]
    
    def reset_user_to_role_permissions(self, user_id: ObjectId, reset_by: Optional[ObjectId] = None) -> bool:
        """Reset user permissions to their role's default permissions."""
        try:
            # Get user's role
            user_data = self.users_collection.find_one({'_id': user_id})
            if not user_data:
                raise ValueError("User not found")
            
            user_role = UserRole(user_data['role'])
            role_permissions = self.get_role_permissions(user_role)
            permission_values = [p.value for p in role_permissions]
            
            result = self.users_collection.update_one(
                {'_id': user_id},
                {
                    '$set': {
                        'permissions': permission_values,
                        'updated_at': datetime.utcnow(),
                        'updated_by': reset_by
                    }
                }
            )
            
            if result.modified_count > 0:
                # Log the action
                if self.audit_logger:
                    self.audit_logger.log_activity(
                        user_id=reset_by,
                        action='user_permissions_reset',
                        resource_type='user',
                        resource_id=str(user_id),
                        details={
                            'role': user_role.value,
                            'permissions': permission_values
                        }
                    )
                return True
            
            return False
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=reset_by,
                    action='user_permissions_reset_failed',
                    resource_type='user',
                    resource_id=str(user_id),
                    details={'error': str(e)},
                    success=False
                )
            raise
    
    def clear_permission_cache(self) -> None:
        """Clear the permission cache."""
        self.permission_cache.clear()
    
    def get_permission_summary(self) -> Dict[str, Any]:
        """Get a summary of all permissions and role mappings."""
        summary = {
            'roles': {},
            'total_permissions': len(Permission),
            'available_permissions': [p.value for p in Permission]
        }
        
        for role in UserRole:
            permissions = self.get_role_permissions(role)
            summary['roles'][role.value] = {
                'permission_count': len(permissions),
                'permissions': [p.value for p in permissions]
            }
        
        return summary