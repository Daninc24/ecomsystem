"""
MongoDB Configuration for the Enhanced E-commerce Application.
Modern, scalable configuration with MongoDB Atlas support.
"""

import os
from datetime import timedelta

class Config:
    """Base configuration class for MongoDB."""
    
    # Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    
    # MongoDB Settings
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/ecommerce'
    
    # Session Settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Application Settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    
    # Pagination Settings
    PRODUCTS_PER_PAGE = 20
    ORDERS_PER_PAGE = 15
    
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
    STORE_NAME = "MarketHub Pro"
    STORE_DESCRIPTION = "Global Marketplace - Connect, Shop, Thrive"
    CURRENCY = "USD"
    CURRENCY_SYMBOL = "$"
    
    # Image Settings
    UPLOAD_FOLDER = 'static/images/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Security Settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/ecommerce_dev'

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    
    # Use MongoDB Atlas in production
    MONGO_URI = os.environ.get('MONGO_URI') or \
        'mongodb+srv://username:password@cluster.mongodb.net/ecommerce?retryWrites=true&w=majority'

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    MONGO_URI = 'mongodb://localhost:27017/ecommerce_test'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Enhanced Store configuration
STORE_CONFIG = {
    'name': Config.STORE_NAME,
    'description': Config.STORE_DESCRIPTION,
    'currency': Config.CURRENCY,
    'currency_symbol': Config.CURRENCY_SYMBOL,
    'tagline': 'Discover Amazing Products from Trusted Sellers Worldwide',
    'features': [
        'Global Marketplace',
        'Secure Payments',
        'Fast Shipping',
        'Buyer Protection',
        'Quality Guarantee'
    ],
    'contact': {
        'email': 'support@markethubpro.com',
        'phone': '+1 (555) 123-4567',
        'address': '123 Commerce Street, Business District, NY 10001'
    },
    'social_media': {
        'facebook': 'https://facebook.com/markethubpro',
        'twitter': 'https://twitter.com/markethubpro',
        'instagram': 'https://instagram.com/markethubpro',
        'linkedin': 'https://linkedin.com/company/markethubpro'
    },
    'business_hours': {
        'monday_friday': '24/7 Online Support',
        'saturday': '24/7 Online Support',
        'sunday': '24/7 Online Support'
    },
    'shipping_info': {
        'free_shipping_threshold': 50.0,
        'standard_shipping_cost': 9.99,
        'express_shipping_cost': 19.99,
        'international_shipping': True
    }
}

# Enhanced product categories with icons
PRODUCT_CATEGORIES = [
    {'name': 'Electronics', 'icon': '📱', 'color': '#007bff'},
    {'name': 'Fashion', 'icon': '👗', 'color': '#e91e63'},
    {'name': 'Home & Garden', 'icon': '🏠', 'color': '#4caf50'},
    {'name': 'Sports & Outdoors', 'icon': '⚽', 'color': '#ff9800'},
    {'name': 'Health & Beauty', 'icon': '💄', 'color': '#9c27b0'},
    {'name': 'Automotive', 'icon': '🚗', 'color': '#f44336'},
    {'name': 'Books & Media', 'icon': '📚', 'color': '#795548'},
    {'name': 'Toys & Games', 'icon': '🎮', 'color': '#2196f3'},
    {'name': 'Office Supplies', 'icon': '📋', 'color': '#607d8b'},
    {'name': 'Food & Beverages', 'icon': '🍕', 'color': '#ff5722'}
]

# Order status options with colors
ORDER_STATUSES = [
    {'value': 'pending', 'label': 'Pending', 'color': '#ffc107'},
    {'value': 'confirmed', 'label': 'Confirmed', 'color': '#17a2b8'},
    {'value': 'processing', 'label': 'Processing', 'color': '#007bff'},
    {'value': 'shipped', 'label': 'Shipped', 'color': '#6f42c1'},
    {'value': 'delivered', 'label': 'Delivered', 'color': '#28a745'},
    {'value': 'cancelled', 'label': 'Cancelled', 'color': '#dc3545'},
    {'value': 'refunded', 'label': 'Refunded', 'color': '#6c757d'}
]

