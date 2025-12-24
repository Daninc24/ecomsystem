"""
Real-time Synchronization Service
Handles real-time synchronization between admin changes and frontend display
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from bson import ObjectId
from .base_service import BaseService
import json
import threading
import time


class RealtimeSyncService(BaseService):
    """Service for real-time synchronization between admin and frontend."""
    
    def __init__(self, mongo_db):
        """Initialize with database connection."""
        self.db = mongo_db
        self._sync_handlers = {}
        self._sync_active = False
        self._sync_thread = None
        
    def _get_collection_name(self) -> str:
        """Get collection name for sync tracking."""
        return "sync_events"
    
    def register_sync_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """Register a handler for specific sync events."""
        if event_type not in self._sync_handlers:
            self._sync_handlers[event_type] = []
        self._sync_handlers[event_type].append(handler)
    
    def trigger_sync_event(self, event_type: str, data: Dict[str, Any], user_id: ObjectId = None) -> bool:
        """Trigger a synchronization event."""
        try:
            # Create sync event record
            sync_event = {
                'event_type': event_type,
                'data': data,
                'user_id': user_id,
                'timestamp': datetime.utcnow(),
                'status': 'pending',
                'processed_at': None,
                'error_message': None
            }
            
            result = self.db.sync_events.insert_one(sync_event)
            sync_event['_id'] = result.inserted_id
            
            # Process sync event immediately
            self._process_sync_event(sync_event)
            
            return True
            
        except Exception as e:
            print(f"Error triggering sync event: {str(e)}")
            return False
    
    def _process_sync_event(self, event: Dict[str, Any]) -> bool:
        """Process a single sync event."""
        try:
            event_type = event['event_type']
            
            # Update frontend cache based on event type
            if event_type == 'configuration_changed':
                self._sync_configuration_change(event['data'])
            elif event_type == 'content_updated':
                self._sync_content_update(event['data'])
            elif event_type == 'theme_changed':
                self._sync_theme_change(event['data'])
            elif event_type == 'product_updated':
                self._sync_product_update(event['data'])
            elif event_type == 'user_updated':
                self._sync_user_update(event['data'])
            elif event_type == 'order_updated':
                self._sync_order_update(event['data'])
            
            # Call registered handlers
            if event_type in self._sync_handlers:
                for handler in self._sync_handlers[event_type]:
                    try:
                        handler(event['data'])
                    except Exception as e:
                        print(f"Error in sync handler: {str(e)}")
            
            # Mark event as processed
            self.db.sync_events.update_one(
                {'_id': event['_id']},
                {'$set': {
                    'status': 'processed',
                    'processed_at': datetime.utcnow()
                }}
            )
            
            return True
            
        except Exception as e:
            # Mark event as failed
            self.db.sync_events.update_one(
                {'_id': event['_id']},
                {'$set': {
                    'status': 'failed',
                    'processed_at': datetime.utcnow(),
                    'error_message': str(e)
                }}
            )
            return False
    
    def _sync_configuration_change(self, data: Dict[str, Any]) -> None:
        """Sync configuration changes to frontend cache."""
        setting_key = data.get('key')
        setting_value = data.get('value')
        
        if setting_key and setting_value is not None:
            # Update frontend configuration cache
            self.db.frontend_cache.replace_one(
                {'cache_type': 'configuration', 'key': setting_key},
                {
                    'cache_type': 'configuration',
                    'key': setting_key,
                    'value': setting_value,
                    'updated_at': datetime.utcnow(),
                    'expires_at': datetime.utcnow() + timedelta(hours=24)
                },
                upsert=True
            )
            
            # Invalidate related caches
            self._invalidate_cache(['site_config', 'navigation'])
    
    def _sync_content_update(self, data: Dict[str, Any]) -> None:
        """Sync content updates to frontend cache."""
        element_id = data.get('element_id')
        content = data.get('content')
        
        if element_id and content is not None:
            # Update content cache
            self.db.frontend_cache.replace_one(
                {'cache_type': 'content', 'element_id': element_id},
                {
                    'cache_type': 'content',
                    'element_id': element_id,
                    'content': content,
                    'updated_at': datetime.utcnow(),
                    'expires_at': datetime.utcnow() + timedelta(hours=12)
                },
                upsert=True
            )
            
            # Invalidate page caches that might contain this content
            location = data.get('location', 'unknown')
            if location == 'homepage':
                self._invalidate_cache(['homepage'])
            elif location == 'global':
                self._invalidate_cache(['site_config', 'navigation', 'footer'])
    
    def _sync_theme_change(self, data: Dict[str, Any]) -> None:
        """Sync theme changes to frontend cache."""
        theme_property = data.get('property')
        theme_value = data.get('value')
        
        if theme_property and theme_value is not None:
            # Update theme cache
            self.db.frontend_cache.replace_one(
                {'cache_type': 'theme', 'property': theme_property},
                {
                    'cache_type': 'theme',
                    'property': theme_property,
                    'value': theme_value,
                    'updated_at': datetime.utcnow(),
                    'expires_at': datetime.utcnow() + timedelta(hours=6)
                },
                upsert=True
            )
            
            # Generate and cache updated CSS
            self._generate_theme_css()
            
            # Invalidate all page caches since theme affects everything
            self._invalidate_cache(['all_pages'])
    
    def _sync_product_update(self, data: Dict[str, Any]) -> None:
        """Sync product updates to frontend cache."""
        product_id = data.get('product_id')
        
        if product_id:
            # Invalidate product-related caches
            self._invalidate_cache([
                f'product_{product_id}',
                'products_list',
                'featured_products',
                'category_products'
            ])
            
            # Update search index if needed
            self._update_search_index('product', product_id)
    
    def _sync_user_update(self, data: Dict[str, Any]) -> None:
        """Sync user updates to frontend cache."""
        user_id = data.get('user_id')
        
        if user_id:
            # Invalidate user-related caches
            self._invalidate_cache([
                f'user_{user_id}',
                'user_sessions'
            ])
            
            # Update user permissions cache if role changed
            if 'role' in data:
                self._update_user_permissions_cache(user_id)
    
    def _sync_order_update(self, data: Dict[str, Any]) -> None:
        """Sync order updates to frontend cache."""
        order_id = data.get('order_id')
        user_id = data.get('user_id')
        
        if order_id:
            # Invalidate order-related caches
            self._invalidate_cache([
                f'order_{order_id}',
                f'user_orders_{user_id}' if user_id else None,
                'order_analytics'
            ])
    
    def _invalidate_cache(self, cache_keys: List[str]) -> None:
        """Invalidate specific cache entries."""
        for cache_key in cache_keys:
            if cache_key:
                if cache_key == 'all_pages':
                    # Invalidate all page caches
                    self.db.frontend_cache.delete_many({
                        'cache_type': {'$in': ['page', 'content', 'theme']}
                    })
                else:
                    # Invalidate specific cache
                    self.db.frontend_cache.delete_many({
                        '$or': [
                            {'cache_type': cache_key},
                            {'key': cache_key},
                            {'element_id': cache_key}
                        ]
                    })
    
    def _generate_theme_css(self) -> None:
        """Generate and cache updated CSS from theme settings."""
        try:
            # Get current theme configuration
            theme_config = self.db.theme_configs.find_one({'is_active': True})
            
            if theme_config:
                # Generate CSS from theme settings
                css_content = self._build_css_from_theme(theme_config.get('settings', {}))
                
                # Cache generated CSS
                self.db.frontend_cache.replace_one(
                    {'cache_type': 'generated_css'},
                    {
                        'cache_type': 'generated_css',
                        'content': css_content,
                        'updated_at': datetime.utcnow(),
                        'expires_at': datetime.utcnow() + timedelta(hours=24)
                    },
                    upsert=True
                )
        
        except Exception as e:
            print(f"Error generating theme CSS: {str(e)}")
    
    def _build_css_from_theme(self, theme_settings: Dict[str, Any]) -> str:
        """Build CSS content from theme settings."""
        css_rules = []
        
        # Primary colors
        if 'primary_color' in theme_settings:
            css_rules.append(f":root {{ --primary-color: {theme_settings['primary_color']}; }}")
        
        if 'secondary_color' in theme_settings:
            css_rules.append(f":root {{ --secondary-color: {theme_settings['secondary_color']}; }}")
        
        # Typography
        if 'font_family' in theme_settings:
            css_rules.append(f"body {{ font-family: {theme_settings['font_family']}; }}")
        
        if 'font_size' in theme_settings:
            css_rules.append(f"body {{ font-size: {theme_settings['font_size']}px; }}")
        
        # Layout
        if 'container_width' in theme_settings:
            css_rules.append(f".container {{ max-width: {theme_settings['container_width']}px; }}")
        
        return '\n'.join(css_rules)
    
    def _update_search_index(self, item_type: str, item_id: str) -> None:
        """Update search index for changed items."""
        try:
            if item_type == 'product':
                product = self.db.products.find_one({'_id': ObjectId(item_id)})
                if product:
                    # Update search index entry
                    search_entry = {
                        'item_type': 'product',
                        'item_id': item_id,
                        'title': product.get('basic_info', {}).get('name', ''),
                        'description': product.get('basic_info', {}).get('description', ''),
                        'keywords': product.get('seo', {}).get('tags', []),
                        'updated_at': datetime.utcnow()
                    }
                    
                    self.db.search_index.replace_one(
                        {'item_type': 'product', 'item_id': item_id},
                        search_entry,
                        upsert=True
                    )
        
        except Exception as e:
            print(f"Error updating search index: {str(e)}")
    
    def _update_user_permissions_cache(self, user_id: str) -> None:
        """Update user permissions cache."""
        try:
            user = self.db.users.find_one({'_id': ObjectId(user_id)})
            if user:
                permissions_cache = {
                    'user_id': user_id,
                    'role': user.get('role', 'user'),
                    'permissions': user.get('permissions', []),
                    'updated_at': datetime.utcnow(),
                    'expires_at': datetime.utcnow() + timedelta(hours=1)
                }
                
                self.db.frontend_cache.replace_one(
                    {'cache_type': 'user_permissions', 'user_id': user_id},
                    permissions_cache,
                    upsert=True
                )
        
        except Exception as e:
            print(f"Error updating user permissions cache: {str(e)}")
    
    def start_sync_monitoring(self) -> bool:
        """Start background sync monitoring."""
        if self._sync_active:
            return False
        
        self._sync_active = True
        self._sync_thread = threading.Thread(target=self._sync_monitor_loop, daemon=True)
        self._sync_thread.start()
        
        return True
    
    def stop_sync_monitoring(self) -> bool:
        """Stop background sync monitoring."""
        if not self._sync_active:
            return False
        
        self._sync_active = False
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
        
        return True
    
    def _sync_monitor_loop(self) -> None:
        """Background loop for processing pending sync events."""
        while self._sync_active:
            try:
                # Process pending sync events
                pending_events = list(self.db.sync_events.find({
                    'status': 'pending',
                    'timestamp': {'$gte': datetime.utcnow() - timedelta(hours=1)}
                }).limit(10))
                
                for event in pending_events:
                    self._process_sync_event(event)
                
                # Clean up old processed events
                cutoff_time = datetime.utcnow() - timedelta(days=7)
                self.db.sync_events.delete_many({
                    'status': {'$in': ['processed', 'failed']},
                    'timestamp': {'$lt': cutoff_time}
                })
                
                # Sleep before next iteration
                time.sleep(5)
                
            except Exception as e:
                print(f"Error in sync monitor loop: {str(e)}")
                time.sleep(10)
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current synchronization status."""
        # Count sync events by status
        pending_count = self.db.sync_events.count_documents({'status': 'pending'})
        processed_count = self.db.sync_events.count_documents({'status': 'processed'})
        failed_count = self.db.sync_events.count_documents({'status': 'failed'})
        
        # Get recent events
        recent_events = list(self.db.sync_events.find({})
                           .sort('timestamp', -1)
                           .limit(10))
        
        # Get cache statistics
        cache_count = self.db.frontend_cache.count_documents({})
        expired_cache_count = self.db.frontend_cache.count_documents({
            'expires_at': {'$lt': datetime.utcnow()}
        })
        
        return {
            'sync_active': self._sync_active,
            'pending_events': pending_count,
            'processed_events': processed_count,
            'failed_events': failed_count,
            'recent_events': recent_events,
            'cache_entries': cache_count,
            'expired_cache_entries': expired_cache_count,
            'registered_handlers': len(self._sync_handlers),
            'last_check': datetime.utcnow()
        }
    
    def cleanup_expired_cache(self) -> int:
        """Clean up expired cache entries."""
        result = self.db.frontend_cache.delete_many({
            'expires_at': {'$lt': datetime.utcnow()}
        })
        return result.deleted_count
    
    def force_cache_refresh(self, cache_types: List[str] = None) -> bool:
        """Force refresh of specific cache types."""
        try:
            if cache_types:
                self.db.frontend_cache.delete_many({
                    'cache_type': {'$in': cache_types}
                })
            else:
                self.db.frontend_cache.delete_many({})
            
            # Trigger regeneration of critical caches
            self._generate_theme_css()
            
            return True
            
        except Exception as e:
            print(f"Error forcing cache refresh: {str(e)}")
            return False