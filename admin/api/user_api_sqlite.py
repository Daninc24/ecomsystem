"""
User Management API endpoints for SQLite - Dynamic Admin System
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models_sqlite import db
import functools

user_bp = Blueprint('user_api', __name__, url_prefix='/users')


def admin_required(f):
    """Decorator to require admin role."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_role('admin'):
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403
        return f(*args, **kwargs)
    return decorated_function


@user_bp.route('/', methods=['GET'])
@login_required
@admin_required
def list_users():
    """List all users with pagination and filtering."""
    try:
        from models_sqlite import User, Role
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        role = request.args.get('role')
        status = request.args.get('status')
        search = request.args.get('search')
        
        # Build query
        query = User.query
        
        if role:
            query = query.filter(User.roles.any(Role.name == role))
        
        if status == 'active':
            query = query.filter(User.is_active == True)
        elif status == 'inactive':
            query = query.filter(User.is_active == False)
        
        if search:
            query = query.filter(
                db.or_(
                    User.username.contains(search),
                    User.email.contains(search),
                    User.first_name.contains(search),
                    User.last_name.contains(search)
                )
            )
        
        # Paginate
        users = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': {
                'users': [user.to_dict() for user in users.items],
                'pagination': {
                    'current_page': users.page,
                    'total_pages': users.pages,
                    'total_items': users.total,
                    'has_next': users.has_next,
                    'has_prev': users.has_prev
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def get_user(user_id):
    """Get a specific user by ID."""
    try:
        from models_sqlite import User
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/', methods=['POST'])
@login_required
@admin_required
def create_user():
    """Create a new user."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        errors = {}
        
        for field in required_fields:
            if not data.get(field):
                errors[field] = f'{field.replace("_", " ").title()} is required'
        
        # Check if username or email already exists
        from models_sqlite import User, Role
        
        if data.get('username'):
            existing_user = User.query.filter_by(username=data['username']).first()
            if existing_user:
                errors['username'] = 'Username already exists'
        
        if data.get('email'):
            existing_email = User.query.filter_by(email=data['email']).first()
            if existing_email:
                errors['email'] = 'Email already exists'
        
        # Validate password confirmation
        if data.get('password') and data.get('confirm_password'):
            if data['password'] != data['confirm_password']:
                errors['confirm_password'] = 'Passwords do not match'
        
        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        # Create new user
        new_user = User(
            username=data['username'],
            email=data['email'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            phone=data.get('phone', ''),
            is_active=data.get('is_active', True)
        )
        
        # Set password
        new_user.set_password(data['password'])
        
        # Add roles if specified
        if data.get('roles'):
            roles = Role.query.filter(Role.name.in_(data['roles'])).all()
            new_user.roles = roles
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    """Update user information."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        from models_sqlite import User, Role
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        errors = {}
        
        # Check if email is being changed and if it already exists
        if data.get('email') and data['email'] != user.email:
            existing_email = User.query.filter_by(email=data['email']).first()
            if existing_email:
                errors['email'] = 'Email already exists'
        
        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        # Update user fields
        if 'email' in data:
            user.email = data['email']
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'is_active' in data:
            user.is_active = data['is_active']
        
        # Update roles if specified
        if 'roles' in data:
            roles = Role.query.filter(Role.name.in_(data['roles'])).all()
            user.roles = roles
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user."""
    try:
        from models_sqlite import User
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Prevent deleting yourself
        if user.id == current_user.id:
            return jsonify({
                'success': False,
                'error': 'Cannot delete your own account'
            }), 400
        
        # Store username for response message
        username = user.username
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'User {username} deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/<int:user_id>/activity', methods=['GET'])
@login_required
@admin_required
def get_user_activity(user_id):
    """Get user activity history."""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        user_manager = current_app.user_manager
        activity = user_manager.get_user_activity(user_id, limit)
        
        return jsonify({
            'success': True,
            'data': activity
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/statistics', methods=['GET'])
@login_required
@admin_required
def get_user_statistics():
    """Get user statistics for dashboard."""
    try:
        user_manager = current_app.user_manager
        stats = user_manager.get_user_statistics()
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/<int:user_id>/suspend', methods=['POST'])
@login_required
@admin_required
def suspend_user(user_id):
    """Suspend a user account (same as deactivate but with different terminology)."""
    try:
        from models_sqlite import User
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Prevent suspending yourself
        if user.id == current_user.id:
            return jsonify({
                'success': False,
                'error': 'Cannot suspend your own account'
            }), 400
        
        if not user.is_active:
            return jsonify({
                'success': False,
                'error': 'User is already suspended/inactive'
            }), 400
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'user_id': user_id,
                'is_active': False,
                'message': 'User suspended successfully'
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/<int:user_id>/activate', methods=['POST'])
@login_required
@admin_required
def activate_user(user_id):
    """Activate a user account."""
    try:
        from models_sqlite import User
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        if user.is_active:
            return jsonify({
                'success': False,
                'error': 'User is already active'
            }), 400
        
        user.is_active = True
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'user_id': user_id,
                'is_active': True,
                'message': 'User activated successfully'
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/<int:user_id>/deactivate', methods=['POST'])
@login_required
@admin_required
def deactivate_user(user_id):
    """Deactivate a user account."""
    try:
        from models_sqlite import User
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Prevent deactivating yourself
        if user.id == current_user.id:
            return jsonify({
                'success': False,
                'error': 'Cannot deactivate your own account'
            }), 400
        
        if not user.is_active:
            return jsonify({
                'success': False,
                'error': 'User is already inactive'
            }), 400
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'user_id': user_id,
                'is_active': False,
                'message': 'User deactivated successfully'
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    """Reset a user's password."""
    try:
        from models_sqlite import User
        import secrets
        import string
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Generate a temporary password
        alphabet = string.ascii_letters + string.digits
        temp_password = ''.join(secrets.choice(alphabet) for i in range(12))
        
        user.set_password(temp_password)
        user.password_reset_required = True
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'user_id': user_id,
                'temporary_password': temp_password,
                'message': 'Password reset successfully. User must change password on next login.'
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/<int:user_id>/roles', methods=['GET'])
@login_required
@admin_required
def get_user_roles(user_id):
    """Get user roles."""
    try:
        from models_sqlite import User
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        roles = [{'id': role.id, 'name': role.name, 'description': role.description} 
                for role in user.roles]
        
        return jsonify({
            'success': True,
            'data': {
                'user_id': user_id,
                'roles': roles
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/<int:user_id>/roles', methods=['POST'])
@login_required
@admin_required
def update_user_roles(user_id):
    """Update user roles."""
    try:
        from models_sqlite import User, Role
        
        data = request.get_json()
        if not data or 'role_ids' not in data:
            return jsonify({
                'success': False,
                'error': 'Role IDs are required'
            }), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        role_ids = data['role_ids']
        roles = Role.query.filter(Role.id.in_(role_ids)).all()
        
        if len(roles) != len(role_ids):
            return jsonify({
                'success': False,
                'error': 'One or more roles not found'
            }), 400
        
        user.roles = roles
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'user_id': user_id,
                'roles': [{'id': role.id, 'name': role.name} for role in roles],
                'message': 'User roles updated successfully'
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/validate', methods=['POST'])
@login_required
@admin_required
def validate_user_data():
    """Validate user data before creating or updating."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        user_id = data.get('user_id')  # For updates
        user_data = data.get('user_data', {})
        
        user_manager = current_app.user_manager
        validation = user_manager.validate_user_data(user_data, user_id)
        
        return jsonify({
            'success': True,
            'data': validation
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500