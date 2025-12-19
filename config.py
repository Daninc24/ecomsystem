"""
Configuration file for the E-commerce Flask application.
Modify these settings to customize your application.
"""

import os
from datetime import timedelta

class Config:
    """Base configuration class."""
    
    # Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    
    # Database Settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///ecommerce.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session Settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Application Settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    
    # Pagination Settings
    PRODUCTS_PER_PAGE = 12
    ORDERS_PER_PAGE = 10
    
    # Payment Gateway Settings
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY') or 'pk_test_your_stripe_publishable_key'
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY') or 'sk_test_your_stripe_secret_key'
    
    # PayPal Settings
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID') or 'your_paypal_client_id'
    PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET') or 'your_paypal_client_secret'
    PAYPAL_MODE = os.environ.get('PAYPAL_MODE') or 'sandbox'  # sandbox or live
    
    # M-Pesa Settings (Safaricom)
    MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY') or 'your_mpesa_consumer_key'
    MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET') or 'your_mpesa_consumer_secret'
    MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE') or 'your_mpesa_shortcode'
    MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY') or 'your_mpesa_passkey'
    MPESA_ENVIRONMENT = os.environ.get('MPESA_ENVIRONMENT') or 'sandbox'  # sandbox or production
    
    # Store Settings
    STORE_NAME = "E-Store"
    STORE_DESCRIPTION = "Your one-stop shop for amazing products"
    CURRENCY = "USD"
    CURRENCY_SYMBOL = "$"
    
    # Image Settings
    UPLOAD_FOLDER = 'static/images/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Security Settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # Set to True to see SQL queries

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    
    # Use PostgreSQL in production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://username:password@localhost/ecommerce'

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Store configuration for easy access
STORE_CONFIG = {
    'name': Config.STORE_NAME,
    'description': Config.STORE_DESCRIPTION,
    'currency': Config.CURRENCY,
    'currency_symbol': Config.CURRENCY_SYMBOL,
    'contact': {
        'email': 'info@estore.com',
        'phone': '(555) 123-4567',
        'address': '123 E-Commerce Street, Business City, BC 12345'
    },
    'social_media': {
        'facebook': 'https://facebook.com/estore',
        'twitter': 'https://twitter.com/estore',
        'instagram': 'https://instagram.com/estore'
    },
    'business_hours': {
        'monday_friday': '9:00 AM - 6:00 PM',
        'saturday': '10:00 AM - 4:00 PM',
        'sunday': 'Closed'
    }
}

# Product categories (can be moved to database later)
PRODUCT_CATEGORIES = [
    'Electronics',
    'Home & Kitchen',
    'Sports & Fitness',
    'Office Supplies',
    'Books',
    'Clothing',
    'Beauty & Health',
    'Toys & Games',
    'Automotive',
    'Garden & Outdoor'
]

# Order status options
ORDER_STATUSES = [
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('shipped', 'Shipped'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled')
]

# User roles
USER_ROLES = [
    ('user', 'User'),
    ('admin', 'Administrator')
]