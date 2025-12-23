"""
Setup script for initializing the dynamic admin system
"""

from admin.database.collections import setup_admin_database
from admin.services.user_manager import UserManager
from admin.services.permission_engine import PermissionEngine
from admin.services.authentication_manager import AuthenticationManager
from admin.services.vendor_approval_workflow import VendorApprovalWorkflow
from admin.services.audit_logger import AuditLogger
from admin.models.user import UserRole, Permission
from simple_mongo_mock import mock_mongo


def initialize_admin_system():
    """Initialize the admin system with database setup and default settings."""
    print("🔧 Setting up Dynamic Admin System...")
    
    # Setup database collections, indexes, and default settings
    setup_admin_database(mock_mongo.db)
    
    # Initialize user management system
    print("👥 Initializing User Management System...")
    _initialize_user_management_system(mock_mongo.db)
    
    print("✅ Dynamic Admin System setup complete!")
    print("📊 Collections created:")
    print("  - admin_settings (configuration management)")
    print("  - admin_config_cache (configuration caching)")
    print("  - content_versions (content management)")
    print("  - media_assets (media management)")
    print("  - theme_configs (theme customization)")
    print("  - theme_backups (theme backups)")
    print("  - users (user management)")
    print("  - user_sessions (session management)")
    print("  - vendor_applications (vendor workflow)")
    print("  - role_permissions (permission management)")
    print("  - activity_logs (audit logging)")
    print("  - system_alerts (system monitoring)")
    print("  - analytics_metrics (analytics data)")
    print("  - report_configs (custom reports)")
    
    return True


def _initialize_user_management_system(db):
    """Initialize the user management system with default admin user and permissions."""
    
    # Initialize services
    audit_logger = AuditLogger(db)
    user_manager = UserManager(db, audit_logger)
    permission_engine = PermissionEngine(db, audit_logger)
    
    # Create default admin user if it doesn't exist
    admin_user = user_manager.get_user_by_username('admin')
    if not admin_user:
        print("  Creating default admin user...")
        admin_data = {
            'username': 'admin',
            'email': 'admin@markethubpro.com',
            'password': 'admin123',  # Should be changed on first login
            'first_name': 'System',
            'last_name': 'Administrator',
            'role': UserRole.ADMIN.value,
            'email_verified': True
        }
        
        try:
            admin_user = user_manager.create_user(admin_data)
            print(f"  ✅ Default admin user created: {admin_user.username}")
        except Exception as e:
            print(f"  ⚠️  Failed to create admin user: {e}")
    else:
        print("  ✅ Admin user already exists")
    
    # Verify permission system is initialized
    admin_permissions = permission_engine.get_role_permissions(UserRole.ADMIN)
    print(f"  ✅ Permission system initialized with {len(admin_permissions)} admin permissions")
    
    # Log system initialization
    audit_logger.log_activity(
        user_id=None,
        action='system_initialized',
        resource_type='system',
        resource_id='user_management',
        details={
            'admin_user_exists': admin_user is not None,
            'admin_permissions_count': len(admin_permissions)
        }
    )
    
    print("  ✅ User management system initialized successfully")


if __name__ == "__main__":
    initialize_admin_system()