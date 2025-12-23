"""
Test configuration and fixtures for the dynamic admin system
"""

import pytest
from datetime import datetime
from bson import ObjectId
from simple_mongo_mock import mock_mongo


@pytest.fixture
def mongo_db():
    """Provide a clean MongoDB mock instance for testing."""
    # Clear all collections by deleting their files
    import os
    import shutil
    
    db_path = "mock_db/ecommerce"
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    
    # Recreate the database directory
    os.makedirs(db_path, exist_ok=True)
    
    return mock_mongo.db


@pytest.fixture
def sample_admin_setting():
    """Provide a sample admin setting for testing."""
    return {
        'key': 'site_name',
        'value': 'MarketHub Pro',
        'category': 'general',
        'description': 'The name of the site',
        'validation_rules': {
            'type': 'string',
            'min_length': 1,
            'max_length': 100
        },
        'is_sensitive': False,
        'requires_restart': False,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'created_by': ObjectId(),
        'updated_by': ObjectId()
    }


@pytest.fixture
def configuration_manager(mongo_db):
    """Provide a ConfigurationManager instance for testing."""
    from admin.services.configuration_manager import ConfigurationManager
    return ConfigurationManager(mongo_db)


@pytest.fixture
def sample_user_id():
    """Provide a sample user ID for testing."""
    return ObjectId()