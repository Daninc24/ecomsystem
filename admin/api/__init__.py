"""
Admin API Package
RESTful API endpoints for the dynamic admin system
"""

from .configuration_api import configuration_bp
from .user_api_sqlite import user_bp
from .theme_api import theme_bp
from .content_api import content_bp
from .analytics_api import analytics_bp

__all__ = [
    'configuration_bp',
    'user_bp',
    'theme_bp',
    'content_bp',
    'analytics_bp'
]