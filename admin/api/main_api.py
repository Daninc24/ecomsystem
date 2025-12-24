"""
Main Admin API Router - Advanced SQLite Version
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from .configuration_api import configuration_bp
from .user_api_sqlite import user_bp
from .theme_api import theme_bp
from .content_api import content_bp
from .analytics_api import analytics_bp
from .product_api import product_bp
from .order_api import order_bp
from .system_api_simple import system_bp

# Main admin API blueprint
admin_api = Blueprint('admin_api', __name__, url_prefix='/api/admin')


@admin_api.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint."""
    return jsonify({
        'success': True,
        'data': {
            'status': 'healthy',
            'version': '2.0.0',
            'timestamp': datetime.now().isoformat(),
            'database': 'SQLite',
            'features': [
                'configuration_management',
                'user_management',
                'theme_management',
                'content_management',
                'analytics',
                'real_time_updates'
            ]
        }
    })


@admin_api.route('/info', methods=['GET'])
def api_info():
    """Get API information and available endpoints."""
    return jsonify({
        'success': True,
        'data': {
            'name': 'Dynamic Admin System API',
            'version': '2.0.0',
            'description': 'Advanced Admin API for MarketHub Pro with SQLite',
            'endpoints': {
                'configuration': '/api/admin/configuration',
                'users': '/api/admin/users',
                'theme': '/api/admin/theme',
                'content': '/api/admin/content',
                'analytics': '/api/admin/analytics',
                'health': '/api/admin/health',
                'info': '/api/admin/info'
            },
            'database': 'SQLite',
            'features': {
                'real_time_configuration': True,
                'user_management': True,
                'theme_customization': True,
                'content_versioning': True,
                'analytics_dashboard': True,
                'audit_logging': True,
                'role_based_access': True
            }
        }
    })


@admin_api.route('/status', methods=['GET'])
def system_status():
    """Get system status information."""
    try:
        from models_sqlite import User, Product, Order, AdminSetting
        
        # Get basic counts
        user_count = User.query.count()
        product_count = Product.query.count()
        order_count = Order.query.count()
        setting_count = AdminSetting.query.count()
        
        # Check database connectivity
        try:
            AdminSetting.query.first()
            db_status = 'connected'
        except Exception:
            db_status = 'error'
        
        return jsonify({
            'success': True,
            'data': {
                'system': {
                    'status': 'operational',
                    'database': db_status,
                    'timestamp': datetime.now().isoformat()
                },
                'statistics': {
                    'users': user_count,
                    'products': product_count,
                    'orders': order_count,
                    'settings': setting_count
                },
                'services': {
                    'configuration_manager': True,
                    'user_manager': True,
                    'theme_manager': True,
                    'content_manager': True
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {
                'system': {
                    'status': 'error',
                    'database': 'error',
                    'timestamp': datetime.now().isoformat()
                }
            }
        }), 500


@admin_api.route('/widgets/<widget_type>/<widget_id>', methods=['GET'])
def get_widget_data(widget_type, widget_id):
    """Get widget data for dashboard."""
    try:
        from models_sqlite import User, Product, Order
        
        if widget_type == 'stats' and widget_id == 'stats':
            # Basic statistics widget
            return jsonify({
                'success': True,
                'data': {
                    'total_users': User.query.count(),
                    'total_products': Product.query.count(),
                    'total_orders': Order.query.count(),
                    'active_products': Product.query.filter_by(is_active=True).count()
                }
            })
        
        elif widget_type == 'chart' and widget_id == 'analytics_chart':
            # Simple analytics chart data
            return jsonify({
                'success': True,
                'data': {
                    'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    'datasets': [{
                        'label': 'Orders',
                        'data': [12, 19, 3, 5, 2, 3],
                        'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                        'borderColor': 'rgba(54, 162, 235, 1)'
                    }]
                }
            })
        
        elif widget_type == 'orders' and widget_id == 'recent_orders':
            # Recent orders widget
            recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
            return jsonify({
                'success': True,
                'data': {
                    'orders': [{
                        'id': order.id,
                        'total': float(order.total_amount),
                        'status': order.status,
                        'created_at': order.created_at.isoformat()
                    } for order in recent_orders]
                }
            })
        
        else:
            return jsonify({
                'success': False,
                'error': 'Widget not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Register all API blueprints
admin_api.register_blueprint(configuration_bp)
admin_api.register_blueprint(user_bp)
admin_api.register_blueprint(theme_bp)
admin_api.register_blueprint(content_bp)
admin_api.register_blueprint(analytics_bp)
admin_api.register_blueprint(product_bp)
admin_api.register_blueprint(order_bp)
admin_api.register_blueprint(system_bp)