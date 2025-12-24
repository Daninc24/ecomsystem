"""
Data Migration Utilities
Handles migration of existing e-commerce data to admin-compatible format
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from bson import ObjectId
from .base_service import BaseService


class DataMigrationService(BaseService):
    """Service for migrating existing e-commerce data to admin system."""
    
    def __init__(self, mongo_db):
        """Initialize with database connection."""
        self.db = mongo_db
        
    def _get_collection_name(self) -> str:
        """Get collection name for migration tracking."""
        return "migration_logs"
    
    def create_migration_log(self, migration_type: str, status: str, details: Dict[str, Any]) -> ObjectId:
        """Create a migration log entry."""
        log_entry = {
            'migration_type': migration_type,
            'status': status,  # 'started', 'completed', 'failed'
            'details': details,
            'started_at': datetime.utcnow(),
            'completed_at': None,
            'error_message': None
        }
        
        result = self.db.migration_logs.insert_one(log_entry)
        return result.inserted_id
    
    def update_migration_log(self, log_id: ObjectId, status: str, error_message: str = None) -> bool:
        """Update migration log with completion status."""
        update_data = {
            'status': status,
            'completed_at': datetime.utcnow()
        }
        
        if error_message:
            update_data['error_message'] = error_message
        
        result = self.db.migration_logs.update_one(
            {'_id': log_id},
            {'$set': update_data}
        )
        return result.modified_count > 0
    
    def migrate_user_authentication(self) -> Dict[str, Any]:
        """Migrate existing user authentication to admin-compatible format."""
        log_id = self.create_migration_log('user_authentication', 'started', {})
        
        try:
            migration_results = {
                'users_processed': 0,
                'users_updated': 0,
                'admin_users_found': 0,
                'errors': []
            }
            
            # Process all users
            users_cursor = self.db.users.find({})
            
            for user in users_cursor:
                migration_results['users_processed'] += 1
                
                try:
                    # Add admin-compatible fields if they don't exist
                    update_fields = {}
                    
                    # Add admin settings
                    if 'admin_settings' not in user:
                        update_fields['admin_settings'] = {
                            'theme_preference': 'default',
                            'dashboard_layout': 'default',
                            'notifications_enabled': True,
                            'timezone': 'UTC',
                            'language': 'en'
                        }
                    
                    # Add permissions based on role
                    if 'permissions' not in user:
                        role = user.get('role', 'user')
                        if role == 'admin':
                            update_fields['permissions'] = [
                                'admin.full_access', 'users.manage', 'products.manage',
                                'orders.manage', 'content.manage', 'theme.manage',
                                'analytics.view', 'system.manage'
                            ]
                            migration_results['admin_users_found'] += 1
                        elif role == 'vendor':
                            update_fields['permissions'] = [
                                'products.manage_own', 'orders.view_own',
                                'analytics.view_own'
                            ]
                        else:
                            update_fields['permissions'] = ['profile.manage']
                    
                    # Add admin metadata
                    if 'admin_metadata' not in user:
                        update_fields['admin_metadata'] = {
                            'migrated_at': datetime.utcnow(),
                            'migration_version': '1.0',
                            'original_role': user.get('role', 'user')
                        }
                    
                    # Add session management fields
                    if 'session_settings' not in user:
                        update_fields['session_settings'] = {
                            'max_sessions': 5,
                            'session_timeout': 3600,  # 1 hour
                            'require_2fa': False,
                            'ip_whitelist': []
                        }
                    
                    # Update user if there are changes
                    if update_fields:
                        self.db.users.update_one(
                            {'_id': user['_id']},
                            {'$set': update_fields}
                        )
                        migration_results['users_updated'] += 1
                
                except Exception as e:
                    migration_results['errors'].append(f"User {user['_id']}: {str(e)}")
            
            self.update_migration_log(log_id, 'completed')
            return migration_results
            
        except Exception as e:
            self.update_migration_log(log_id, 'failed', str(e))
            raise
    
    def migrate_content_data(self) -> Dict[str, Any]:
        """Migrate existing content to version-controlled format."""
        log_id = self.create_migration_log('content_data', 'started', {})
        
        try:
            migration_results = {
                'content_elements_created': 0,
                'templates_processed': 0,
                'errors': []
            }
            
            # Define content elements to migrate from templates/config
            content_elements = [
                {
                    'element_id': 'site_name',
                    'content': 'MarketHub Pro',
                    'element_type': 'text',
                    'location': 'global'
                },
                {
                    'element_id': 'site_description',
                    'content': 'Global Marketplace - Connect, Shop, Thrive',
                    'element_type': 'text',
                    'location': 'global'
                },
                {
                    'element_id': 'hero_title',
                    'content': 'Discover Amazing Products',
                    'element_type': 'text',
                    'location': 'homepage'
                },
                {
                    'element_id': 'hero_subtitle',
                    'content': 'From trusted sellers worldwide',
                    'element_type': 'text',
                    'location': 'homepage'
                },
                {
                    'element_id': 'footer_copyright',
                    'content': '© 2024 MarketHub Pro. All rights reserved.',
                    'element_type': 'text',
                    'location': 'footer'
                }
            ]
            
            for element in content_elements:
                try:
                    # Check if content version already exists
                    existing = self.db.content_versions.find_one({
                        'element_id': element['element_id']
                    })
                    
                    if not existing:
                        content_version = {
                            'element_id': element['element_id'],
                            'content': element['content'],
                            'element_type': element['element_type'],
                            'location': element['location'],
                            'version_number': 1,
                            'is_published': True,
                            'created_at': datetime.utcnow(),
                            'created_by': None,  # System migration
                            'metadata': {
                                'migrated_from': 'config',
                                'migration_version': '1.0'
                            }
                        }
                        
                        self.db.content_versions.insert_one(content_version)
                        migration_results['content_elements_created'] += 1
                
                except Exception as e:
                    migration_results['errors'].append(f"Content {element['element_id']}: {str(e)}")
            
            self.update_migration_log(log_id, 'completed')
            return migration_results
            
        except Exception as e:
            self.update_migration_log(log_id, 'failed', str(e))
            raise
    
    def migrate_product_data(self) -> Dict[str, Any]:
        """Migrate existing products to admin-manageable format."""
        log_id = self.create_migration_log('product_data', 'started', {})
        
        try:
            migration_results = {
                'products_processed': 0,
                'products_updated': 0,
                'categories_created': 0,
                'errors': []
            }
            
            # First, create product categories collection if it doesn't exist
            existing_categories = set()
            products_cursor = self.db.products.find({})
            
            for product in products_cursor:
                migration_results['products_processed'] += 1
                
                try:
                    # Extract category
                    category = product.get('basic_info', {}).get('category')
                    if category and category not in existing_categories:
                        existing_categories.add(category)
                    
                    # Add admin fields to product
                    update_fields = {}
                    
                    if 'admin_metadata' not in product:
                        update_fields['admin_metadata'] = {
                            'migrated_at': datetime.utcnow(),
                            'migration_version': '1.0',
                            'review_status': 'approved',
                            'featured_priority': 0
                        }
                    
                    if 'admin_notes' not in product:
                        update_fields['admin_notes'] = []
                    
                    if 'admin_flags' not in product:
                        update_fields['admin_flags'] = []
                    
                    if 'moderation_status' not in product:
                        update_fields['moderation_status'] = 'approved'
                    
                    # Update product if there are changes
                    if update_fields:
                        self.db.products.update_one(
                            {'_id': product['_id']},
                            {'$set': update_fields}
                        )
                        migration_results['products_updated'] += 1
                
                except Exception as e:
                    migration_results['errors'].append(f"Product {product['_id']}: {str(e)}")
            
            # Create category documents
            for category_name in existing_categories:
                try:
                    # Check if category already exists
                    existing_cat = self.db.product_categories.find_one({'name': category_name})
                    
                    if not existing_cat:
                        category_doc = {
                            'name': category_name,
                            'slug': category_name.lower().replace(' ', '-').replace('&', 'and'),
                            'description': f'Products in {category_name} category',
                            'parent_id': None,
                            'level': 0,
                            'sort_order': 0,
                            'is_active': True,
                            'metadata': {
                                'migrated_at': datetime.utcnow(),
                                'migration_version': '1.0'
                            },
                            'created_at': datetime.utcnow(),
                            'updated_at': datetime.utcnow()
                        }
                        
                        self.db.product_categories.insert_one(category_doc)
                        migration_results['categories_created'] += 1
                
                except Exception as e:
                    migration_results['errors'].append(f"Category {category_name}: {str(e)}")
            
            self.update_migration_log(log_id, 'completed')
            return migration_results
            
        except Exception as e:
            self.update_migration_log(log_id, 'failed', str(e))
            raise
    
    def migrate_order_data(self) -> Dict[str, Any]:
        """Migrate existing orders to admin-manageable format."""
        log_id = self.create_migration_log('order_data', 'started', {})
        
        try:
            migration_results = {
                'orders_processed': 0,
                'orders_updated': 0,
                'errors': []
            }
            
            orders_cursor = self.db.orders.find({})
            
            for order in orders_cursor:
                migration_results['orders_processed'] += 1
                
                try:
                    update_fields = {}
                    
                    # Add admin metadata
                    if 'admin_metadata' not in order:
                        update_fields['admin_metadata'] = {
                            'migrated_at': datetime.utcnow(),
                            'migration_version': '1.0',
                            'priority_level': 'normal',
                            'requires_review': False
                        }
                    
                    # Add admin notes
                    if 'admin_notes' not in order:
                        update_fields['admin_notes'] = []
                    
                    # Add admin actions log
                    if 'admin_actions' not in order:
                        update_fields['admin_actions'] = []
                    
                    # Add fulfillment tracking
                    if 'fulfillment_tracking' not in order:
                        update_fields['fulfillment_tracking'] = {
                            'assigned_to': None,
                            'estimated_ship_date': None,
                            'tracking_number': None,
                            'carrier': None,
                            'last_status_update': datetime.utcnow()
                        }
                    
                    # Update order if there are changes
                    if update_fields:
                        self.db.orders.update_one(
                            {'_id': order['_id']},
                            {'$set': update_fields}
                        )
                        migration_results['orders_updated'] += 1
                
                except Exception as e:
                    migration_results['errors'].append(f"Order {order['_id']}: {str(e)}")
            
            self.update_migration_log(log_id, 'completed')
            return migration_results
            
        except Exception as e:
            self.update_migration_log(log_id, 'failed', str(e))
            raise
    
    def run_full_migration(self) -> Dict[str, Any]:
        """Run complete data migration process."""
        full_migration_log_id = self.create_migration_log('full_migration', 'started', {})
        
        try:
            results = {
                'started_at': datetime.utcnow(),
                'user_migration': None,
                'content_migration': None,
                'product_migration': None,
                'order_migration': None,
                'completed_at': None,
                'overall_status': 'in_progress'
            }
            
            # Run individual migrations
            try:
                results['user_migration'] = self.migrate_user_authentication()
            except Exception as e:
                results['user_migration'] = {'error': str(e)}
            
            try:
                results['content_migration'] = self.migrate_content_data()
            except Exception as e:
                results['content_migration'] = {'error': str(e)}
            
            try:
                results['product_migration'] = self.migrate_product_data()
            except Exception as e:
                results['product_migration'] = {'error': str(e)}
            
            try:
                results['order_migration'] = self.migrate_order_data()
            except Exception as e:
                results['order_migration'] = {'error': str(e)}
            
            results['completed_at'] = datetime.utcnow()
            results['overall_status'] = 'completed'
            
            self.update_migration_log(full_migration_log_id, 'completed')
            return results
            
        except Exception as e:
            self.update_migration_log(full_migration_log_id, 'failed', str(e))
            raise
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get status of all migrations."""
        # Get recent migration logs
        recent_logs = list(self.db.migration_logs.find({})
                          .sort('started_at', -1)
                          .limit(10))
        
        # Get summary statistics
        total_migrations = self.db.migration_logs.count_documents({})
        completed_migrations = self.db.migration_logs.count_documents({'status': 'completed'})
        failed_migrations = self.db.migration_logs.count_documents({'status': 'failed'})
        
        return {
            'total_migrations': total_migrations,
            'completed_migrations': completed_migrations,
            'failed_migrations': failed_migrations,
            'success_rate': (completed_migrations / total_migrations * 100) if total_migrations > 0 else 0,
            'recent_logs': recent_logs,
            'last_check': datetime.utcnow()
        }
    
    def rollback_migration(self, migration_type: str) -> Dict[str, Any]:
        """Rollback a specific migration (where possible)."""
        rollback_log_id = self.create_migration_log(f'rollback_{migration_type}', 'started', {})
        
        try:
            rollback_results = {
                'migration_type': migration_type,
                'items_processed': 0,
                'items_rolled_back': 0,
                'errors': []
            }
            
            if migration_type == 'user_authentication':
                # Remove admin fields added during migration
                users_cursor = self.db.users.find({'admin_metadata.migration_version': '1.0'})
                
                for user in users_cursor:
                    rollback_results['items_processed'] += 1
                    try:
                        self.db.users.update_one(
                            {'_id': user['_id']},
                            {'$unset': {
                                'admin_settings': '',
                                'permissions': '',
                                'admin_metadata': '',
                                'session_settings': ''
                            }}
                        )
                        rollback_results['items_rolled_back'] += 1
                    except Exception as e:
                        rollback_results['errors'].append(f"User {user['_id']}: {str(e)}")
            
            elif migration_type == 'content_data':
                # Remove migrated content versions
                result = self.db.content_versions.delete_many({
                    'metadata.migration_version': '1.0'
                })
                rollback_results['items_rolled_back'] = result.deleted_count
            
            # Add more rollback logic for other migration types as needed
            
            self.update_migration_log(rollback_log_id, 'completed')
            return rollback_results
            
        except Exception as e:
            self.update_migration_log(rollback_log_id, 'failed', str(e))
            raise