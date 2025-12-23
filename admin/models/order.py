"""
Order and transaction management models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from bson import ObjectId
from .base import BaseModel


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class RefundStatus(Enum):
    """Refund status enumeration."""
    REQUESTED = "requested"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"


class DisputeStatus(Enum):
    """Dispute status enumeration."""
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"


class ShippingStatus(Enum):
    """Shipping status enumeration."""
    PENDING = "pending"
    LABEL_CREATED = "label_created"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    EXCEPTION = "exception"
    RETURNED = "returned"


class Order(BaseModel):
    """Order model for managing customer orders."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.order_number: str = kwargs.get('order_number', '')
        self.customer_id: ObjectId = kwargs.get('customer_id')
        self.vendor_id: Optional[ObjectId] = kwargs.get('vendor_id')
        
        # Handle enum conversion safely
        status_value = kwargs.get('status', OrderStatus.PENDING.value)
        if isinstance(status_value, OrderStatus):
            self.status = status_value
        else:
            # Handle string values that might include enum class name
            if isinstance(status_value, str) and '.' in status_value:
                status_value = status_value.split('.')[-1].lower()
            self.status = OrderStatus(status_value)
        
        payment_status_value = kwargs.get('payment_status', PaymentStatus.PENDING.value)
        if isinstance(payment_status_value, PaymentStatus):
            self.payment_status = payment_status_value
        else:
            if isinstance(payment_status_value, str) and '.' in payment_status_value:
                payment_status_value = payment_status_value.split('.')[-1].lower()
            self.payment_status = PaymentStatus(payment_status_value)
        
        shipping_status_value = kwargs.get('shipping_status', ShippingStatus.PENDING.value)
        if isinstance(shipping_status_value, ShippingStatus):
            self.shipping_status = shipping_status_value
        else:
            if isinstance(shipping_status_value, str) and '.' in shipping_status_value:
                shipping_status_value = shipping_status_value.split('.')[-1].lower()
            self.shipping_status = ShippingStatus(shipping_status_value)
        
        # Order details
        self.items: List[Dict[str, Any]] = kwargs.get('items', [])
        self.subtotal: float = kwargs.get('subtotal', 0.0)
        self.tax_amount: float = kwargs.get('tax_amount', 0.0)
        self.shipping_amount: float = kwargs.get('shipping_amount', 0.0)
        self.discount_amount: float = kwargs.get('discount_amount', 0.0)
        self.total_amount: float = kwargs.get('total_amount', 0.0)
        
        # Addresses
        self.billing_address: Dict[str, Any] = kwargs.get('billing_address', {})
        self.shipping_address: Dict[str, Any] = kwargs.get('shipping_address', {})
        
        # Payment information
        self.payment_method: str = kwargs.get('payment_method', '')
        self.payment_reference: str = kwargs.get('payment_reference', '')
        
        # Shipping information
        self.shipping_method: str = kwargs.get('shipping_method', '')
        self.tracking_number: Optional[str] = kwargs.get('tracking_number')
        self.carrier: Optional[str] = kwargs.get('carrier')
        
        # Timestamps
        self.order_date: datetime = kwargs.get('order_date', datetime.utcnow())
        self.shipped_date: Optional[datetime] = kwargs.get('shipped_date')
        self.delivered_date: Optional[datetime] = kwargs.get('delivered_date')
        
        # Notes and metadata
        self.notes: str = kwargs.get('notes', '')
        self.metadata: Dict[str, Any] = kwargs.get('metadata', {})


