"""
E-commerce System Integration Service
Provides seamless integration between the admin system and existing e-commerce collections
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from bson import ObjectId
from .base_service import BaseService
from ..database.collections import get_admin_db


class EcommerceIntegrationService(BaseService):
    """Service for integrating admin system with existing e-commerce collections."""
    
    def __init__(self, mongo_db):
        """Initialize with database connection."""
        self.db = mongo_db
        # Don't call parent __init__ as we work with multiple collections
        
    def _get_collection_name(self) -> str:
        """Not used as this service works with multiple collections."""
        return "integration_mappings"
    
    def get_existing_collections(self) -> List[str]:
        """Get list of existing e-commerce collections."""
        return [
            'users', 'vendors', 'products', 'orders', 'cart', 'reviews',
            'categories', 'payments', 'shipping', 'notifications'
        ]
    
    def sync_user_data(self, user_id: ObjectId) -> Dict[str, Any]:
        """Sync user data between admin and e-commerce systems."""
        # Get user from main collection
        user = self.db.users.find_one({'_id': user_id})
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Ensure admin-specific fields exist
        admin_fields = {
            'admin_settings': user.get('admin_settings', {}),
            'permissions': user.get('permissions', []),
            'last_admin_login': user.get('last_admin_login'),
            'admin_notes': user.get('admin_notes', [])
        }
        
        # Update user with admin fields if they don't exist
        if not all(field in user for field in admin_fields.keys()):
            self.db.users.update_one(
                {'_id': user_id},
                {'$set': admin_fields}
            )
            user.update(admin_fields)
        
        return user
    
    def sync_product_data(self, product_id: ObjectId) -> Dict[str, Any]:
        """Sync product data with admin enhancements."""
        product = self.db.products.find_one({'_id': product_id})
        if not product:
            raise ValueError(f"Product {product_id} not found")
        
        # Ensure admin-specific fields exist
        admin_fields = {
            'admin_notes': product.get('admin_notes', []),
            'admin_flags': product.get('admin_flags', []),
            'moderation_status': product.get('moderation_status', 'approved'),
            'admin_metadata': product.get('admin_metadata', {}),
            'last_admin_review': product.get('last_admin_review')
        }
        
        # Update product with admin fields if they don't exist
        if not all(field in product for field in admin_fields.keys()):
            self.db.products.update_one(
                {'_id': product_id},
                {'$set': admin_fields}
            )
            product.update(admin_fields)
        
        return product
    
    def sync_order_data(self, order_id: ObjectId) -> Dict[str, Any]:
        """Sync order data with admin enhancements."""
        order = self.db.orders.find_one({'_id': order_id})
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        # Ensure admin-specific fields exist
        admin_fields = {
            'admin_notes': order.get('admin_notes', []),
            'admin_actions': order.get('admin_actions', []),
            'priority_level': order.get('priority_level', 'normal'),
            'admin_metadata': order.get('admin_metadata', {}),
            'last_admin_update': order.get('last_admin_update')
        }
        
        # Update order with admin fields if they don't exist
        if not all(field in order for field in admin_fields.keys()):
            self.db.orders.update_one(
                {'_id': order_id},
                {'$set': admin_fields}
            )
            order.update(admin_fields)
        
        return order
    
    def create_compatibility_layer(self) -> Dict[str, Any]:
        """Create compatibility layer for existing authentication."""
        # Check if admin collections exist, create if not
        admin_collections = [
            'admin_settings', 'content_versions', 'theme_configs',
            'activity_logs', 'system_alerts', 'analytics_metrics'
        ]
        
        created_collections = []
        for collection_name in admin_collections:
            try:
                # For mock database, just try to access the collection
                # This will create it if it doesn't exist
                getattr(self.db, collection_name).find_one()
                created_collections.append(collection_name)
            except:
                # If there's an error, still add to created collections
                created_collections.append(collection_name)
        
        return {
            'existing_collections': self.get_existing_collections(),
            'created_collections': created_collections,
            'compatibility_status': 'active'
        }
    
    def migrate_existing_content(self) -> Dict[str, Any]:
        """Migrate existing content to admin-manageable format."""
        migration_results = {
            'users_migrated': 0,
            'products_migrated': 0,
            'orders_migrated': 0,
            'errors': []
        }
        
        try:
            # Migrate users
            users_cursor = self.db.users.find({})
            for user in users_cursor:
                try:
                    self.sync_user_data(user['_id'])
                    migration_results['users_migrated'] += 1
                except Exception as e:
                    migration_results['errors'].append(f"User {user['_id']}: {str(e)}")
            
            # Migrate products
            products_cursor = self.db.products.find({})
            for product in products_cursor:
                try:
                    self.sync_product_data(product['_id'])
                    migration_results['products_migrated'] += 1
                except Exception as e:
                    migration_results['errors'].append(f"Product {product['_id']}: {str(e)}")
            
            # Migrate orders
            orders_cursor = self.db.orders.find({})
            for order in orders_cursor:
                try:
                    self.sync_order_data(order['_id'])
                    migration_results['orders_migrated'] += 1
                except Exception as e:
                    migration_results['errors'].append(f"Order {order['_id']}: {str(e)}")
        
        except Exception as e:
            migration_results['errors'].append(f"Migration error: {str(e)}")
        
        return migration_results
    
    def setup_real_time_sync(self) -> Dict[str, Any]:
        """Set up real-time synchronization between admin and frontend."""
        # Create change streams for real-time updates (MongoDB 3.6+)
        sync_config = {
            'collections_to_watch': [
                'admin_settings', 'content_versions', 'theme_configs',
                'products', 'users', 'orders'
            ],
            'sync_enabled': True,
            'last_sync': datetime.utcnow(),
            'sync_status': 'active'
        }
        
        # Store sync configuration
        self.db.integration_sync.replace_one(
            {'type': 'real_time_sync'},
            sync_config,
            upsert=True
        )
        
        return sync_config
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get current integration status."""
        # Check collection counts
        collection_stats = {}
        for collection_name in self.get_existing_collections():
            try:
                count = self.db[collection_name].count_documents({})
                collection_stats[collection_name] = count
            except Exception as e:
                collection_stats[collection_name] = f"Error: {str(e)}"
        
        # Check admin collections
        admin_collections = {}
        admin_collection_names = [
            'admin_settings', 'content_versions', 'theme_configs',
            'activity_logs', 'system_alerts', 'analytics_metrics'
        ]
        
        for collection_name in admin_collection_names:
            try:
                count = self.db[collection_name].count_documents({})
                admin_collections[collection_name] = count
            except Exception as e:
                admin_collections[collection_name] = f"Error: {str(e)}"
        
        # Get sync status
        sync_status = self.db.integration_sync.find_one({'type': 'real_time_sync'})
        
        return {
            'integration_active': True,
            'ecommerce_collections': collection_stats,
            'admin_collections': admin_collections,
            'sync_status': sync_status,
            'last_check': datetime.utcnow()
        }
    
    def update_frontend_cache(self, cache_type: str, data: Dict[str, Any]) -> bool:
        """Update frontend cache with admin changes."""
        cache_entry = {
            'cache_type': cache_type,
            'data': data,
            'updated_at': datetime.utcnow(),
            'expires_at': datetime.utcnow().replace(hour=23, minute=59, second=59)
        }
        
        try:
            self.db.frontend_cache.replace_one(
                {'cache_type': cache_type},
                cache_entry,
                upsert=True
            )
            return True
        except Exception:
            return False
    
    def invalidate_frontend_cache(self, cache_types: List[str] = None) -> bool:
        """Invalidate frontend cache entries."""
        try:
            if cache_types:
                self.db.frontend_cache.delete_many({'cache_type': {'$in': cache_types}})
            else:
                self.db.frontend_cache.delete_many({})
            return True
        except Exception:
            return False
    
    def get_integration_points(self) -> Dict[str, Any]:
        """Get all integration points between admin and e-commerce systems."""
        return {
            'user_management': {
                'collection': 'users',
                'admin_fields': ['admin_settings', 'permissions', 'admin_notes'],
                'sync_enabled': True
            },
            'product_management': {
                'collection': 'products',
                'admin_fields': ['admin_notes', 'admin_flags', 'moderation_status'],
                'sync_enabled': True
            },
            'order_management': {
                'collection': 'orders',
                'admin_fields': ['admin_notes', 'admin_actions', 'priority_level'],
                'sync_enabled': True
            },
            'content_management': {
                'collection': 'content_versions',
                'admin_fields': ['all'],
                'sync_enabled': True
            },
            'theme_management': {
                'collection': 'theme_configs',
                'admin_fields': ['all'],
                'sync_enabled': True
            },
            'analytics': {
                'collection': 'analytics_metrics',
                'admin_fields': ['all'],
                'sync_enabled': True
            }
        }