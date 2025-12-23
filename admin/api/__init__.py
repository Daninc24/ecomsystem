"""
Admin API Package
RESTful API endpoints for the dynamic admin system
"""

from .configuration_api import configuration_bp
from .content_api import content_bp
from .theme_api import theme_bp
from .user_api import user_bp
from .analytics_api import analytics_bp

__all__ = [
    'configuration_bp',
    'content_bp',
    'theme_bp', 
    'user_bp',
    'analytics_api'
]