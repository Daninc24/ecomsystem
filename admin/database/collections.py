"""
MongoDB collection setup and configuration for the admin system
"""

from datetime import datetime
from typing import Dict, Any
from pymongo.errors import CollectionInvalid


def get_collection(db, collection_name: str):
    """Get a MongoDB collection by name."""
    return getattr(db, collection_name)


def setup_admin_collections(db) -> None:
    """Set up all MongoDB collections required for the admin system."""
    
    # For mock database, just access the collections to create them
    collections = [
        'admin_settings',
        'admin_config_cache',
        'content_versions',
        'media_assets',
        'theme_configs',
        'theme_backups',
        'activity_logs',
        'system_alerts',
        'analytics_metrics',
        'report_configs',
        'users',
        'user_sessions',
        'vendor_applications',
        'role_permissions',
        'product_categories',
        'bulk_operations',
        'data_imports',
        'automation_rules',
        'product_attributes',
        'inventory_transactions'
    ]
    
    for collection_name in collections:
        # Access the collection to ensure it exists in mock
        getattr(db, collection_name)


def create_admin_indexes(db) -> None:
    """Create indexes for optimal performance of admin collections."""
    
    # Admin Settings Indexes
    db.admin_settings.create_index('key', unique=True)
    db.admin_settings.create_index('category')
    db.admin_settings.create_index('is_sensitive')
    db.admin_settings.create_index('updated_at')
    
    # Configuration Cache Indexes
    db.admin_config_cache.create_index('key', unique=True)
    db.admin_config_cache.create_index('expires_at')
    db.admin_config_cache.create_index('last_accessed')
    
    # Content Versions Indexes
    db.content_versions.create_index('element_id')
    db.content_versions.create_index([('element_id', 1), ('version_number', -1)])
    db.content_versions.create_index('is_published')
    db.content_versions.create_index('created_at')
    db.content_versions.create_index('created_by')
    
    # Media Assets Indexes
    db.media_assets.create_index('filename')
    db.media_assets.create_index('file_type')
    db.media_assets.create_index('mime_type')
    db.media_assets.create_index('tags')
    db.media_assets.create_index('usage_count')
    db.media_assets.create_index('created_at')
    
    # Theme Configurations Indexes
    db.theme_configs.create_index('name', unique=True)
    db.theme_configs.create_index('is_active')
    db.theme_configs.create_index('is_default')
    db.theme_configs.create_index('updated_at')
    
    # Theme Backups Indexes
    db.theme_backups.create_index('theme_id')
    db.theme_backups.create_index('backup_type')
    db.theme_backups.create_index('created_at')
    
    # Activity Logs Indexes
    db.activity_logs.create_index('user_id')
    db.activity_logs.create_index('action')
    db.activity_logs.create_index('resource_type')
    db.activity_logs.create_index('resource_id')
    db.activity_logs.create_index('created_at')
    db.activity_logs.create_index('severity')
    db.activity_logs.create_index('success')
    db.activity_logs.create_index('ip_address')
    
    # System Alerts Indexes
    db.system_alerts.create_index('alert_type')
    db.system_alerts.create_index('severity')
    db.system_alerts.create_index('is_resolved')
    db.system_alerts.create_index('created_at')
    db.system_alerts.create_index('resolved_at')
    db.system_alerts.create_index('source')
    
    # Analytics Metrics Indexes
    db.analytics_metrics.create_index('metric_name')
    db.analytics_metrics.create_index('timestamp')
    db.analytics_metrics.create_index('aggregation_period')
    db.analytics_metrics.create_index([('metric_name', 1), ('timestamp', -1)])
    db.analytics_metrics.create_index('source')
    db.analytics_metrics.create_index('tags')
    
    # Report Configurations Indexes
    db.report_configs.create_index('name')
    db.report_configs.create_index('report_type')
    db.report_configs.create_index('is_active')
    db.report_configs.create_index('created_by')
    db.report_configs.create_index('last_generated')
    
    # Users Indexes
    db.users.create_index('username', unique=True)
    db.users.create_index('email', unique=True)
    db.users.create_index('role')
    db.users.create_index('status')
    db.users.create_index('created_at')
    db.users.create_index('last_login')
    db.users.create_index('email_verified')
    
    # User Sessions Indexes
    db.user_sessions.create_index('user_id')
    db.user_sessions.create_index('session_token', unique=True)
    db.user_sessions.create_index('expires_at')
    db.user_sessions.create_index('is_active')
    db.user_sessions.create_index('last_activity')
    db.user_sessions.create_index('ip_address')
    
    # Vendor Applications Indexes
    db.vendor_applications.create_index('user_id')
    db.vendor_applications.create_index('status')
    db.vendor_applications.create_index('business_name')
    db.vendor_applications.create_index('created_at')
    db.vendor_applications.create_index('reviewed_by')
    db.vendor_applications.create_index('reviewed_at')
    
    # Role Permissions Indexes
    db.role_permissions.create_index('role', unique=True)
    db.role_permissions.create_index('is_default')
    db.role_permissions.create_index('updated_at')
    
    # Product Categories Indexes
    db.product_categories.create_index('name')
    db.product_categories.create_index('slug', unique=True)
    db.product_categories.create_index('parent_id')
    db.product_categories.create_index('level')
    db.product_categories.create_index('sort_order')
    db.product_categories.create_index('is_active')
    db.product_categories.create_index('path')
    
    # Bulk Operations Indexes
    db.bulk_operations.create_index('operation_type')
    db.bulk_operations.create_index('status')
    db.bulk_operations.create_index('created_by')
    db.bulk_operations.create_index('created_at')
    db.bulk_operations.create_index('started_at')
    db.bulk_operations.create_index('completed_at')
    
    # Data Imports Indexes
    db.data_imports.create_index('filename')
    db.data_imports.create_index('file_type')
    db.data_imports.create_index('status')
    db.data_imports.create_index('created_by')
    db.data_imports.create_index('created_at')
    db.data_imports.create_index('started_at')
    db.data_imports.create_index('completed_at')
    
    # Automation Rules Indexes
    db.automation_rules.create_index('name')
    db.automation_rules.create_index('is_active')
    db.automation_rules.create_index('priority')
    db.automation_rules.create_index('created_by')
    db.automation_rules.create_index('last_executed')
    db.automation_rules.create_index('created_at')
    
    # Product Attributes Indexes
    db.product_attributes.create_index('name')
    db.product_attributes.create_index('slug', unique=True)
    db.product_attributes.create_index('type')
    db.product_attributes.create_index('is_required')
    db.product_attributes.create_index('is_filterable')
    db.product_attributes.create_index('is_searchable')
    db.product_attributes.create_index('sort_order')
    db.product_attributes.create_index('categories')
    
    # Inventory Transactions Indexes
    db.inventory_transactions.create_index('product_id')
    db.inventory_transactions.create_index('variant_id')
    db.inventory_transactions.create_index('transaction_type')
    db.inventory_transactions.create_index('created_at')
    db.inventory_transactions.create_index('created_by')
    db.inventory_transactions.create_index('reference_id')


