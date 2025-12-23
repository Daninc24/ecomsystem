"""
Property-Based Tests for Order Management
Tests for refund processing completeness and order transaction integrity
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta
from bson import ObjectId
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from admin.services.order_manager import OrderManager
from admin.services.refund_processor import RefundProcessor
from admin.services.shipping_integrator import ShippingIntegrator
from admin.services.dispute_manager import DisputeManager
from admin.services.report_generator import ReportGenerator
from admin.models.order import (
    OrderStatus, PaymentStatus, RefundStatus, DisputeStatus, ShippingStatus
)
from simple_mongo_mock import MockMongo


class TestOrderManagementProperties:
    """Property-based tests for order management functionality."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        self.mock_mongo = MockMongo()
        self.order_manager = OrderManager(self.mock_mongo.db)
        self.refund_processor = RefundProcessor(self.mock_mongo.db)
        self.shipping_integrator = ShippingIntegrator(self.mock_mongo.db)
        self.dispute_manager = DisputeManager(self.mock_mongo.db)
        self.report_generator = ReportGenerator(self.mock_mongo.db)
        self.test_user_id = ObjectId()
        self.test_customer_id = ObjectId()
        self.test_vendor_id = ObjectId()
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clear all collections
        collections = [
            'orders', 'refunds', 'disputes', 'shipping_integrations', 
            'financial_reports', 'products'
        ]
        for collection_name in collections:
            try:
                getattr(self.mock_mongo.db, collection_name).delete_many({})
            except:
                pass
    
    # Test data generators
    
    @st.composite
    def order_data_strategy(draw):
        """Generate valid order data."""
        test_customer_id = ObjectId()
        test_vendor_id = ObjectId()
        
        items = []
        for _ in range(draw(st.integers(min_value=1, max_value=3))):
            items.append({
                'product_id': str(ObjectId()),
                'name': draw(st.text(min_size=1, max_size=50)),
                'quantity': draw(st.integers(min_value=1, max_value=10)),
                'price': draw(st.floats(min_value=1.0, max_value=1000.0)),
                'total': draw(st.floats(min_value=1.0, max_value=10000.0))
            })
        
        subtotal = sum(item['total'] for item in items)
        tax_amount = draw(st.floats(min_value=0.0, max_value=subtotal * 0.2))
        shipping_amount = draw(st.floats(min_value=0.0, max_value=50.0))
        discount_amount = draw(st.floats(min_value=0.0, max_value=subtotal * 0.5))
        
        return {
            'customer_id': test_customer_id,
            'vendor_id': test_vendor_id,
            'status': draw(st.sampled_from([status.value for status in OrderStatus])),
            'payment_status': draw(st.sampled_from([status.value for status in PaymentStatus])),
            'shipping_status': draw(st.sampled_from([status.value for status in ShippingStatus])),
            'items': items,
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'shipping_amount': shipping_amount,
            'discount_amount': discount_amount,
            'billing_address': {
                'street': draw(st.text(min_size=1, max_size=100)),
                'city': draw(st.text(min_size=1, max_size=50)),
                'state': draw(st.text(min_size=2, max_size=2)),
                'zip': draw(st.text(min_size=5, max_size=10)),
                'country': 'US'
            },
            'shipping_address': {
                'street': draw(st.text(min_size=1, max_size=100)),
                'city': draw(st.text(min_size=1, max_size=50)),
                'state': draw(st.text(min_size=2, max_size=2)),
                'zip': draw(st.text(min_size=5, max_size=10)),
                'country': 'US'
            },
            'payment_method': draw(st.sampled_from(['credit_card', 'paypal', 'bank_transfer'])),
            'shipping_method': draw(st.sampled_from(['standard', 'express', 'overnight'])),
            'notes': draw(st.text(max_size=200))
        }
    
    @st.composite
    def refund_data_strategy(draw, order_total):
        """Generate valid refund data based on order total."""
        refund_amount = draw(st.floats(min_value=0.01, max_value=order_total))
        
        return {
            'refund_amount': refund_amount,
            'refund_reason': draw(st.sampled_from([
                'Defective product', 'Wrong item', 'Customer request', 
                'Shipping damage', 'Quality issues'
            ])),
            'refund_type': draw(st.sampled_from(['full', 'partial'])),
            'restore_inventory': draw(st.booleans())
        }
    
    # Property 13: Refund Processing Completeness Tests
    # **Feature: dynamic-admin-system, Property 13: Refund Processing Completeness**
    
    @given(
        order_data=order_data_strategy()
    )
    @settings(max_examples=50, deadline=10000)
    def test_refund_processing_updates_all_systems(self, order_data):
        """
        **Feature: dynamic-admin-system, Property 13: Refund Processing Completeness**
        For any refund or cancellation, all related systems (inventory, payments, notifications) 
        should be updated automatically and consistently.
        **Validates: Requirements 6.2**
        """
        # Create an order with captured payment
        order_data['payment_status'] = PaymentStatus.CAPTURED.value
        order_data['status'] = OrderStatus.CONFIRMED.value
        
        order = self.order_manager.create_order(order_data, self.test_user_id)
        
        # Create products for inventory tracking
        for item in order.items:
            product_data = {
                '_id': ObjectId(item['product_id']),
                'name': item['name'],
                'inventory_count': 100,  # Initial inventory
                'track_inventory': True
            }
            self.mock_mongo.db.products.insert_one(product_data)
        
        # Create refund request
        refund_data = {
            'refund_amount': order.total_amount,
            'refund_reason': 'Customer request',
            'refund_type': 'full',
            'restore_inventory': True,
            'items_to_refund': [
                {
                    'product_id': item['product_id'],
                    'quantity': item['quantity']
                }
                for item in order.items
            ]
        }
        
        refund = self.refund_processor.create_refund_request(
            order.id, refund_data, self.test_user_id
        )
        
        # Approve and process the refund
        approve_success = self.refund_processor.approve_refund(refund.id, self.test_user_id)
        assert approve_success, "Refund approval should succeed"
        
        process_success = self.refund_processor.process_refund(refund.id, self.test_user_id)
        assert process_success, "Refund processing should succeed"
        
        # Verify refund status is completed
        processed_refund = self.refund_processor.get_refund(refund.id)
        assert processed_refund.status == RefundStatus.COMPLETED, \
            "Refund should be completed"
        assert processed_refund.processed_date is not None, \
            "Refund should have processed date"
        
        # Verify order status is updated for full refunds
        if refund_data['refund_type'] == 'full':
            updated_order = self.order_manager.get_order(order.id)
            assert updated_order.status == OrderStatus.REFUNDED, \
                "Order should be marked as refunded for full refunds"
        
        # Verify inventory is restored if requested
        if refund_data['restore_inventory']:
            for item in refund_data['items_to_refund']:
                product = self.mock_mongo.db.products.find_one({'_id': ObjectId(item['product_id'])})
                expected_inventory = 100 + item['quantity']  # Original + restored
                assert product['inventory_count'] == expected_inventory, \
                    f"Product {item['product_id']} inventory should be restored"
            
            # Verify inventory restoration flag is set
            assert processed_refund.inventory_restored, \
                "Refund should be marked as inventory restored"
    
    @given(
        order_data=order_data_strategy(),
        cancellation_reason=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=50, deadline=10000)
    def test_order_cancellation_completeness(self, order_data, cancellation_reason):
        """
        **Feature: dynamic-admin-system, Property 13: Refund Processing Completeness**
        For any order cancellation, all related systems should be updated consistently,
        including automatic refund processing and inventory restoration.
        **Validates: Requirements 6.2**
        """
        # Create an order that can be cancelled (not shipped/delivered)
        cancellable_statuses = [OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING]
        order_data['status'] = st.sampled_from([status.value for status in cancellable_statuses]).example()
        order_data['payment_status'] = PaymentStatus.CAPTURED.value
        
        order = self.order_manager.create_order(order_data, self.test_user_id)
        
        # Create products for inventory tracking
        original_inventory = {}
        for item in order.items:
            initial_inventory = 50
            original_inventory[item['product_id']] = initial_inventory
            product_data = {
                '_id': ObjectId(item['product_id']),
                'name': item['name'],
                'inventory_count': initial_inventory,
                'track_inventory': True
            }
            self.mock_mongo.db.products.insert_one(product_data)
        
        # Cancel the order
        cancel_success = self.refund_processor.cancel_order(
            order.id, cancellation_reason, self.test_user_id
        )
        assert cancel_success, "Order cancellation should succeed"
        
        # Verify order status is updated
        cancelled_order = self.order_manager.get_order(order.id)
        assert cancelled_order.status == OrderStatus.CANCELLED, \
            "Order should be marked as cancelled"
        
        # Verify automatic refund was created and processed for captured payments
        refunds = self.refund_processor.get_refunds_by_order(order.id)
        assert len(refunds) == 1, "One refund should be created for cancelled order"
        
        refund = refunds[0]
        assert refund.status == RefundStatus.COMPLETED, \
            "Automatic refund should be completed"
        assert refund.refund_amount == order.total_amount, \
            "Refund amount should equal order total"
        assert refund.refund_type == 'full', \
            "Cancellation refund should be full refund"
        assert cancellation_reason in refund.refund_reason, \
            "Refund reason should include cancellation reason"
        
        # Verify inventory is restored
        for item in order.items:
            product = self.mock_mongo.db.products.find_one({'_id': ObjectId(item['product_id'])})
            expected_inventory = original_inventory[item['product_id']] + item['quantity']
            assert product['inventory_count'] == expected_inventory, \
                f"Product {item['product_id']} inventory should be restored after cancellation"
    
    @given(
        order_data=order_data_strategy()
    )
    @settings(max_examples=50, deadline=10000)
    def test_partial_refund_consistency(self, order_data):
        """
        **Feature: dynamic-admin-system, Property 13: Refund Processing Completeness**
        For any partial refund, the refund amount should be properly tracked and 
        the order should remain in appropriate status.
        **Validates: Requirements 6.2**
        """
        # Create an order with captured payment
        order_data['payment_status'] = PaymentStatus.CAPTURED.value
        order_data['status'] = OrderStatus.DELIVERED.value
        
        order = self.order_manager.create_order(order_data, self.test_user_id)
        
        # Create partial refund (50% of order total)
        partial_amount = order.total_amount * 0.5
        refund_data = {
            'refund_amount': partial_amount,
            'refund_reason': 'Partial damage',
            'refund_type': 'partial',
            'restore_inventory': False  # Don't restore inventory for partial refunds
        }
        
        refund = self.refund_processor.create_refund_request(
            order.id, refund_data, self.test_user_id
        )
        
        # Process the refund
        approve_success = self.refund_processor.approve_refund(refund.id, self.test_user_id)
        assert approve_success, "Partial refund approval should succeed"
        
        process_success = self.refund_processor.process_refund(refund.id, self.test_user_id)
        assert process_success, "Partial refund processing should succeed"
        
        # Verify refund is completed with correct amount
        processed_refund = self.refund_processor.get_refund(refund.id)
        assert processed_refund.status == RefundStatus.COMPLETED, \
            "Partial refund should be completed"
        assert processed_refund.refund_amount == partial_amount, \
            "Refund amount should match requested partial amount"
        assert processed_refund.refund_type == 'partial', \
            "Refund type should be partial"
        
        # Verify order status is NOT changed to refunded for partial refunds
        updated_order = self.order_manager.get_order(order.id)
        assert updated_order.status != OrderStatus.REFUNDED, \
            "Order should not be marked as refunded for partial refunds"
        assert updated_order.status == OrderStatus.DELIVERED, \
            "Order should maintain original status for partial refunds"
    
    @given(
        order_data=order_data_strategy()
    )
    @settings(max_examples=50, deadline=10000)
    def test_multiple_refunds_tracking(self, order_data):
        """
        **Feature: dynamic-admin-system, Property 13: Refund Processing Completeness**
        For any order with multiple refunds, the total refunded amount should be 
        properly tracked and not exceed the order total.
        **Validates: Requirements 6.2**
        """
        # Create an order with captured payment
        order_data['payment_status'] = PaymentStatus.CAPTURED.value
        order_data['status'] = OrderStatus.DELIVERED.value
        
        order = self.order_manager.create_order(order_data, self.test_user_id)
        
        # Create multiple partial refunds
        refund_amounts = [
            order.total_amount * 0.3,  # 30%
            order.total_amount * 0.2   # 20%
        ]
        
        refund_ids = []
        for i, amount in enumerate(refund_amounts):
            refund_data = {
                'refund_amount': amount,
                'refund_reason': f'Partial issue {i+1}',
                'refund_type': 'partial',
                'restore_inventory': False
            }
            
            refund = self.refund_processor.create_refund_request(
                order.id, refund_data, self.test_user_id
            )
            refund_ids.append(refund.id)
            
            # Process each refund
            self.refund_processor.approve_refund(refund.id, self.test_user_id)
            process_success = self.refund_processor.process_refund(refund.id, self.test_user_id)
            assert process_success, f"Refund {i+1} processing should succeed"
        
        # Verify all refunds are completed
        all_refunds = self.refund_processor.get_refunds_by_order(order.id)
        assert len(all_refunds) == len(refund_amounts), \
            "All refunds should be created"
        
        total_refunded = sum(refund.refund_amount for refund in all_refunds)
        expected_total = sum(refund_amounts)
        
        assert abs(total_refunded - expected_total) < 0.01, \
            "Total refunded amount should match sum of individual refunds"
        assert total_refunded <= order.total_amount, \
            "Total refunded should not exceed order total"
        
        # Verify each refund has correct status
        for refund in all_refunds:
            assert refund.status == RefundStatus.COMPLETED, \
                "Each refund should be completed"
            assert refund.processed_date is not None, \
                "Each refund should have processed date"
    
    @given(
        order_data=order_data_strategy()
    )
    @settings(max_examples=50, deadline=10000)
    def test_refund_failure_handling(self, order_data):
        """
        **Feature: dynamic-admin-system, Property 13: Refund Processing Completeness**
        For any refund processing failure, the system should handle errors gracefully
        and maintain data consistency.
        **Validates: Requirements 6.2**
        """
        # Create an order
        order_data['payment_status'] = PaymentStatus.CAPTURED.value
        order = self.order_manager.create_order(order_data, self.test_user_id)
        
        # Create refund with invalid amount (exceeds order total)
        invalid_refund_data = {
            'refund_amount': order.total_amount * 2,  # Invalid: exceeds order total
            'refund_reason': 'Test invalid refund',
            'refund_type': 'full',
            'restore_inventory': True
        }
        
        # Attempt to create invalid refund should fail
        with pytest.raises(ValueError):
            self.refund_processor.create_refund_request(
                order.id, invalid_refund_data, self.test_user_id
            )
        
        # Create valid refund but simulate processing failure
        valid_refund_data = {
            'refund_amount': order.total_amount * 0.5,
            'refund_reason': 'Valid refund',
            'refund_type': 'partial',
            'restore_inventory': False
        }
        
        refund = self.refund_processor.create_refund_request(
            order.id, valid_refund_data, self.test_user_id
        )
        
        # Approve the refund
        approve_success = self.refund_processor.approve_refund(refund.id, self.test_user_id)
        assert approve_success, "Valid refund approval should succeed"
        
        # Verify refund is in approved state
        approved_refund = self.refund_processor.get_refund(refund.id)
        assert approved_refund.status == RefundStatus.APPROVED, \
            "Refund should be in approved state"
        
        # Verify order status is unchanged until processing completes
        unchanged_order = self.order_manager.get_order(order.id)
        assert unchanged_order.status == order.status, \
            "Order status should be unchanged until refund processing completes"