class Refund(BaseModel):
    """Refund model for managing order refunds."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.refund_number: str = kwargs.get('refund_number', '')
        self.order_id: ObjectId = kwargs.get('order_id')
        self.customer_id: ObjectId = kwargs.get('customer_id')
        
        # Handle enum conversion safely
        status_value = kwargs.get('status', RefundStatus.REQUESTED.value)
        if isinstance(status_value, RefundStatus):
            self.status = status_value
        else:
            if isinstance(status_value, str) and '.' in status_value:
                status_value = status_value.split('.')[-1].lower()
            self.status = RefundStatus(status_value)
        
        # Refund details
        self.refund_amount: float = kwargs.get('refund_amount', 0.0)
        self.refund_reason: str = kwargs.get('refund_reason', '')
        self.refund_type: str = kwargs.get('refund_type', 'full')  # full, partial
        self.items_to_refund: List[Dict[str, Any]] = kwargs.get('items_to_refund', [])
        
        # Processing information
        self.processed_date: Optional[datetime] = kwargs.get('processed_date')
        self.payment_reference: str = kwargs.get('payment_reference', '')
        self.processor_notes: str = kwargs.get('processor_notes', '')
        
        # Inventory impact
        self.restore_inventory: bool = kwargs.get('restore_inventory', True)
        self.inventory_restored: bool = kwargs.get('inventory_restored', False)


class Dispute(BaseModel):
    """Dispute model for managing order disputes."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dispute_number: str = kwargs.get('dispute_number', '')
        self.order_id: ObjectId = kwargs.get('order_id')
        self.customer_id: ObjectId = kwargs.get('customer_id')
        self.vendor_id: Optional[ObjectId] = kwargs.get('vendor_id')
        
        # Handle enum conversion safely
        status_value = kwargs.get('status', DisputeStatus.OPEN.value)
        if isinstance(status_value, DisputeStatus):
            self.status = status_value
        else:
            if isinstance(status_value, str) and '.' in status_value:
                status_value = status_value.split('.')[-1].lower()
            self.status = DisputeStatus(status_value)
        
        # Dispute details
        self.dispute_type: str = kwargs.get('dispute_type', '')  # quality, shipping, refund, etc.
        self.subject: str = kwargs.get('subject', '')
        self.description: str = kwargs.get('description', '')
        self.disputed_amount: float = kwargs.get('disputed_amount', 0.0)
        
        # Resolution information
        self.resolution: str = kwargs.get('resolution', '')
        self.resolution_amount: float = kwargs.get('resolution_amount', 0.0)
        self.resolved_date: Optional[datetime] = kwargs.get('resolved_date')
        self.resolved_by: Optional[ObjectId] = kwargs.get('resolved_by')
        
        # Communication
        self.messages: List[Dict[str, Any]] = kwargs.get('messages', [])
        self.attachments: List[Dict[str, Any]] = kwargs.get('attachments', [])


class ShippingIntegration(BaseModel):
    """Shipping integration model for managing shipping providers."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.provider_name: str = kwargs.get('provider_name', '')
        self.provider_code: str = kwargs.get('provider_code', '')
        self.api_endpoint: str = kwargs.get('api_endpoint', '')
        self.api_key: str = kwargs.get('api_key', '')
        self.api_secret: str = kwargs.get('api_secret', '')
        
        # Configuration
        self.is_active: bool = kwargs.get('is_active', True)
        self.is_test_mode: bool = kwargs.get('is_test_mode', False)
        self.supported_services: List[str] = kwargs.get('supported_services', [])
        self.rate_calculation_enabled: bool = kwargs.get('rate_calculation_enabled', True)
        self.tracking_enabled: bool = kwargs.get('tracking_enabled', True)
        
        # Settings
        self.default_service: str = kwargs.get('default_service', '')
        self.packaging_type: str = kwargs.get('packaging_type', '')
        self.insurance_enabled: bool = kwargs.get('insurance_enabled', False)
        self.signature_required: bool = kwargs.get('signature_required', False)


class FinancialReport(BaseModel):
    """Financial report model for analytics and reporting."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.report_name: str = kwargs.get('report_name', '')
        self.report_type: str = kwargs.get('report_type', '')  # sales, refunds, taxes, etc.
        self.period_start: datetime = kwargs.get('period_start')
        self.period_end: datetime = kwargs.get('period_end')
        
        # Report data
        self.total_orders: int = kwargs.get('total_orders', 0)
        self.total_revenue: float = kwargs.get('total_revenue', 0.0)
        self.total_refunds: float = kwargs.get('total_refunds', 0.0)
        self.total_taxes: float = kwargs.get('total_taxes', 0.0)
        self.total_shipping: float = kwargs.get('total_shipping', 0.0)
        self.net_revenue: float = kwargs.get('net_revenue', 0.0)
        
        # Breakdown data
        self.revenue_by_category: Dict[str, float] = kwargs.get('revenue_by_category', {})
        self.revenue_by_vendor: Dict[str, float] = kwargs.get('revenue_by_vendor', {})
        self.orders_by_status: Dict[str, int] = kwargs.get('orders_by_status', {})
        
        # Export information
        self.export_format: str = kwargs.get('export_format', 'json')
        self.export_path: Optional[str] = kwargs.get('export_path')
        self.generated_by: ObjectId = kwargs.get('generated_by')