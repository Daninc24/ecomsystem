"""
Refund processing service for automated refund and cancellation handling
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from bson import ObjectId

from ..models.order import Order, Refund, RefundStatus, OrderStatus, PaymentStatus
from .base_service import BaseService


class RefundProcessor(BaseService):
    """Service for processing refunds and cancellations automatically."""
    
    def __init__(self, db_client):
        super().__init__(db_client)
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'refunds'
    
    def create_refund_request(self, order_id: ObjectId, refund_data: Dict[str, Any], 
                            user_id: ObjectId) -> Refund:
        """Create a new refund request."""
        # Get the order
        order = self._get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        # Validate refund amount
        refund_amount = refund_data.get('refund_amount', 0.0)
        if refund_amount <= 0 or refund_amount > order.total_amount:
            raise ValueError("Invalid refund amount")
        
        # Create refund
        refund = Refund(
            refund_number=self._generate_refund_number(),
            order_id=order_id,
            customer_id=order.customer_id,
            refund_amount=refund_amount,
            refund_reason=refund_data.get('refund_reason', ''),
            refund_type=refund_data.get('refund_type', 'full'),
            items_to_refund=refund_data.get('items_to_refund', []),
            restore_inventory=refund_data.get('restore_inventory', True),
            created_by=user_id
        )
        
        # Insert into database
        result = self.db.refunds.insert_one(refund.to_dict())
        refund.id = result.inserted_id
        
        return refund
    
    def process_refund(self, refund_id: ObjectId, user_id: ObjectId) -> bool:
        """Process a refund request."""
        refund = self._get_refund(refund_id)
        if not refund:
            return False
        
        if refund.status not in [RefundStatus.REQUESTED, RefundStatus.APPROVED]:
            return False
        
        try:
            # Update refund status to processing
            self._update_refund_status(refund_id, RefundStatus.PROCESSING, user_id)
            
            # Process payment refund
            payment_success = self._process_payment_refund(refund)
            
            if payment_success:
                # Restore inventory if requested
                if refund.restore_inventory:
                    self._restore_inventory(refund)
                
                # Update order status if full refund
                if refund.refund_type == 'full':
                    self._update_order_status(refund.order_id, OrderStatus.REFUNDED, user_id)
                
                # Mark refund as completed
                self._update_refund_status(refund_id, RefundStatus.COMPLETED, user_id)
                
                # Update processed date
                self.db.refunds.update_one(
                    {'_id': refund_id},
                    {'$set': {'processed_date': datetime.utcnow()}}
                )
                
                return True
            else:
                # Mark refund as rejected if payment failed
                self._update_refund_status(refund_id, RefundStatus.REJECTED, user_id)
                return False
                
        except Exception as e:
            # Mark refund as rejected on error
            self._update_refund_status(refund_id, RefundStatus.REJECTED, user_id)
            self.db.refunds.update_one(
                {'_id': refund_id},
                {'$set': {'processor_notes': str(e)}}
            )
            return False
    
    def approve_refund(self, refund_id: ObjectId, user_id: ObjectId) -> bool:
        """Approve a refund request."""
        result = self.db.refunds.update_one(
            {'_id': refund_id, 'status': RefundStatus.REQUESTED.value},
            {
                '$set': {
                    'status': RefundStatus.APPROVED.value,
                    'updated_at': datetime.utcnow(),
                    'updated_by': user_id
                }
            }
        )
        
        return result.modified_count > 0
    
    def reject_refund(self, refund_id: ObjectId, reason: str, user_id: ObjectId) -> bool:
        """Reject a refund request."""
        result = self.db.refunds.update_one(
            {'_id': refund_id, 'status': RefundStatus.REQUESTED.value},
            {
                '$set': {
                    'status': RefundStatus.REJECTED.value,
                    'processor_notes': reason,
                    'updated_at': datetime.utcnow(),
                    'updated_by': user_id
                }
            }
        )
        
        return result.modified_count > 0
    
    def cancel_order(self, order_id: ObjectId, reason: str, user_id: ObjectId) -> bool:
        """Cancel an order and process automatic refund if payment was captured."""
        order = self._get_order(order_id)
        if not order:
            return False
        
        # Check if order can be cancelled
        if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
            return False
        
        try:
            # Update order status to cancelled
            self._update_order_status(order_id, OrderStatus.CANCELLED, user_id)
            
            # If payment was captured, create automatic refund
            if order.payment_status == PaymentStatus.CAPTURED:
                refund_data = {
                    'refund_amount': order.total_amount,
                    'refund_reason': f"Order cancellation: {reason}",
                    'refund_type': 'full',
                    'restore_inventory': True
                }
                
                refund = self.create_refund_request(order_id, refund_data, user_id)
                
                # Auto-approve and process the refund
                self.approve_refund(refund.id, user_id)
                self.process_refund(refund.id, user_id)
            
            # Restore inventory
            self._restore_order_inventory(order)
            
            return True
            
        except Exception:
            return False
    
    def get_refund(self, refund_id: ObjectId) -> Optional[Refund]:
        """Get refund by ID."""
        return self._get_refund(refund_id)
    
    def get_refunds_by_order(self, order_id: ObjectId) -> List[Refund]:
        """Get all refunds for an order."""
        refunds_data = self.db.refunds.find({'order_id': order_id})
        return [Refund.from_dict(refund_data) for refund_data in refunds_data]
    
    def get_refunds_by_status(self, status: RefundStatus, limit: int = 100) -> List[Refund]:
        """Get refunds by status."""
        refunds_data = self.db.refunds.find({'status': status.value}).limit(limit)
        return [Refund.from_dict(refund_data) for refund_data in refunds_data]
    
    def get_pending_refunds(self, limit: int = 50) -> List[Refund]:
        """Get pending refunds that need processing."""
        refunds_data = self.db.refunds.find({
            'status': {'$in': [RefundStatus.REQUESTED.value, RefundStatus.APPROVED.value]}
        }).limit(limit)
        return [Refund.from_dict(refund_data) for refund_data in refunds_data]
    
    def _get_order(self, order_id: ObjectId) -> Optional[Order]:
        """Get order by ID."""
        order_data = self.db.orders.find_one({'_id': order_id})
        if order_data:
            return Order.from_dict(order_data)
        return None
    
    def _get_refund(self, refund_id: ObjectId) -> Optional[Refund]:
        """Get refund by ID."""
        refund_data = self.db.refunds.find_one({'_id': refund_id})
        if refund_data:
            return Refund.from_dict(refund_data)
        return None
    
    def _update_refund_status(self, refund_id: ObjectId, status: RefundStatus, user_id: ObjectId) -> bool:
        """Update refund status."""
        result = self.db.refunds.update_one(
            {'_id': refund_id},
            {
                '$set': {
                    'status': status.value,
                    'updated_at': datetime.utcnow(),
                    'updated_by': user_id
                }
            }
        )
        return result.modified_count > 0
    
    def _update_order_status(self, order_id: ObjectId, status: OrderStatus, user_id: ObjectId) -> bool:
        """Update order status."""
        result = self.db.orders.update_one(
            {'_id': order_id},
            {
                '$set': {
                    'status': status.value,
                    'updated_at': datetime.utcnow(),
                    'updated_by': user_id
                }
            }
        )
        return result.modified_count > 0
    
    def _process_payment_refund(self, refund: Refund) -> bool:
        """Process payment refund through payment gateway."""
        # This would integrate with actual payment processors
        # For now, simulate successful refund processing
        return True
    
    def _restore_inventory(self, refund: Refund) -> bool:
        """Restore inventory for refunded items."""
        if not refund.items_to_refund:
            return True
        
        try:
            for item in refund.items_to_refund:
                product_id = item.get('product_id')
                quantity = item.get('quantity', 0)
                
                if product_id and quantity > 0:
                    # Update product inventory
                    self.db.products.update_one(
                        {'_id': ObjectId(product_id)},
                        {'$inc': {'inventory_count': quantity}}
                    )
            
            # Mark inventory as restored
            self.db.refunds.update_one(
                {'_id': refund.id},
                {'$set': {'inventory_restored': True}}
            )
            
            return True
        except Exception:
            return False
    
    def _restore_order_inventory(self, order: Order) -> bool:
        """Restore inventory for cancelled order."""
        try:
            for item in order.items:
                product_id = item.get('product_id')
                quantity = item.get('quantity', 0)
                
                if product_id and quantity > 0:
                    # Update product inventory
                    self.db.products.update_one(
                        {'_id': ObjectId(product_id)},
                        {'$inc': {'inventory_count': quantity}}
                    )
            
            return True
        except Exception:
            return False
    
    def _generate_refund_number(self) -> str:
        """Generate unique refund number."""
        now = datetime.utcnow()
        date_str = now.strftime('%Y%m%d')
        
        # Get count of refunds today
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        daily_count = self.db.refunds.count_documents({
            'created_at': {'$gte': start_of_day, '$lt': end_of_day}
        })
        
        # Generate refund number: REF-YYYYMMDD-NNNN
        return f"REF-{date_str}-{daily_count + 1:04d}"