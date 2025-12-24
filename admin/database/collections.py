"""
SQLite database setup and configuration for the admin system
"""

from datetime import datetime, timezone
from typing import Dict, Any
from flask import current_app
from models_sqlite import db, AdminSetting, ActivityLog, User


def get_admin_db():
    """Get admin database connection (SQLite)."""
    return db


def get_collection(collection_name: str):
    """Get a SQLite table through SQLAlchemy models."""
    model_mapping = {
        'admin_settings': AdminSetting,
        'activity_logs': ActivityLog,
        'users': User,
        # Add other model mappings as needed
    }
    return model_mapping.get(collection_name)


def setup_admin_collections() -> None:
    """Set up all SQLite tables required for the admin system."""
    # Tables are automatically created by SQLAlchemy
    # This function is kept for compatibility
    pass


def create_admin_indexes() -> None:
    """Create indexes for optimal performance of admin tables."""
    # SQLite indexes are created automatically by SQLAlchemy
    # This function is kept for compatibility
    pass


def initialize_default_settings() -> None:
    """Initialize default admin settings if they don't exist."""
    from models_sqlite import AdminSetting, db
    
    default_settings = [
        {
            'key': 'site_name',
            'value': 'MarketHub Pro',
            'category': 'general',
            'description': 'The name of the website',
            'data_type': 'string',
            'is_sensitive': False
        },
        {
            'key': 'site_description',
            'value': 'Your premier e-commerce marketplace',
            'category': 'general',
            'description': 'Site description for SEO and branding',
            'data_type': 'string',
            'is_sensitive': False
        },
        {
            'key': 'contact_email',
            'value': 'contact@markethubpro.com',
            'category': 'general',
            'description': 'Primary contact email address',
            'data_type': 'string',
            'is_sensitive': False
        },
        {
            'key': 'default_currency',
            'value': 'USD',
            'category': 'commerce',
            'description': 'Default currency for the platform',
            'data_type': 'string',
            'is_sensitive': False
        },
        {
            'key': 'products_per_page',
            'value': '24',
            'category': 'display',
            'description': 'Number of products to display per page',
            'data_type': 'number',
            'is_sensitive': False
        },
        {
            'key': 'enable_user_registration',
            'value': 'true',
            'category': 'security',
            'description': 'Allow new users to register accounts',
            'data_type': 'boolean',
            'is_sensitive': False
        },
        {
            'key': 'maintenance_mode',
            'value': 'false',
            'category': 'system',
            'description': 'Enable maintenance mode to disable public access',
            'data_type': 'boolean',
            'is_sensitive': False
        }
    ]
    
    for setting_data in default_settings:
        # Check if setting already exists
        existing = AdminSetting.query.filter_by(key=setting_data['key']).first()
        if not existing:
            setting = AdminSetting(**setting_data)
            db.session.add(setting)
    
    db.session.commit()


def setup_admin_database() -> None:
    """Complete setup of the admin database including tables and default data."""
    setup_admin_collections()
    create_admin_indexes()
    initialize_default_settings()