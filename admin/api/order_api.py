"""
Order Management API endpoints for Dynamic Admin System
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models_sqlite import Order, OrderItem, User, db
import functools

order_bp = Blueprint('order_api', __name__, url_prefix='/orders')


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


@order_bp.route('/info', methods=['GET'])
def order_info():
    """Get order API information."""
    return jsonify({
        'success': True,
        'data': {
            'name': 'Order Management API',
            'version': '2.0.0',
            'endpoints': {
                'list': '/api/admin/orders',
                'details': '/api/admin/orders/<id>',
                'refund': '/api/admin/orders/<id>/refund (POST)',
                'shipping_label': '/api/admin/orders/<id>/shipping-label'
            }
        }
    })


@order_bp.route('/', methods=['GET'])
@login_required
@admin_required
def get_orders():
    """Get all orders."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        orders = Order.query.order_by(Order.created_at.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        orders_data = []
        for order in orders.items:
            order_dict = order.to_dict()
            # Add customer info
            if order.user:
                order_dict['customer_name'] = order.user.get_full_name()
                order_dict['customer_email'] = order.user.email
            else:
                order_dict['customer_name'] = 'Guest'
                order_dict['customer_email'] = 'N/A'
            
            # Add shipping address
            shipping_addr = order.get_shipping_address()
            order_dict['shipping_address'] = shipping_addr
            
            # Add tracking number (placeholder)
            order_dict['tracking_number'] = None
            
            orders_data.append(order_dict)
        
        return jsonify({
            'success': True,
            'data': {
                'orders': orders_data,
                'pagination': {
                    'current_page': orders.page,
                    'total_pages': orders.pages,
                    'total_items': orders.total,
                    'has_next': orders.has_next,
                    'has_prev': orders.has_prev
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@order_bp.route('/<int:order_id>', methods=['GET'])
@login_required
@admin_required
def get_order_details(order_id):
    """Get order details."""
    try:
        order = Order.query.get_or_404(order_id)
        
        order_dict = order.to_dict()
        # Add customer info
        if order.user:
            order_dict['customer'] = {
                'id': order.user.id,
                'name': order.user.get_full_name(),
                'email': order.user.email,
                'phone': order.user.phone
            }
        
        return jsonify({
            'success': True,
            'data': {
                'order': order_dict
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@order_bp.route('/<int:order_id>/refund', methods=['POST'])
@login_required
@admin_required
def process_refund(order_id):
    """Process order refund."""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Update order status
        order.status = 'refunded'
        order.payment_status = 'refunded'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Refund processed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@order_bp.route('/<int:order_id>/shipping-label', methods=['GET'])
@login_required
@admin_required
def get_shipping_label(order_id):
    """Get shipping label for order."""
    try:
        order = Order.query.get_or_404(order_id)
        
        # For now, return a placeholder response
        # In a real implementation, you'd generate a PDF label
        
        return jsonify({
            'success': True,
            'message': 'Shipping label functionality not implemented yet'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500