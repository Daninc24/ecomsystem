"""
Analytics API endpoints for Dynamic Admin System
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models_sqlite import User, Product, Order, ActivityLog, db
from datetime import datetime, timezone, timedelta
import functools

analytics_bp = Blueprint('analytics_api', __name__, url_prefix='/analytics')


def admin_required(f):
    """Decorator to require admin role."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_role('admin'):
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403
        return f(*args, **kwargs)
    return decorated_function


@analytics_bp.route('/', methods=['GET'])
def analytics_info():
    """Get analytics API information."""
    return jsonify({
        'success': True,
        'data': {
            'name': 'Analytics API',
            'version': '2.0.0',
            'endpoints': {
                'dashboard': '/api/admin/analytics/dashboard',
                'users': '/api/admin/analytics/users',
                'products': '/api/admin/analytics/products',
                'orders': '/api/admin/analytics/orders',
                'activity': '/api/admin/analytics/activity',
                'export': '/api/admin/analytics/export'
            }
        }
    })


@analytics_bp.route('/dashboard-metrics', methods=['GET'])
@login_required
@admin_required
def get_dashboard_metrics():
    """Get dashboard metrics for real-time updates."""
    try:
        from models_sqlite import User, Product, Order
        
        # Get basic metrics
        total_users = User.query.count()
        total_products = Product.query.count()
        total_orders = Order.query.count()
        
        # Calculate revenue (placeholder)
        total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
        
        return jsonify({
            'success': True,
            'data': {
                'users': total_users,
                'products': total_products,
                'orders': total_orders,
                'revenue': float(total_revenue),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/dashboard', methods=['GET'])
@login_required
@admin_required
def get_dashboard_analytics():
    """Get dashboard analytics data."""
    try:
        # Get date range
        days = request.args.get('days', 30, type=int)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Basic counts
        total_users = User.query.count()
        total_products = Product.query.count()
        total_orders = Order.query.count()
        
        # Recent activity
        new_users = User.query.filter(User.created_at >= start_date).count()
        new_orders = Order.query.filter(Order.created_at >= start_date).count()
        
        # Revenue calculation (if orders have total_amount)
        revenue_query = db.session.query(db.func.sum(Order.total_amount)).filter(
            Order.created_at >= start_date,
            Order.status.in_(['completed', 'shipped', 'delivered'])
        ).scalar()
        total_revenue = float(revenue_query) if revenue_query else 0.0
        
        # Active users (logged in within last 7 days)
        active_cutoff = end_date - timedelta(days=7)
        active_users = User.query.filter(
            User.last_login >= active_cutoff,
            User.is_active == True
        ).count()
        
        # Top products by orders
        top_products = db.session.query(
            Product.name,
            db.func.count(Order.id).label('order_count')
        ).join(Order.items).join(Product).group_by(Product.id).order_by(
            db.func.count(Order.id).desc()
        ).limit(5).all()
        
        return jsonify({
            'success': True,
            'data': {
                'overview': {
                    'total_users': total_users,
                    'total_products': total_products,
                    'total_orders': total_orders,
                    'total_revenue': total_revenue,
                    'active_users': active_users
                },
                'recent_activity': {
                    'new_users': new_users,
                    'new_orders': new_orders,
                    'period_days': days
                },
                'top_products': [
                    {'name': name, 'order_count': count} 
                    for name, count in top_products
                ],
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/users', methods=['GET'])
@login_required
@admin_required
def get_user_analytics():
    """Get user analytics data."""
    try:
        # Get user statistics
        user_manager = current_app.user_manager
        stats = user_manager.get_user_statistics()
        
        # User registration trend (last 30 days)
        registration_trend = []
        for i in range(30):
            date = datetime.now(timezone.utc) - timedelta(days=i)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            count = User.query.filter(
                User.created_at >= start_of_day,
                User.created_at < end_of_day
            ).count()
            
            registration_trend.append({
                'date': start_of_day.strftime('%Y-%m-%d'),
                'count': count
            })
        
        registration_trend.reverse()  # Oldest first
        
        return jsonify({
            'success': True,
            'data': {
                'statistics': stats,
                'registration_trend': registration_trend
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/products', methods=['GET'])
@login_required
@admin_required
def get_product_analytics():
    """Get product analytics data."""
    try:
        # Product statistics
        total_products = Product.query.count()
        active_products = Product.query.filter_by(is_active=True).count()
        featured_products = Product.query.filter_by(is_featured=True).count()
        out_of_stock = Product.query.filter_by(inventory_quantity=0).count()
        
        # Products by category
        category_stats = db.session.query(
            db.func.count(Product.id).label('count')
        ).join(Product.categories).group_by('category.name').all()
        
        # Price distribution
        price_ranges = [
            ('$0-$25', 0, 25),
            ('$25-$50', 25, 50),
            ('$50-$100', 50, 100),
            ('$100-$250', 100, 250),
            ('$250+', 250, float('inf'))
        ]
        
        price_distribution = []
        for label, min_price, max_price in price_ranges:
            if max_price == float('inf'):
                count = Product.query.filter(Product.price >= min_price).count()
            else:
                count = Product.query.filter(
                    Product.price >= min_price,
                    Product.price < max_price
                ).count()
            price_distribution.append({'range': label, 'count': count})
        
        return jsonify({
            'success': True,
            'data': {
                'overview': {
                    'total_products': total_products,
                    'active_products': active_products,
                    'featured_products': featured_products,
                    'out_of_stock': out_of_stock
                },
                'price_distribution': price_distribution
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/orders', methods=['GET'])
@login_required
@admin_required
def get_order_analytics():
    """Get order analytics data."""
    try:
        # Order statistics
        total_orders = Order.query.count()
        pending_orders = Order.query.filter_by(status='pending').count()
        completed_orders = Order.query.filter_by(status='completed').count()
        
        # Revenue by status
        revenue_by_status = db.session.query(
            Order.status,
            db.func.sum(Order.total_amount).label('revenue'),
            db.func.count(Order.id).label('count')
        ).group_by(Order.status).all()
        
        # Orders trend (last 30 days)
        orders_trend = []
        for i in range(30):
            date = datetime.now(timezone.utc) - timedelta(days=i)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            count = Order.query.filter(
                Order.created_at >= start_of_day,
                Order.created_at < end_of_day
            ).count()
            
            revenue = db.session.query(db.func.sum(Order.total_amount)).filter(
                Order.created_at >= start_of_day,
                Order.created_at < end_of_day
            ).scalar() or 0
            
            orders_trend.append({
                'date': start_of_day.strftime('%Y-%m-%d'),
                'orders': count,
                'revenue': float(revenue)
            })
        
        orders_trend.reverse()  # Oldest first
        
        return jsonify({
            'success': True,
            'data': {
                'overview': {
                    'total_orders': total_orders,
                    'pending_orders': pending_orders,
                    'completed_orders': completed_orders
                },
                'revenue_by_status': [
                    {
                        'status': status,
                        'revenue': float(revenue) if revenue else 0,
                        'count': count
                    }
                    for status, revenue, count in revenue_by_status
                ],
                'orders_trend': orders_trend
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/activity', methods=['GET'])
@login_required
@admin_required
def get_activity_analytics():
    """Get system activity analytics."""
    try:
        days = request.args.get('days', 7, type=int)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Activity by action type
        activity_by_action = db.session.query(
            ActivityLog.action,
            db.func.count(ActivityLog.id).label('count')
        ).filter(
            ActivityLog.created_at >= start_date
        ).group_by(ActivityLog.action).order_by(
            db.func.count(ActivityLog.id).desc()
        ).limit(10).all()
        
        # Activity trend
        activity_trend = []
        for i in range(days):
            date = end_date - timedelta(days=i)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            count = ActivityLog.query.filter(
                ActivityLog.created_at >= start_of_day,
                ActivityLog.created_at < end_of_day
            ).count()
            
            activity_trend.append({
                'date': start_of_day.strftime('%Y-%m-%d'),
                'count': count
            })
        
        activity_trend.reverse()  # Oldest first
        
        # Recent activity
        recent_activity = ActivityLog.query.order_by(
            ActivityLog.created_at.desc()
        ).limit(20).all()
        
        return jsonify({
            'success': True,
            'data': {
                'activity_by_action': [
                    {'action': action, 'count': count}
                    for action, count in activity_by_action
                ],
                'activity_trend': activity_trend,
                'recent_activity': [
                    {
                        'id': activity.id,
                        'action': activity.action,
                        'resource_type': activity.resource_type,
                        'user_id': activity.user_id,
                        'success': activity.success,
                        'created_at': activity.created_at.isoformat()
                    }
                    for activity in recent_activity
                ]
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/export', methods=['GET'])
@login_required
@admin_required
def export_analytics():
    """Export analytics data."""
    try:
        export_type = request.args.get('type', 'dashboard')
        format_type = request.args.get('format', 'json')
        
        if export_type == 'dashboard':
            # Get dashboard data
            response = get_dashboard_analytics()
            data = response.get_json()
        elif export_type == 'users':
            response = get_user_analytics()
            data = response.get_json()
        elif export_type == 'products':
            response = get_product_analytics()
            data = response.get_json()
        elif export_type == 'orders':
            response = get_order_analytics()
            data = response.get_json()
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid export type'
            }), 400
        
        if format_type == 'csv':
            # Convert to CSV format (simplified)
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers and data based on export type
            if export_type == 'dashboard':
                writer.writerow(['Metric', 'Value'])
                overview = data['data']['overview']
                for key, value in overview.items():
                    writer.writerow([key.replace('_', ' ').title(), value])
            
            csv_data = output.getvalue()
            output.close()
            
            return jsonify({
                'success': True,
                'data': csv_data,
                'format': 'csv'
            })
        else:
            return jsonify({
                'success': True,
                'data': data['data'],
                'format': 'json'
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500