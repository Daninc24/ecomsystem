"""
User Management API endpoints for the dynamic admin system
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from bson import ObjectId
from flask import Blueprint, request, jsonify, session

from ..services.user_manager import UserManager
from ..services.permission_engine import PermissionEngine
from ..services.authentication_manager import AuthenticationManager
from ..services.vendor_approval_workflow import VendorApprovalWorkflow
from ..services.audit_logger import AuditLogger
from ..models.user import User, UserRole, UserStatus, Permission
from .base_api import BaseAPI


class UserAPI(BaseAPI):
    """API endpoints for user and permission management."""
    
    def __init__(self, db):
        super().__init__(db)
        self.audit_logger = AuditLogger(db)
        self.user_manager = UserManager(db, self.audit_logger)
        self.permission_engine = PermissionEngine(db, self.audit_logger)
        self.auth_manager = AuthenticationManager(db, self.user_manager, self.audit_logger)
        self.vendor_workflow = VendorApprovalWorkflow(db, self.user_manager, self.audit_logger)
    
    def register_routes(self, bp: Blueprint) -> None:
        """Register all user management routes."""
        
        # User CRUD operations
        bp.route('/users', methods=['GET'])(self.list_users)
        bp.route('/users', methods=['POST'])(self.create_user)
        bp.route('/users/<user_id>', methods=['GET'])(self.get_user)
        bp.route('/users/<user_id>', methods=['PUT'])(self.update_user)
        bp.route('/users/<user_id>', methods=['DELETE'])(self.delete_user)
        
        # User status management
        bp.route('/users/<user_id>/suspend', methods=['POST'])(self.suspend_user)
        bp.route('/users/<user_id>/activate', methods=['POST'])(self.activate_user)
        
        # Permission management
        bp.route('/users/<user_id>/permissions', methods=['GET'])(self.get_user_permissions)
        bp.route('/users/<user_id>/permissions', methods=['PUT'])(self.assign_user_permissions)
        bp.route('/users/<user_id>/permissions/<permission>', methods=['POST'])(self.add_user_permission)
        bp.route('/users/<user_id>/permissions/<permission>', methods=['DELETE'])(self.remove_user_permission)
        bp.route('/users/<user_id>/permissions/reset', methods=['POST'])(self.reset_user_permissions)
        
        # Role management
        bp.route('/roles', methods=['GET'])(self.list_roles)
        bp.route('/roles/<role>/permissions', methods=['GET'])(self.get_role_permissions)
        bp.route('/roles/<role>/permissions', methods=['PUT'])(self.update_role_permissions)
        
        # Authentication
        bp.route('/auth/login', methods=['POST'])(self.login)
        bp.route('/auth/logout', methods=['POST'])(self.logout)
        bp.route('/auth/validate', methods=['GET'])(self.validate_session)
        bp.route('/auth/sessions/<user_id>', methods=['GET'])(self.get_user_sessions)
        bp.route('/auth/sessions/<user_id>/deactivate', methods=['POST'])(self.deactivate_user_sessions)
        
        # Vendor applications
        bp.route('/vendor-applications', methods=['GET'])(self.list_vendor_applications)
        bp.route('/vendor-applications', methods=['POST'])(self.submit_vendor_application)
        bp.route('/vendor-applications/<app_id>', methods=['GET'])(self.get_vendor_application)
        bp.route('/vendor-applications/<app_id>/review', methods=['POST'])(self.set_application_under_review)
        bp.route('/vendor-applications/<app_id>/approve', methods=['POST'])(self.approve_vendor_application)
        bp.route('/vendor-applications/<app_id>/reject', methods=['POST'])(self.reject_vendor_application)
        
        # Audit and monitoring
        bp.route('/audit/activities', methods=['GET'])(self.get_activities)
        bp.route('/audit/activities/user/<user_id>', methods=['GET'])(self.get_user_activities)
        bp.route('/audit/activities/security', methods=['GET'])(self.get_security_events)
        bp.route('/audit/statistics', methods=['GET'])(self.get_audit_statistics)
        
        # System alerts
        bp.route('/alerts', methods=['GET'])(self.get_alerts)
        bp.route('/alerts/<alert_id>/resolve', methods=['POST'])(self.resolve_alert)
    
    # User CRUD operations
    def list_users(self):
        """List users with optional filtering."""
        try:
            # Get query parameters
            limit = int(request.args.get('limit', 50))
            skip = int(request.args.get('skip', 0))
            role = request.args.get('role')
            status = request.args.get('status')
            search = request.args.get('search')
            
            # Build filters
            filters = {}
            if role:
                filters['role'] = role
            if status:
                filters['status'] = status
            if search:
                filters['$or'] = [
                    {'username': {'$regex': search, '$options': 'i'}},
                    {'email': {'$regex': search, '$options': 'i'}},
                    {'first_name': {'$regex': search, '$options': 'i'}},
                    {'last_name': {'$regex': search, '$options': 'i'}}
                ]
            
            # Get users
            users = self.user_manager.list_users(filters, limit, skip)
            total_count = self.user_manager.count_users(filters)
            
            # Convert to dict format
            users_data = []
            for user in users:
                user_dict = user.to_dict()
                user_dict['id'] = str(user_dict.pop('_id', user.id))
                # Remove sensitive data
                user_dict.pop('password_hash', None)
                users_data.append(user_dict)
            
            return jsonify({
                'success': True,
                'data': {
                    'users': users_data,
                    'pagination': {
                        'total': total_count,
                        'limit': limit,
                        'skip': skip,
                        'has_more': skip + len(users) < total_count
                    }
                }
            })
            
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def create_user(self):
        """Create a new user."""
        try:
            data = request.get_json()
            if not data:
                return self._error_response("No data provided", 400)
            
            # Get current user ID for audit logging
            current_user_id = self._get_current_user_id()
            
            # Create user
            user = self.user_manager.create_user(data, current_user_id)
            
            # Convert to response format
            user_dict = user.to_dict()
            user_dict['id'] = str(user_dict.pop('_id', user.id))
            user_dict.pop('password_hash', None)  # Remove sensitive data
            
            return jsonify({
                'success': True,
                'data': {'user': user_dict},
                'message': 'User created successfully'
            }), 201
            
        except ValueError as e:
            return self._error_response(str(e), 400)
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def get_user(self, user_id: str):
        """Get user by ID."""
        try:
            user = self.user_manager.get_user(ObjectId(user_id))
            if not user:
                return self._error_response("User not found", 404)
            
            # Convert to response format
            user_dict = user.to_dict()
            user_dict['id'] = str(user_dict.pop('_id', user.id))
            user_dict.pop('password_hash', None)  # Remove sensitive data
            
            return jsonify({
                'success': True,
                'data': {'user': user_dict}
            })
            
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def update_user(self, user_id: str):
        """Update user."""
        try:
            data = request.get_json()
            if not data:
                return self._error_response("No data provided", 400)
            
            current_user_id = self._get_current_user_id()
            
            # Update user
            success = self.user_manager.update_user(ObjectId(user_id), data, current_user_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'User updated successfully'
                })
            else:
                return self._error_response("User not found or no changes made", 404)
                
        except ValueError as e:
            return self._error_response(str(e), 400)
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def delete_user(self, user_id: str):
        """Delete user."""
        try:
            current_user_id = self._get_current_user_id()
            
            # Delete user
            success = self.user_manager.delete_user(ObjectId(user_id), current_user_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'User deleted successfully'
                })
            else:
                return self._error_response("User not found", 404)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    # User status management
    def suspend_user(self, user_id: str):
        """Suspend user account."""
        try:
            data = request.get_json() or {}
            reason = data.get('reason', 'No reason provided')
            duration_hours = data.get('duration_hours')
            
            current_user_id = self._get_current_user_id()
            
            success = self.user_manager.suspend_user(
                ObjectId(user_id), reason, current_user_id, duration_hours
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'User suspended successfully'
                })
            else:
                return self._error_response("User not found", 404)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def activate_user(self, user_id: str):
        """Activate user account."""
        try:
            current_user_id = self._get_current_user_id()
            
            success = self.user_manager.activate_user(ObjectId(user_id), current_user_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'User activated successfully'
                })
            else:
                return self._error_response("User not found", 404)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    # Permission management
    def get_user_permissions(self, user_id: str):
        """Get user permissions."""
        try:
            permissions = self.permission_engine.get_user_permissions(ObjectId(user_id))
            
            return jsonify({
                'success': True,
                'data': {
                    'permissions': [p.value for p in permissions]
                }
            })
            
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def assign_user_permissions(self, user_id: str):
        """Assign permissions to user."""
        try:
            data = request.get_json()
            if not data or 'permissions' not in data:
                return self._error_response("Permissions list required", 400)
            
            permissions = [Permission(p) for p in data['permissions']]
            current_user_id = self._get_current_user_id()
            
            success = self.permission_engine.assign_user_permissions(
                ObjectId(user_id), permissions, current_user_id
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Permissions assigned successfully'
                })
            else:
                return self._error_response("User not found", 404)
                
        except ValueError as e:
            return self._error_response(str(e), 400)
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def add_user_permission(self, user_id: str, permission: str):
        """Add single permission to user."""
        try:
            perm = Permission(permission)
            current_user_id = self._get_current_user_id()
            
            success = self.permission_engine.add_user_permission(
                ObjectId(user_id), perm, current_user_id
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Permission {permission} added successfully'
                })
            else:
                return self._error_response("User not found", 404)
                
        except ValueError as e:
            return self._error_response(f"Invalid permission: {permission}", 400)
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def remove_user_permission(self, user_id: str, permission: str):
        """Remove single permission from user."""
        try:
            perm = Permission(permission)
            current_user_id = self._get_current_user_id()
            
            success = self.permission_engine.remove_user_permission(
                ObjectId(user_id), perm, current_user_id
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Permission {permission} removed successfully'
                })
            else:
                return self._error_response("User not found", 404)
                
        except ValueError as e:
            return self._error_response(f"Invalid permission: {permission}", 400)
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def reset_user_permissions(self, user_id: str):
        """Reset user permissions to role defaults."""
        try:
            current_user_id = self._get_current_user_id()
            
            success = self.permission_engine.reset_user_to_role_permissions(
                ObjectId(user_id), current_user_id
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'User permissions reset to role defaults'
                })
            else:
                return self._error_response("User not found", 404)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    # Role management
    def list_roles(self):
        """List all available roles."""
        try:
            roles_data = []
            for role in UserRole:
                permissions = self.permission_engine.get_role_permissions(role)
                roles_data.append({
                    'role': role.value,
                    'permissions': [p.value for p in permissions],
                    'permission_count': len(permissions)
                })
            
            return jsonify({
                'success': True,
                'data': {'roles': roles_data}
            })
            
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def get_role_permissions(self, role: str):
        """Get permissions for a specific role."""
        try:
            user_role = UserRole(role)
            permissions = self.permission_engine.get_role_permissions(user_role)
            
            return jsonify({
                'success': True,
                'data': {
                    'role': role,
                    'permissions': [p.value for p in permissions]
                }
            })
            
        except ValueError as e:
            return self._error_response(f"Invalid role: {role}", 400)
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def update_role_permissions(self, role: str):
        """Update permissions for a role."""
        try:
            data = request.get_json()
            if not data or 'permissions' not in data:
                return self._error_response("Permissions list required", 400)
            
            user_role = UserRole(role)
            permissions = [Permission(p) for p in data['permissions']]
            current_user_id = self._get_current_user_id()
            
            success = self.permission_engine.update_role_permissions(
                user_role, permissions, current_user_id
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Permissions updated for role {role}'
                })
            else:
                return self._error_response("Failed to update role permissions", 500)
                
        except ValueError as e:
            return self._error_response(str(e), 400)
        except Exception as e:
            return self._error_response(str(e), 500)
    
    # Authentication
    def login(self):
        """Authenticate user and create session."""
        try:
            data = request.get_json()
            if not data:
                return self._error_response("No data provided", 400)
            
            username_or_email = data.get('username') or data.get('email')
            password = data.get('password')
            
            if not username_or_email or not password:
                return self._error_response("Username/email and password required", 400)
            
            # Get client info
            ip_address = request.remote_addr or ''
            user_agent = request.headers.get('User-Agent', '')
            
            # Authenticate
            user, session, message = self.auth_manager.authenticate_user(
                username_or_email, password, ip_address, user_agent
            )
            
            if user and session:
                return jsonify({
                    'success': True,
                    'data': {
                        'user': {
                            'id': str(user.id),
                            'username': user.username,
                            'email': user.email,
                            'role': user.role.value,
                            'permissions': [p.value for p in user.permissions]
                        },
                        'session': {
                            'token': session.session_token,
                            'expires_at': session.expires_at.isoformat()
                        }
                    },
                    'message': message
                })
            else:
                return self._error_response(message, 401)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def logout(self):
        """Logout user by deactivating session."""
        try:
            data = request.get_json() or {}
            session_token = data.get('session_token') or request.headers.get('Authorization', '').replace('Bearer ', '')
            
            if not session_token:
                return self._error_response("Session token required", 400)
            
            success = self.auth_manager.logout_user(session_token)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Logged out successfully'
                })
            else:
                return self._error_response("Invalid session token", 400)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def validate_session(self):
        """Validate session token."""
        try:
            session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
            
            if not session_token:
                return self._error_response("Session token required", 400)
            
            user, session = self.auth_manager.validate_session(session_token)
            
            if user and session:
                return jsonify({
                    'success': True,
                    'data': {
                        'user': {
                            'id': str(user.id),
                            'username': user.username,
                            'email': user.email,
                            'role': user.role.value,
                            'permissions': [p.value for p in user.permissions]
                        },
                        'session': {
                            'expires_at': session.expires_at.isoformat(),
                            'last_activity': session.last_activity.isoformat()
                        }
                    }
                })
            else:
                return self._error_response("Invalid or expired session", 401)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def get_user_sessions(self, user_id: str):
        """Get active sessions for a user."""
        try:
            sessions = self.auth_manager.get_user_sessions(ObjectId(user_id), active_only=True)
            
            sessions_data = []
            for session in sessions:
                sessions_data.append({
                    'id': str(session.id),
                    'ip_address': session.ip_address,
                    'user_agent': session.user_agent,
                    'created_at': session.created_at.isoformat(),
                    'last_activity': session.last_activity.isoformat(),
                    'expires_at': session.expires_at.isoformat()
                })
            
            return jsonify({
                'success': True,
                'data': {'sessions': sessions_data}
            })
            
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def deactivate_user_sessions(self, user_id: str):
        """Deactivate all sessions for a user."""
        try:
            data = request.get_json() or {}
            except_session_id = data.get('except_session_id')
            
            except_id = ObjectId(except_session_id) if except_session_id else None
            count = self.auth_manager.deactivate_all_user_sessions(ObjectId(user_id), except_id)
            
            return jsonify({
                'success': True,
                'data': {'deactivated_count': count},
                'message': f'Deactivated {count} sessions'
            })
            
        except Exception as e:
            return self._error_response(str(e), 500)
    
    # Vendor applications
    def list_vendor_applications(self):
        """List vendor applications."""
        try:
            status = request.args.get('status')
            limit = int(request.args.get('limit', 50))
            skip = int(request.args.get('skip', 0))
            
            applications = self.vendor_workflow.list_applications(status, limit, skip)
            total_count = self.vendor_workflow.count_applications(status)
            
            apps_data = []
            for app in applications:
                app_dict = app.to_dict()
                app_dict['id'] = str(app_dict.pop('_id', app.id))
                apps_data.append(app_dict)
            
            return jsonify({
                'success': True,
                'data': {
                    'applications': apps_data,
                    'pagination': {
                        'total': total_count,
                        'limit': limit,
                        'skip': skip,
                        'has_more': skip + len(applications) < total_count
                    }
                }
            })
            
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def submit_vendor_application(self):
        """Submit a new vendor application."""
        try:
            data = request.get_json()
            if not data:
                return self._error_response("No data provided", 400)
            
            user_id = data.get('user_id')
            if not user_id:
                return self._error_response("User ID required", 400)
            
            application = self.vendor_workflow.submit_application(ObjectId(user_id), data)
            
            app_dict = application.to_dict()
            app_dict['id'] = str(app_dict.pop('_id', application.id))
            
            return jsonify({
                'success': True,
                'data': {'application': app_dict},
                'message': 'Vendor application submitted successfully'
            }), 201
            
        except ValueError as e:
            return self._error_response(str(e), 400)
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def get_vendor_application(self, app_id: str):
        """Get vendor application by ID."""
        try:
            application = self.vendor_workflow.get_application(ObjectId(app_id))
            if not application:
                return self._error_response("Application not found", 404)
            
            app_dict = application.to_dict()
            app_dict['id'] = str(app_dict.pop('_id', application.id))
            
            return jsonify({
                'success': True,
                'data': {'application': app_dict}
            })
            
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def set_application_under_review(self, app_id: str):
        """Set application status to under review."""
        try:
            current_user_id = self._get_current_user_id()
            
            success = self.vendor_workflow.set_under_review(ObjectId(app_id), current_user_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Application set under review'
                })
            else:
                return self._error_response("Application not found or invalid status", 400)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def approve_vendor_application(self, app_id: str):
        """Approve vendor application."""
        try:
            data = request.get_json() or {}
            notes = data.get('notes', '')
            
            current_user_id = self._get_current_user_id()
            
            success = self.vendor_workflow.approve_application(ObjectId(app_id), current_user_id, notes)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Vendor application approved successfully'
                })
            else:
                return self._error_response("Application not found or invalid status", 400)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def reject_vendor_application(self, app_id: str):
        """Reject vendor application."""
        try:
            data = request.get_json()
            if not data or 'reason' not in data:
                return self._error_response("Rejection reason required", 400)
            
            reason = data['reason']
            notes = data.get('notes', '')
            
            current_user_id = self._get_current_user_id()
            
            success = self.vendor_workflow.reject_application(ObjectId(app_id), current_user_id, reason, notes)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Vendor application rejected'
                })
            else:
                return self._error_response("Application not found or invalid status", 400)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    # Audit and monitoring
    def get_activities(self):
        """Get activity logs."""
        try:
            limit = int(request.args.get('limit', 100))
            skip = int(request.args.get('skip', 0))
            action = request.args.get('action')
            resource_type = request.args.get('resource_type')
            success_only = request.args.get('success_only', 'false').lower() == 'true'
            
            filters = {}
            if action:
                filters['action'] = action
            if resource_type:
                filters['resource_type'] = resource_type
            if success_only:
                filters['success'] = True
            
            activities = self.audit_logger.search_activities(filters, limit, skip)
            
            activities_data = []
            for activity in activities:
                activity_dict = activity.to_dict()
                activity_dict['id'] = str(activity_dict.pop('_id', activity.id))
                activities_data.append(activity_dict)
            
            return jsonify({
                'success': True,
                'data': {'activities': activities_data}
            })
            
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def get_user_activities(self, user_id: str):
        """Get activities for a specific user."""
        try:
            limit = int(request.args.get('limit', 100))
            skip = int(request.args.get('skip', 0))
            
            activities = self.audit_logger.get_user_activity(ObjectId(user_id), limit, skip)
            
            activities_data = []
            for activity in activities:
                activity_dict = activity.to_dict()
                activity_dict['id'] = str(activity_dict.pop('_id', activity.id))
                activities_data.append(activity_dict)
            
            return jsonify({
                'success': True,
                'data': {'activities': activities_data}
            })
            
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def get_security_events(self):
        """Get security-related events."""
        try:
            hours_back = int(request.args.get('hours_back', 24))
            limit = int(request.args.get('limit', 100))
            skip = int(request.args.get('skip', 0))
            
            events = self.audit_logger.get_security_events(limit, skip, hours_back)
            
            events_data = []
            for event in events:
                event_dict = event.to_dict()
                event_dict['id'] = str(event_dict.pop('_id', event.id))
                events_data.append(event_dict)
            
            return jsonify({
                'success': True,
                'data': {'events': events_data}
            })
            
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def get_audit_statistics(self):
        """Get audit statistics."""
        try:
            hours_back = int(request.args.get('hours_back', 24))
            
            stats = self.audit_logger.get_activity_statistics(hours_back)
            
            return jsonify({
                'success': True,
                'data': {'statistics': stats}
            })
            
        except Exception as e:
            return self._error_response(str(e), 500)
    
    # System alerts
    def get_alerts(self):
        """Get system alerts."""
        try:
            limit = int(request.args.get('limit', 50))
            unresolved_only = request.args.get('unresolved_only', 'true').lower() == 'true'
            
            if unresolved_only:
                alerts = self.audit_logger.get_unresolved_alerts(limit)
            else:
                # Would need to implement get_all_alerts method
                alerts = self.audit_logger.get_unresolved_alerts(limit)
            
            alerts_data = []
            for alert in alerts:
                alert_dict = alert.to_dict()
                alert_dict['id'] = str(alert_dict.pop('_id', alert.id))
                alerts_data.append(alert_dict)
            
            return jsonify({
                'success': True,
                'data': {'alerts': alerts_data}
            })
            
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def resolve_alert(self, alert_id: str):
        """Resolve a system alert."""
        try:
            data = request.get_json() or {}
            notes = data.get('notes', '')
            
            current_user_id = self._get_current_user_id()
            
            success = self.audit_logger.resolve_alert(ObjectId(alert_id), current_user_id, notes)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Alert resolved successfully'
                })
            else:
                return self._error_response("Alert not found", 404)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def _get_current_user_id(self) -> Optional[ObjectId]:
        """Get current user ID from session or request."""
        # This would typically come from session or JWT token
        # For now, return None (system user)
        return None


# Create blueprint and register routes
user_bp = Blueprint('user_api', __name__, url_prefix='/api/users')

def create_user_api(db):
    """Create and configure the user API."""
    api = UserAPI(db)
    api.register_routes(user_bp)
    return user_bp