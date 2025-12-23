"""
Property-Based Tests for Product Management
Tests for bulk operations and category organization integrity
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime
from bson import ObjectId
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from admin.services.product_manager import ProductManager
from admin.services.bulk_operation_handler import BulkOperationHandler
from admin.models.product import BulkOperationType, ProductStatus
from simple_mongo_mock import MockMongo


class TestProductManagementProperties:
    """Property-based tests for product management functionality."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        self.mock_mongo = MockMongo()
        self.product_manager = ProductManager(self.mock_mongo.db)
        self.bulk_handler = BulkOperationHandler(self.mock_mongo.db)
        self.test_user_id = ObjectId()
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clear all collections - simplified approach
        collections = ['products', 'product_categories', 'bulk_operations', 'inventory_transactions']
        for collection_name in collections:
            try:
                getattr(self.mock_mongo.db, collection_name).delete_many({})
            except:
                pass
    
    # Test data generators
    
    @st.composite
    def product_data_strategy(draw):
        """Generate valid product data."""
        return {
            'basic_info': {
                'name': draw(st.text(min_size=1, max_size=100)),
                'description': draw(st.text(max_size=500)),
                'sku': draw(st.text(min_size=1, max_size=50)),
                'brand': draw(st.text(max_size=50)),
                'condition': draw(st.sampled_from(['new', 'used', 'refurbished']))
            },
            'pricing': {
                'price': draw(st.floats(min_value=0.01, max_value=10000)),
                'currency': 'USD'
            },
            'inventory': {
                'stock': draw(st.integers(min_value=0, max_value=1000)),
                'low_stock_threshold': draw(st.integers(min_value=1, max_value=50)),
                'track_inventory': True,
                'allow_backorders': draw(st.booleans())
            },
            'status': draw(st.sampled_from([status.value for status in ProductStatus])),
            'is_featured': draw(st.booleans()),
            'tags': draw(st.lists(st.text(min_size=1, max_size=20), max_size=10))
        }
    
    @st.composite
    def category_data_strategy(draw):
        """Generate valid category data."""
        return {
            'name': draw(st.text(min_size=1, max_size=100)),
            'description': draw(st.text(max_size=500)),
            'is_active': True,  # Always create active categories for tests
            'sort_order': draw(st.integers(min_value=0, max_value=1000)),
            'icon': draw(st.text(max_size=10)),
            'color': draw(st.text(min_size=6, max_size=7))  # Hex color
        }
    
    # Property 11: Bulk Operation Consistency Tests
    # **Feature: dynamic-admin-system, Property 11: Bulk Operation Consistency**
    
    @given(
        products=st.lists(product_data_strategy(), min_size=1, max_size=10),
        price_update=st.floats(min_value=0.01, max_value=1000)
    )
    @settings(max_examples=50, deadline=5000)
    def test_bulk_price_update_consistency(self, products, price_update):
        """
        **Feature: dynamic-admin-system, Property 11: Bulk Operation Consistency**
        For any bulk price update operation, all selected products should have their prices updated consistently.
        **Validates: Requirements 5.2**
        """
        # Create test products
        product_ids = []
        original_prices = []
        
        for product_data in products:
            product_id = self.product_manager.create_product(product_data, self.test_user_id)
            product_ids.append(product_id)
            original_prices.append(product_data['pricing']['price'])
        
        # Create and execute bulk price update operation
        operation_id = self.bulk_handler.create_bulk_operation(
            operation_type=BulkOperationType.UPDATE_PRICE,
            product_ids=product_ids,
            parameters={
                'update_type': 'absolute',
                'value': price_update
            },
            user_id=self.test_user_id
        )
        
        # Execute the operation
        success = self.bulk_handler.execute_bulk_operation(operation_id)
        assert success, "Bulk operation should succeed"
        
        # Verify all products have the new price
        for product_id in product_ids:
            updated_product = self.product_manager.get_product(product_id)
            assert updated_product is not None, f"Product {product_id} should exist"
            assert updated_product['pricing']['price'] == price_update, \
                f"Product {product_id} should have price {price_update}"
        
        # Verify operation status
        operation_status = self.bulk_handler.get_operation_status(operation_id)
        assert operation_status['status'] == 'completed', "Operation should be completed"
        assert operation_status['processed_items'] == len(product_ids), \
            "All products should be processed"
        assert operation_status['failed_items'] == 0, "No products should fail"
    
    @given(
        products=st.lists(product_data_strategy(), min_size=1, max_size=10),
        new_status=st.sampled_from([status.value for status in ProductStatus])
    )
    @settings(max_examples=50, deadline=5000)
    def test_bulk_status_update_consistency(self, products, new_status):
        """
        **Feature: dynamic-admin-system, Property 11: Bulk Operation Consistency**
        For any bulk status update operation, all selected products should have their status updated consistently.
        **Validates: Requirements 5.2**
        """
        # Create test products
        product_ids = []
        
        for product_data in products:
            product_id = self.product_manager.create_product(product_data, self.test_user_id)
            product_ids.append(product_id)
        
        # Create and execute bulk status update operation
        operation_id = self.bulk_handler.create_bulk_operation(
            operation_type=BulkOperationType.UPDATE_STATUS,
            product_ids=product_ids,
            parameters={'status': new_status},
            user_id=self.test_user_id
        )
        
        # Execute the operation
        success = self.bulk_handler.execute_bulk_operation(operation_id)
        assert success, "Bulk operation should succeed"
        
        # Verify all products have the new status
        for product_id in product_ids:
            updated_product = self.product_manager.get_product(product_id)
            assert updated_product is not None, f"Product {product_id} should exist"
            assert updated_product['status'] == new_status, \
                f"Product {product_id} should have status {new_status}"
        
        # Verify operation status
        operation_status = self.bulk_handler.get_operation_status(operation_id)
        assert operation_status['status'] == 'completed', "Operation should be completed"
        assert operation_status['processed_items'] == len(product_ids), \
            "All products should be processed"
        assert operation_status['failed_items'] == 0, "No products should fail"
    
    @given(
        products=st.lists(product_data_strategy(), min_size=1, max_size=10),
        inventory_update=st.integers(min_value=0, max_value=1000)
    )
    @settings(max_examples=50, deadline=5000)
    def test_bulk_inventory_update_consistency(self, products, inventory_update):
        """
        **Feature: dynamic-admin-system, Property 11: Bulk Operation Consistency**
        For any bulk inventory update operation, all selected products should have their inventory updated consistently.
        **Validates: Requirements 5.2**
        """
        # Create test products
        product_ids = []
        
        for product_data in products:
            product_id = self.product_manager.create_product(product_data, self.test_user_id)
            product_ids.append(product_id)
        
        # Create and execute bulk inventory update operation
        operation_id = self.bulk_handler.create_bulk_operation(
            operation_type=BulkOperationType.UPDATE_INVENTORY,
            product_ids=product_ids,
            parameters={
                'update_type': 'set',
                'quantity': inventory_update
            },
            user_id=self.test_user_id
        )
        
        # Execute the operation
        success = self.bulk_handler.execute_bulk_operation(operation_id)
        assert success, "Bulk operation should succeed"
        
        # Verify all products have the new inventory
        for product_id in product_ids:
            updated_product = self.product_manager.get_product(product_id)
            assert updated_product is not None, f"Product {product_id} should exist"
            assert updated_product['inventory']['stock'] == inventory_update, \
                f"Product {product_id} should have stock {inventory_update}"
        
        # Verify operation status
        operation_status = self.bulk_handler.get_operation_status(operation_id)
        assert operation_status['status'] == 'completed', "Operation should be completed"
        assert operation_status['processed_items'] == len(product_ids), \
            "All products should be processed"
        assert operation_status['failed_items'] == 0, "No products should fail"
    
    # Property 12: Category Organization Integrity Tests
    # **Feature: dynamic-admin-system, Property 12: Category Organization Integrity**
    
    @given(
        categories=st.lists(category_data_strategy(), min_size=2, max_size=5),
        products=st.lists(product_data_strategy(), min_size=1, max_size=5)
    )
    @settings(max_examples=50, deadline=5000)
    def test_category_move_updates_product_paths(self, categories, products):
        """
        **Feature: dynamic-admin-system, Property 12: Category Organization Integrity**
        For any category reorganization, all products in moved categories should have their category paths updated automatically.
        **Validates: Requirements 5.1**
        """
        # Create parent and child categories
        parent_category_id = self.product_manager.create_category(categories[0], self.test_user_id)
        child_category_data = categories[1].copy()
        child_category_data['parent_id'] = parent_category_id
        child_category_id = self.product_manager.create_category(child_category_data, self.test_user_id)
        
        # Create products in the child category
        product_ids = []
        for product_data in products:
            product_data['category_id'] = child_category_id
            product_id = self.product_manager.create_product(product_data, self.test_user_id)
            product_ids.append(product_id)
        
        # Verify initial category paths
        for product_id in product_ids:
            product = self.product_manager.get_product(product_id)
            assert len(product['category_path']) == 2, "Product should have 2-level category path"
            assert product['category_path'][0] == categories[0]['name'], \
                "First path element should be parent category name"
            assert product['category_path'][1] == categories[1]['name'], \
                "Second path element should be child category name"
        
        # Create a new parent category and move the child category
        if len(categories) > 2:
            new_parent_category_id = self.product_manager.create_category(categories[2], self.test_user_id)
            
            # Move child category to new parent
            success = self.product_manager.move_category(
                child_category_id, 
                new_parent_category_id, 
                0, 
                self.test_user_id
            )
            assert success, "Category move should succeed"
            
            # Verify all products have updated category paths
            for product_id in product_ids:
                updated_product = self.product_manager.get_product(product_id)
                assert len(updated_product['category_path']) == 2, \
                    "Product should still have 2-level category path"
                assert updated_product['category_path'][0] == categories[2]['name'], \
                    "First path element should be new parent category name"
                assert updated_product['category_path'][1] == categories[1]['name'], \
                    "Second path element should remain child category name"
    
    @given(
        category_data=category_data_strategy(),
        products=st.lists(product_data_strategy(), min_size=1, max_size=5)
    )
    @settings(max_examples=50, deadline=5000)
    def test_category_deletion_handles_products(self, category_data, products):
        """
        **Feature: dynamic-admin-system, Property 12: Category Organization Integrity**
        For any category deletion, all products in that category should be handled appropriately (moved or uncategorized).
        **Validates: Requirements 5.1**
        """
        # Create a category
        category_id = self.product_manager.create_category(category_data, self.test_user_id)
        
        # Create products in the category
        product_ids = []
        for product_data in products:
            product_data['category_id'] = category_id
            product_id = self.product_manager.create_product(product_data, self.test_user_id)
            product_ids.append(product_id)
        
        # Verify products are in the category
        for product_id in product_ids:
            product = self.product_manager.get_product(product_id)
            # Handle both ObjectId and string representations
            product_category_id = product['category_id']
            if isinstance(product_category_id, str):
                product_category_id = ObjectId(product_category_id)
            assert product_category_id == category_id, \
                "Product should be in the created category"
        
        # Delete the category
        success = self.product_manager.delete_category(category_id, self.test_user_id)
        assert success, "Category deletion should succeed"
        
        # Verify products still exist but category is handled
        for product_id in product_ids:
            product = self.product_manager.get_product(product_id)
            assert product is not None, "Product should still exist after category deletion"
            # Category should be None or moved to parent (in this case None since no parent)
            assert product.get('category_id') is None, \
                "Product should have no category after category deletion"
    
    @given(
        parent_category=category_data_strategy(),
        child_categories=st.lists(category_data_strategy(), min_size=1, max_size=3),
        new_sort_orders=st.lists(st.integers(min_value=0, max_value=100), min_size=1, max_size=3)
    )
    @settings(max_examples=50, deadline=5000)
    def test_category_reordering_maintains_hierarchy(self, parent_category, child_categories, new_sort_orders):
        """
        **Feature: dynamic-admin-system, Property 12: Category Organization Integrity**
        For any category reordering, the hierarchical structure should be maintained with updated sort orders.
        **Validates: Requirements 5.1**
        """
        assume(len(child_categories) == len(new_sort_orders))
        
        # Create parent category
        parent_id = self.product_manager.create_category(parent_category, self.test_user_id)
        
        # Create child categories
        child_ids = []
        for i, child_data in enumerate(child_categories):
            child_data['parent_id'] = parent_id
            child_data['sort_order'] = i  # Initial sort order
            child_id = self.product_manager.create_category(child_data, self.test_user_id)
            child_ids.append(child_id)
        
        # Reorder categories by moving them with new sort orders
        for i, (child_id, new_sort_order) in enumerate(zip(child_ids, new_sort_orders)):
            success = self.product_manager.move_category(
                child_id, 
                parent_id,  # Keep same parent
                new_sort_order, 
                self.test_user_id
            )
            assert success, f"Moving category {i} should succeed"
        
        # Verify hierarchy is maintained
        category_tree = self.product_manager.get_category_tree()
        
        # Find the parent category in the tree
        parent_in_tree = None
        for category in category_tree:
            if category['_id'] == parent_id:
                parent_in_tree = category
                break
        
        assert parent_in_tree is not None, "Parent category should be in tree"
        assert len(parent_in_tree.get('children_data', [])) == len(child_categories), \
            "Parent should have all child categories"
        
        # Verify each child has correct parent and sort order
        for child_id, expected_sort_order in zip(child_ids, new_sort_orders):
            child_category = self.product_manager.categories_collection.find_one({'_id': child_id})
            assert child_category is not None, "Child category should exist"
            
            # Handle ObjectId vs string comparison
            child_parent_id = child_category['parent_id']
            if isinstance(child_parent_id, str):
                child_parent_id = ObjectId(child_parent_id)
            assert child_parent_id == parent_id, "Child should have correct parent"
            
            assert child_category['sort_order'] == expected_sort_order, \
                f"Child should have sort order {expected_sort_order}"