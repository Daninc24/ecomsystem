"""
SQLite Configuration for E-commerce System
"""

import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Basic Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # SQLite Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///ecommerce.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Admin Database (separate SQLite file for admin system)
    ADMIN_DATABASE_URI = os.environ.get('ADMIN_DATABASE_URL') or 'sqlite:///admin.db'
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'ecommerce:'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Security Configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
    
    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@markethubpro.com'
    
    # Cache Configuration
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Admin Configuration
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'admin@markethubpro.com'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'
    
    # Pagination
    POSTS_PER_PAGE = 24
    USERS_PER_PAGE = 50
    ORDERS_PER_PAGE = 25
    
    # API Configuration
    API_RATE_LIMIT = "100 per hour"
    API_KEY_EXPIRY_DAYS = 365
    
    # Theme Configuration
    DEFAULT_THEME = 'aliexpress'
    THEME_CACHE_TIMEOUT = 3600  # 1 hour
    
    # Search Configuration
    SEARCH_RESULTS_PER_PAGE = 20
    
    # Payment Configuration
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID')
    PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET')
    
    # Shipping Configuration
    SHIPPING_API_KEY = os.environ.get('SHIPPING_API_KEY')
    DEFAULT_SHIPPING_COST = 9.99
    FREE_SHIPPING_THRESHOLD = 50.00
    
    # Analytics Configuration
    GOOGLE_ANALYTICS_ID = os.environ.get('GOOGLE_ANALYTICS_ID')
    FACEBOOK_PIXEL_ID = os.environ.get('FACEBOOK_PIXEL_ID')
    
    # Social Media Configuration
    FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID')
    FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET')
    TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY')
    TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET')
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'logs/app.log'
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration"""
        # Ensure upload directory exists
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        # Ensure logs directory exists
        os.makedirs(os.path.dirname(Config.LOG_FILE), exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Development-specific database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///dev_ecommerce.db'
    ADMIN_DATABASE_URI = os.environ.get('DEV_ADMIN_DATABASE_URL') or 'sqlite:///dev_admin.db'
    
    # Disable CSRF for development
    WTF_CSRF_ENABLED = False
    
    # Development email settings
    MAIL_SUPPRESS_SEND = True
    
    # Cache disabled for development
    CACHE_TYPE = 'null'


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = False
    
    # In-memory database for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    ADMIN_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Disable email sending in tests
    MAIL_SUPPRESS_SEND = True
    
    # Fast password hashing for tests
    BCRYPT_LOG_ROUNDS = 4


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production database (can be overridden with environment variables)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///prod_ecommerce.db'
    ADMIN_DATABASE_URI = os.environ.get('ADMIN_DATABASE_URL') or 'sqlite:///prod_admin.db'
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Production logging
    LOG_LEVEL = 'WARNING'
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Production-specific initialization
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug and not app.testing:
            # Set up file logging
            file_handler = RotatingFileHandler(
                cls.LOG_FILE, maxBytes=10240000, backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            app.logger.setLevel(logging.INFO)
            app.logger.info('E-commerce application startup')


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}