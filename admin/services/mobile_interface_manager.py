"""
Mobile Interface Manager for Admin System
Handles mobile-responsive UI components and touch interactions
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from bson import ObjectId
from .base_service import BaseService


class MobileInterfaceManager(BaseService):
    """Manages mobile-responsive admin interface components."""
    
    def _get_collection_name(self) -> str:
        return "mobile_interface_settings"
    
    def __init__(self, mongo_db):
        super().__init__(mongo_db)
        self.notification_collection = self.db.mobile_notifications
        self.touch_settings_collection = self.db.touch_interface_settings
        self.mobile_layouts_collection = self.db.mobile_layouts
    
    def get_mobile_dashboard_config(self, user_id: ObjectId) -> Dict[str, Any]:
        """Get mobile dashboard configuration for a user."""
        config = self.collection.find_one({
            'user_id': user_id,
            'type': 'dashboard_config'
        })
        
        if not config:
            # Return default mobile dashboard config
            config = self._get_default_mobile_dashboard()
            self.create_mobile_dashboard_config(user_id, config)
        
        return config
    
    def _get_default_mobile_dashboard(self) -> Dict[str, Any]:
        """Get default mobile dashboard configuration."""
        return {
            'type': 'dashboard_config',
            'layout': 'mobile_optimized',
            'widgets': [
                {
                    'id': 'quick_stats',
                    'type': 'stats_grid',
                    'position': 1,
                    'size': 'full_width',
                    'config': {
                        'columns': 2,
                        'metrics': ['users', 'orders', 'revenue', 'alerts']
                    }
                },
                {
                    'id': 'quick_actions',
                    'type': 'action_grid',
                    'position': 2,
                    'size': 'full_width',
                    'config': {
                        'columns': 2,
                        'actions': [
                            'manage_orders',
                            'manage_users',
                            'view_analytics',
                            'system_alerts'
                        ]
                    }
                },
                {
                    'id': 'recent_activity',
                    'type': 'activity_feed',
                    'position': 3,
                    'size': 'full_width',
                    'config': {
                        'limit': 5,
                        'show_timestamps': True
                    }
                }
            ],
            'touch_settings': {
                'tap_delay': 0,
                'swipe_threshold': 50,
                'long_press_duration': 500
            }
        }
    
    def create_mobile_dashboard_config(self, user_id: ObjectId, config: Dict[str, Any]) -> ObjectId:
        """Create mobile dashboard configuration for a user."""
        config.update({
            'user_id': user_id,
            'type': 'dashboard_config'
        })
        return self.create(config, user_id)
    
    def update_mobile_dashboard_config(self, user_id: ObjectId, config: Dict[str, Any]) -> bool:
        """Update mobile dashboard configuration for a user."""
        existing_config = self.collection.find_one({
            'user_id': user_id,
            'type': 'dashboard_config'
        })
        
        if existing_config:
            return self.update(existing_config['_id'], config, user_id)
        else:
            self.create_mobile_dashboard_config(user_id, config)
            return True
    
    def get_touch_interface_settings(self) -> Dict[str, Any]:
        """Get touch interface settings for mobile devices."""
        settings = self.touch_settings_collection.find_one({'type': 'global_touch_settings'})
        
        if not settings:
            settings = self._get_default_touch_settings()
            self.touch_settings_collection.insert_one(settings)
        
        return settings
    
    def _get_default_touch_settings(self) -> Dict[str, Any]:
        """Get default touch interface settings."""
        return {
            'type': 'global_touch_settings',
            'button_min_size': 44,  # iOS HIG minimum touch target
            'touch_padding': 8,
            'swipe_gestures': {
                'enabled': True,
                'threshold': 50,
                'velocity_threshold': 0.3
            },
            'long_press': {
                'enabled': True,
                'duration': 500
            },
            'double_tap': {
                'enabled': True,
                'max_delay': 300
            },
            'haptic_feedback': {
                'enabled': True,
                'intensity': 'medium'
            }
        }
    
    def create_push_notification(self, user_id: ObjectId, notification_data: Dict[str, Any]) -> ObjectId:
        """Create a push notification for mobile devices."""
        notification = {
            'user_id': user_id,
            'title': notification_data.get('title', ''),
            'message': notification_data.get('message', ''),
            'type': notification_data.get('type', 'info'),
            'priority': notification_data.get('priority', 'normal'),
            'action_url': notification_data.get('action_url'),
            'icon': notification_data.get('icon'),
            'badge_count': notification_data.get('badge_count', 0),
            'sound': notification_data.get('sound', 'default'),
            'vibration_pattern': notification_data.get('vibration_pattern', [200, 100, 200]),
            'is_read': False,
            'is_sent': False,
            'scheduled_at': notification_data.get('scheduled_at'),
            'expires_at': notification_data.get('expires_at'),
            'metadata': notification_data.get('metadata', {})
        }
        
        result = self.notification_collection.insert_one(notification)
        
        # If not scheduled, send immediately
        if not notification.get('scheduled_at'):
            self._send_push_notification(result.inserted_id)
        
        return result.inserted_id
    
    def _send_push_notification(self, notification_id: ObjectId) -> bool:
        """Send a push notification (placeholder for actual implementation)."""
        # In a real implementation, this would integrate with:
        # - Firebase Cloud Messaging (FCM) for Android
        # - Apple Push Notification Service (APNs) for iOS
        # - Web Push API for web browsers
        
        notification = self.notification_collection.find_one({'_id': notification_id})
        if not notification:
            return False
        
        # Mark as sent
        self.notification_collection.update_one(
            {'_id': notification_id},
            {
                '$set': {
                    'is_sent': True,
                    'sent_at': datetime.utcnow()
                }
            }
        )
        
        return True
    
    def get_mobile_notifications(self, user_id: ObjectId, limit: int = 20) -> List[Dict[str, Any]]:
        """Get mobile notifications for a user."""
        return list(self.notification_collection.find(
            {'user_id': user_id},
            sort=[('created_at', -1)],
            limit=limit
        ))
    
    def mark_notification_read(self, notification_id: ObjectId, user_id: ObjectId) -> bool:
        """Mark a notification as read."""
        result = self.notification_collection.update_one(
            {'_id': notification_id, 'user_id': user_id},
            {
                '$set': {
                    'is_read': True,
                    'read_at': datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    def get_mobile_layout_config(self, screen_size: str) -> Dict[str, Any]:
        """Get mobile layout configuration for different screen sizes."""
        layout = self.mobile_layouts_collection.find_one({
            'screen_size': screen_size,
            'type': 'admin_layout'
        })
        
        if not layout:
            layout = self._get_default_mobile_layout(screen_size)
            self.mobile_layouts_collection.insert_one(layout)
        
        return layout
    
    def _get_default_mobile_layout(self, screen_size: str) -> Dict[str, Any]:
        """Get default mobile layout configuration."""
        base_layout = {
            'type': 'admin_layout',
            'screen_size': screen_size,
            'navigation': {
                'type': 'bottom_tabs',
                'items': [
                    {'id': 'dashboard', 'icon': 'dashboard', 'label': 'Dashboard'},
                    {'id': 'orders', 'icon': 'shopping_cart', 'label': 'Orders'},
                    {'id': 'users', 'icon': 'people', 'label': 'Users'},
                    {'id': 'analytics', 'icon': 'analytics', 'label': 'Analytics'},
                    {'id': 'more', 'icon': 'more_horiz', 'label': 'More'}
                ]
            },
            'header': {
                'height': 56,
                'show_back_button': True,
                'show_menu_button': True,
                'show_search': True
            }
        }
        
        if screen_size == 'small':  # < 480px
            base_layout.update({
                'grid_columns': 1,
                'card_spacing': 8,
                'content_padding': 16,
                'navigation': {
                    'type': 'hamburger_menu',
                    'items': base_layout['navigation']['items']
                }
            })
        elif screen_size == 'medium':  # 480px - 768px
            base_layout.update({
                'grid_columns': 2,
                'card_spacing': 12,
                'content_padding': 20
            })
        else:  # large (tablet)
            base_layout.update({
                'grid_columns': 3,
                'card_spacing': 16,
                'content_padding': 24,
                'navigation': {
                    'type': 'side_drawer',
                    'items': base_layout['navigation']['items']
                }
            })
        
        return base_layout
    
    def optimize_content_for_mobile(self, content: Dict[str, Any], screen_size: str) -> Dict[str, Any]:
        """Optimize content layout for mobile devices."""
        optimized = content.copy()
        
        if screen_size == 'small':
            # Simplify content for small screens
            if 'tables' in optimized:
                for table in optimized['tables']:
                    # Convert tables to card layout
                    table['display_mode'] = 'cards'
                    table['columns_visible'] = min(2, len(table.get('columns', [])))
            
            if 'forms' in optimized:
                for form in optimized['forms']:
                    # Stack form fields vertically
                    form['layout'] = 'vertical'
                    form['field_width'] = 'full'
        
        elif screen_size == 'medium':
            # Moderate optimization for medium screens
            if 'tables' in optimized:
                for table in optimized['tables']:
                    table['columns_visible'] = min(4, len(table.get('columns', [])))
        
        return optimized
    
    def get_mobile_quick_actions(self, user_role: str) -> List[Dict[str, Any]]:
        """Get quick actions optimized for mobile interface."""
        base_actions = [
            {
                'id': 'view_dashboard',
                'title': 'Dashboard',
                'icon': 'dashboard',
                'url': '/admin/dashboard',
                'priority': 1
            },
            {
                'id': 'manage_orders',
                'title': 'Orders',
                'icon': 'shopping_cart',
                'url': '/admin/orders',
                'priority': 2
            },
            {
                'id': 'manage_users',
                'title': 'Users',
                'icon': 'people',
                'url': '/admin/users',
                'priority': 3
            },
            {
                'id': 'view_analytics',
                'title': 'Analytics',
                'icon': 'analytics',
                'url': '/admin/analytics',
                'priority': 4
            }
        ]
        
        if user_role == 'super_admin':
            base_actions.extend([
                {
                    'id': 'system_settings',
                    'title': 'Settings',
                    'icon': 'settings',
                    'url': '/admin/settings',
                    'priority': 5
                },
                {
                    'id': 'system_logs',
                    'title': 'Logs',
                    'icon': 'description',
                    'url': '/admin/logs',
                    'priority': 6
                }
            ])
        
        return sorted(base_actions, key=lambda x: x['priority'])
    
    def validate_mobile_compatibility(self, component_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that a component configuration is mobile-compatible."""
        issues = []
        recommendations = []
        
        # Check touch target sizes
        if 'buttons' in component_config:
            for button in component_config['buttons']:
                size = button.get('size', {})
                min_size = size.get('min_width', 0)
                if min_size < 44:
                    issues.append(f"Button '{button.get('id')}' is too small for touch (minimum 44px)")
                    recommendations.append(f"Increase button size to at least 44px")
        
        # Check text readability
        if 'text' in component_config:
            font_size = component_config['text'].get('font_size', 16)
            if font_size < 14:
                issues.append("Text size is too small for mobile readability")
                recommendations.append("Use minimum 14px font size for mobile")
        
        # Check layout complexity
        if 'layout' in component_config:
            columns = component_config['layout'].get('columns', 1)
            if columns > 2:
                recommendations.append("Consider reducing columns to 1-2 for mobile screens")
        
        return {
            'is_compatible': len(issues) == 0,
            'issues': issues,
            'recommendations': recommendations
        }