def initialize_default_settings(db) -> None:
    """Initialize default admin settings if they don't exist."""
    
    default_settings = [
        {
            'key': 'site_name',
            'value': 'MarketHub Pro',
            'category': 'general',
            'description': 'The name of the website',
            'validation_rules': {
                'type': 'string',
                'min_length': 1,
                'max_length': 100
            },
            'is_sensitive': False,
            'requires_restart': False
        },
        {
            'key': 'site_description',
            'value': 'Your premier e-commerce marketplace',
            'category': 'general',
            'description': 'Site description for SEO and branding',
            'validation_rules': {
                'type': 'string',
                'min_length': 1,
                'max_length': 500
            },
            'is_sensitive': False,
            'requires_restart': False
        },
        {
            'key': 'contact_email',
            'value': 'contact@markethubpro.com',
            'category': 'general',
            'description': 'Primary contact email address',
            'validation_rules': {
                'type': 'string',
                'min_length': 5,
                'max_length': 100
            },
            'is_sensitive': False,
            'requires_restart': False
        },
        {
            'key': 'default_currency',
            'value': 'USD',
            'category': 'commerce',
            'description': 'Default currency for the platform',
            'validation_rules': {
                'type': 'string',
                'allowed_values': ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY']
            },
            'is_sensitive': False,
            'requires_restart': False
        },
        {
            'key': 'products_per_page',
            'value': 24,
            'category': 'display',
            'description': 'Number of products to display per page',
            'validation_rules': {
                'type': 'number',
                'min': 6,
                'max': 100
            },
            'is_sensitive': False,
            'requires_restart': False
        },
        {
            'key': 'enable_user_registration',
            'value': True,
            'category': 'security',
            'description': 'Allow new users to register accounts',
            'validation_rules': {
                'type': 'boolean'
            },
            'is_sensitive': False,
            'requires_restart': False
        },
        {
            'key': 'maintenance_mode',
            'value': False,
            'category': 'system',
            'description': 'Enable maintenance mode to disable public access',
            'validation_rules': {
                'type': 'boolean'
            },
            'is_sensitive': False,
            'requires_restart': False
        }
    ]
    
    now = datetime.utcnow()
    
    for setting in default_settings:
        # Check if setting already exists
        if not db.admin_settings.find_one({'key': setting['key']}):
            setting.update({
                'created_at': now,
                'updated_at': now,
                'created_by': None,
                'updated_by': None
            })
            db.admin_settings.insert_one(setting)


def setup_admin_database(db) -> None:
    """Complete setup of the admin database including collections, indexes, and default data."""
    setup_admin_collections(db)
    create_admin_indexes(db)
    initialize_default_settings(db)