# User roles with permissions
USER_ROLES = [
    {'value': 'user', 'label': 'Customer', 'permissions': ['shop', 'order', 'review']},
    {'value': 'vendor', 'label': 'Vendor', 'permissions': ['shop', 'order', 'review', 'sell', 'manage_products']},
    {'value': 'admin', 'label': 'Administrator', 'permissions': ['all']}
]

# MongoDB Collections Schema (for reference)
COLLECTIONS_SCHEMA = {
    'users': {
        '_id': 'ObjectId',
        'username': 'string',
        'email': 'string',
        'password': 'string (hashed)',
        'role': 'string',
        'profile': {
            'first_name': 'string',
            'last_name': 'string',
            'phone': 'string',
            'avatar_url': 'string',
            'date_of_birth': 'datetime',
            'gender': 'string'
        },
        'addresses': [
            {
                'type': 'string',  # shipping, billing
                'street': 'string',
                'city': 'string',
                'state': 'string',
                'zip_code': 'string',
                'country': 'string',
                'is_default': 'boolean'
            }
        ],
        'preferences': {
            'language': 'string',
            'currency': 'string',
            'notifications': 'object'
        },
        'created_at': 'datetime',
        'updated_at': 'datetime',
        'last_login': 'datetime',
        'is_active': 'boolean',
        'email_verified': 'boolean'
    },
    'vendors': {
        '_id': 'ObjectId',
        'user_id': 'ObjectId',
        'business_info': {
            'name': 'string',
            'description': 'string',
            'category': 'string',
            'website': 'string',
            'logo_url': 'string',
            'banner_url': 'string'
        },
        'contact_info': {
            'email': 'string',
            'phone': 'string',
            'address': 'object'
        },
        'verification': {
            'is_verified': 'boolean',
            'verification_date': 'datetime',
            'documents': 'array'
        },
        'performance': {
            'rating': 'float',
            'total_reviews': 'int',
            'total_sales': 'float',
            'total_orders': 'int',
            'response_rate': 'float',
            'response_time': 'int'  # in hours
        },
        'settings': {
            'commission_rate': 'float',
            'auto_approve_orders': 'boolean',
            'vacation_mode': 'boolean'
        },
        'created_at': 'datetime',
        'updated_at': 'datetime'
    },
    'products': {
        '_id': 'ObjectId',
        'vendor_id': 'ObjectId',
        'basic_info': {
            'name': 'string',
            'description': 'string',
            'short_description': 'string',
            'category': 'string',
            'subcategory': 'string',
            'brand': 'string',
            'model': 'string',
            'sku': 'string'
        },
        'pricing': {
            'price': 'float',
            'compare_price': 'float',
            'cost_price': 'float',
            'discount_percentage': 'float',
            'bulk_pricing': 'array'
        },
        'inventory': {
            'stock': 'int',
            'low_stock_threshold': 'int',
            'track_inventory': 'boolean',
            'allow_backorders': 'boolean'
        },
        'media': {
            'images': 'array',
            'videos': 'array',
            'main_image': 'string'
        },
        'attributes': {
            'weight': 'float',
            'dimensions': 'object',
            'color': 'string',
            'size': 'string',
            'material': 'string',
            'custom_attributes': 'object'
        },
        'seo': {
            'meta_title': 'string',
            'meta_description': 'string',
            'tags': 'array',
            'slug': 'string'
        },
        'shipping': {
            'free_shipping': 'boolean',
            'shipping_cost': 'float',
            'processing_time': 'int',
            'shipping_from': 'string'
        },
        'status': 'string',  # active, inactive, draft, archived
        'is_featured': 'boolean',
        'created_at': 'datetime',
        'updated_at': 'datetime',
        'views': 'int',
        'favorites': 'int'
    }
}