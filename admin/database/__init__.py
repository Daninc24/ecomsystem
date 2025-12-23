"""
Database configuration and initialization for the admin system
"""

from .collections import setup_admin_collections, create_admin_indexes

__all__ = ['setup_admin_collections', 'create_admin_indexes']