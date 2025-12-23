"""
Order management service for handling order operations and real-time dashboard
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from bson import ObjectId

from ..models.order import Order, OrderStatus, PaymentStatus, ShippingStatus
from ..models.base import BaseModel
from .base_service import BaseService


class OrderManager(BaseService):
    """Service for managing orders with real-time dashboard capabilities."""
    
    def __init__(self, db_client):
        super().__init__(db_client)
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'orders'
    
    def create_order(self, order_data: Dict[str, Any], user_id: ObjectId) -> Order:
        """Create a new order."""
        order = Order(**order_data)
        order.created_by = user_id
        order.order_number = self._generate_order_number()
        
        # Calculate totals
        order.total_amount = (
            order.subtotal + 
            order.tax_amount + 
            order.shipping_amount - 
            order.discount_amount
        )
        
        # Insert into database
        result = self.db.orders.insert_one(order.to_dict())
        order.id = result.inserted_id
        
        return order
    
    def get_order(self, order_id: ObjectId) -> Optional[Order]:
        """Get order by ID."""
        order_data = self.db.orders.find_one({'_id': order_id})
        if order_data:
            return Order.from_dict(order_data)
        return None
    
    def get_order_by_number(self, order_number: str) -> Optional[Order]:
        """Get order by order number."""
        order_data = self.db.orders.find_one({'order_number': order_number})
        if order_data:
            return Order.from_dict(order_data)
        return None
    
    def update_order_status(self, order_id: ObjectId, status: OrderStatus, user_id: ObjectId) -> bool:
        """Update order status."""
        update_data = {
            'status': status.value,
            'updated_at': datetime.utcnow(),
            'updated_by': user_id
        }
        
        # Add status-specific timestamps
        if status == OrderStatus.SHIPPED:
            update_data['shipped_date'] = datetime.utcnow()
        elif status == OrderStatus.DELIVERED:
            update_data['delivered_date'] = datetime.utcnow()
        
        result = self.db.orders.update_one(
            {'_id': order_id},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    def update_payment_status(self, order_id: ObjectId, payment_status: PaymentStatus, 
                            payment_reference: str = '', user_id: ObjectId = None) -> bool:
        """Update payment status."""
        update_data = {
            'payment_status': payment_status.value,
            'updated_at': datetime.utcnow()
        }
        
        if payment_reference:
            update_data['payment_reference'] = payment_reference
        
        if user_id:
            update_data['updated_by'] = user_id
        
        result = self.db.orders.update_one(
            {'_id': order_id},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    def update_shipping_status(self, order_id: ObjectId, shipping_status: ShippingStatus,
                             tracking_number: str = '', carrier: str = '', user_id: ObjectId = None) -> bool:
        """Update shipping status."""
        update_data = {
            'shipping_status': shipping_status.value,
            'updated_at': datetime.utcnow()
        }
        
        if tracking_number:
            update_data['tracking_number'] = tracking_number
        
        if carrier:
            update_data['carrier'] = carrier
        
        if user_id:
            update_data['updated_by'] = user_id
        
        result = self.db.orders.update_one(
            {'_id': order_id},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    def get_orders_by_status(self, status: OrderStatus, limit: int = 100) -> List[Order]:
        """Get orders by status."""
        orders_data = self.db.orders.find({'status': status.value}).limit(limit)
        return [Order.from_dict(order_data) for order_data in orders_data]
    
    def get_orders_by_customer(self, customer_id: ObjectId, limit: int = 50) -> List[Order]:
        """Get orders by customer."""
        orders_data = self.db.orders.find({'customer_id': customer_id}).limit(limit)
        return [Order.from_dict(order_data) for order_data in orders_data]
    
    def get_orders_by_vendor(self, vendor_id: ObjectId, limit: int = 100) -> List[Order]:
        """Get orders by vendor."""
        orders_data = self.db.orders.find({'vendor_id': vendor_id}).limit(limit)
        return [Order.from_dict(order_data) for order_data in orders_data]
    
    def get_dashboard_metrics(self, period_days: int = 30) -> Dict[str, Any]:
        """Get real-time dashboard metrics."""
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Aggregate pipeline for metrics
        pipeline = [
            {'$match': {'created_at': {'$gte': start_date}}},
            {'$group': {
                '_id': None,
                'total_orders': {'$sum': 1},
                'total_revenue': {'$sum': '$total_amount'},
                'avg_order_value': {'$avg': '$total_amount'},
                'orders_by_status': {
                    '$push': {
                        'status': '$status',
                        'amount': '$total_amount'
                    }
                }
            }}
        ]
        
        result = list(self.db.orders.aggregate(pipeline))
        
        if not result:
            return {
                'total_orders': 0,
                'total_revenue': 0.0,
                'avg_order_value': 0.0,
                'orders_by_status': {},
                'recent_orders': []
            }
        
        metrics = result[0]
        
        # Process orders by status
        status_counts = {}
        for order in metrics.get('orders_by_status', []):
            status = order['status']
            if status not in status_counts:
                status_counts[status] = {'count': 0, 'revenue': 0.0}
            status_counts[status]['count'] += 1
            status_counts[status]['revenue'] += order['amount']
        
        # Get recent orders
        recent_orders = list(self.db.orders.find().sort('created_at', -1).limit(10))
        
        return {
            'total_orders': metrics.get('total_orders', 0),
            'total_revenue': metrics.get('total_revenue', 0.0),
            'avg_order_value': metrics.get('avg_order_value', 0.0),
            'orders_by_status': status_counts,
            'recent_orders': [Order.from_dict(order) for order in recent_orders]
        }
    
    def search_orders(self, query: str, filters: Dict[str, Any] = None, limit: int = 50) -> List[Order]:
        """Search orders by various criteria."""
        search_filter = {}
        
        # Add text search
        if query:
            search_filter['$or'] = [
                {'order_number': {'$regex': query, '$options': 'i'}},
                {'customer_email': {'$regex': query, '$options': 'i'}},
                {'tracking_number': {'$regex': query, '$options': 'i'}}
            ]
        
        # Add additional filters
        if filters:
            if 'status' in filters:
                search_filter['status'] = filters['status']
            if 'payment_status' in filters:
                search_filter['payment_status'] = filters['payment_status']
            if 'date_from' in filters:
                search_filter['created_at'] = {'$gte': filters['date_from']}
            if 'date_to' in filters:
                if 'created_at' not in search_filter:
                    search_filter['created_at'] = {}
                search_filter['created_at']['$lte'] = filters['date_to']
        
        orders_data = self.db.orders.find(search_filter).limit(limit)
        return [Order.from_dict(order_data) for order_data in orders_data]
    
    def _generate_order_number(self) -> str:
        """Generate unique order number."""
        # Get current date
        now = datetime.utcnow()
        date_str = now.strftime('%Y%m%d')
        
        # Get count of orders today
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        daily_count = self.db.orders.count_documents({
            'created_at': {'$gte': start_of_day, '$lt': end_of_day}
        })
        
        # Generate order number: YYYYMMDD-NNNN
        return f"{date_str}-{daily_count + 1:04d}"