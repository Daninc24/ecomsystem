"""
Bulk Operation Handler Service
Handles batch operations on products with progress tracking and error handling
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from bson import ObjectId
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .base_service import BaseService
from ..models.product import BulkOperation, BulkOperationType, ProductStatus


class BulkOperationHandler(BaseService):
    """Service for handling bulk operations on products."""
    
    def __init__(self, db):
        self.products_collection = db.products
        self.categories_collection = db.product_categories
        self._operation_lock = threading.Lock()
        super().__init__(db)
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'bulk_operations'
    
    def create_bulk_operation(self, operation_type: BulkOperationType, 
                            product_ids: List[ObjectId], parameters: Dict[str, Any],
                            user_id: ObjectId) -> ObjectId:
        """Create a new bulk operation."""
        operation_data = {
            'operation_type': operation_type.value,  # Store enum value directly
            'product_ids': product_ids,
            'parameters': parameters,
            'status': 'pending',
            'progress': 0,
            'total_items': len(product_ids),
            'processed_items': 0,
            'failed_items': 0,
            'results': [],
            'errors': [],
            'started_at': None,
            'completed_at': None,
            'created_by': user_id,
            'created_at': datetime.utcnow()
        }
        
        result = self.collection.insert_one(operation_data)
        return result.inserted_id
    
    def execute_bulk_operation(self, operation_id: ObjectId) -> bool:
        """Execute a bulk operation with progress tracking."""
        operation = self.collection.find_one({'_id': operation_id})
        if not operation:
            return False
        
        # Update operation status to processing
        self._update_operation_status(operation_id, 'processing', started_at=datetime.utcnow())
        
        try:
            operation_type = BulkOperationType(operation['operation_type'])
            product_ids = operation['product_ids']
            parameters = operation['parameters']
            
            # Execute based on operation type
            if operation_type == BulkOperationType.UPDATE_PRICE:
                success = self._execute_price_update(operation_id, product_ids, parameters)
            elif operation_type == BulkOperationType.UPDATE_CATEGORY:
                success = self._execute_category_update(operation_id, product_ids, parameters)
            elif operation_type == BulkOperationType.UPDATE_STATUS:
                success = self._execute_status_update(operation_id, product_ids, parameters)
            elif operation_type == BulkOperationType.UPDATE_INVENTORY:
                success = self._execute_inventory_update(operation_id, product_ids, parameters)
            elif operation_type == BulkOperationType.DELETE:
                success = self._execute_delete(operation_id, product_ids, parameters)
            elif operation_type == BulkOperationType.DUPLICATE:
                success = self._execute_duplicate(operation_id, product_ids, parameters)
            else:
                success = False
            
            # Update final status
            status = 'completed' if success else 'failed'
            self._update_operation_status(operation_id, status, completed_at=datetime.utcnow())
            
            return success
            
        except Exception as e:
            self._update_operation_status(operation_id, 'failed', completed_at=datetime.utcnow())
            self._add_operation_error(operation_id, f"Execution failed: {str(e)}")
            return False
    
    def get_operation_status(self, operation_id: ObjectId) -> Optional[Dict[str, Any]]:
        """Get the current status of a bulk operation."""
        return self.collection.find_one({'_id': operation_id})
    
    def list_operations(self, user_id: Optional[ObjectId] = None, 
                       limit: int = 50) -> List[Dict[str, Any]]:
        """List bulk operations, optionally filtered by user."""
        query = {}
        if user_id:
            query['created_by'] = user_id
        
        return list(self.collection.find(query).sort('created_at', -1).limit(limit))
    
    def cancel_operation(self, operation_id: ObjectId) -> bool:
        """Cancel a pending or processing bulk operation."""
        operation = self.collection.find_one({'_id': operation_id})
        if not operation or operation['status'] in ['completed', 'failed', 'cancelled']:
            return False
        
        result = self.collection.update_one(
            {'_id': operation_id},
            {
                '$set': {
                    'status': 'cancelled',
                    'completed_at': datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0
    
    # Private execution methods
    
    def _execute_price_update(self, operation_id: ObjectId, product_ids: List[ObjectId], 
                            parameters: Dict[str, Any]) -> bool:
        """Execute bulk price update operation."""
        update_type = parameters.get('update_type', 'absolute')  # absolute, percentage, fixed_amount
        value = parameters.get('value', 0)
        
        processed = 0
        failed = 0
        
        for product_id in product_ids:
            try:
                product = self.products_collection.find_one({'_id': product_id})
                if not product:
                    failed += 1
                    self._add_operation_error(operation_id, f"Product {product_id} not found")
                    continue
                
                current_price = product.get('pricing', {}).get('price', 0)
                
                if update_type == 'absolute':
                    new_price = value
                elif update_type == 'percentage':
                    new_price = current_price * (1 + value / 100)
                elif update_type == 'fixed_amount':
                    new_price = current_price + value
                else:
                    new_price = current_price
                
                # Ensure price is not negative
                new_price = max(0, new_price)
                
                # Update product
                result = self.products_collection.update_one(
                    {'_id': product_id},
                    {
                        '$set': {
                            'pricing': {
                                **product.get('pricing', {}),
                                'price': new_price
                            },
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    processed += 1
                    self._add_operation_result(operation_id, {
                        'product_id': product_id,
                        'old_price': current_price,
                        'new_price': new_price,
                        'status': 'success'
                    })
                else:
                    failed += 1
                    self._add_operation_error(operation_id, f"Failed to update price for product {product_id}")
                
            except Exception as e:
                failed += 1
                self._add_operation_error(operation_id, f"Error updating product {product_id}: {str(e)}")
            
            # Update progress
            self._update_operation_progress(operation_id, processed + failed, processed, failed)
        
        return failed == 0
    
    def _execute_category_update(self, operation_id: ObjectId, product_ids: List[ObjectId], 
                               parameters: Dict[str, Any]) -> bool:
        """Execute bulk category update operation."""
        new_category_id = parameters.get('category_id')
        if not new_category_id:
            return False
        
        # Validate category exists
        category = self.categories_collection.find_one({'_id': ObjectId(new_category_id)})
        if not category:
            self._add_operation_error(operation_id, f"Category {new_category_id} not found")
            return False
        
        category_path = category.get('path', [])
        processed = 0
        failed = 0
        
        for product_id in product_ids:
            try:
                result = self.products_collection.update_one(
                    {'_id': product_id},
                    {
                        '$set': {
                            'category_id': ObjectId(new_category_id),
                            'category_path': category_path,
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    processed += 1
                    self._add_operation_result(operation_id, {
                        'product_id': product_id,
                        'new_category_id': new_category_id,
                        'status': 'success'
                    })
                else:
                    failed += 1
                    self._add_operation_error(operation_id, f"Failed to update category for product {product_id}")
                
            except Exception as e:
                failed += 1
                self._add_operation_error(operation_id, f"Error updating product {product_id}: {str(e)}")
            
            # Update progress
            self._update_operation_progress(operation_id, processed + failed, processed, failed)
        
        return failed == 0
    
    def _execute_status_update(self, operation_id: ObjectId, product_ids: List[ObjectId], 
                             parameters: Dict[str, Any]) -> bool:
        """Execute bulk status update operation."""
        new_status = parameters.get('status')
        if not new_status or new_status not in [status.value for status in ProductStatus]:
            return False
        
        processed = 0
        failed = 0
        
        for product_id in product_ids:
            try:
                result = self.products_collection.update_one(
                    {'_id': product_id},
                    {
                        '$set': {
                            'status': new_status,
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    processed += 1
                    self._add_operation_result(operation_id, {
                        'product_id': product_id,
                        'new_status': new_status,
                        'status': 'success'
                    })
                else:
                    failed += 1
                    self._add_operation_error(operation_id, f"Failed to update status for product {product_id}")
                
            except Exception as e:
                failed += 1
                self._add_operation_error(operation_id, f"Error updating product {product_id}: {str(e)}")
            
            # Update progress
            self._update_operation_progress(operation_id, processed + failed, processed, failed)
        
        return failed == 0
    
    def _execute_inventory_update(self, operation_id: ObjectId, product_ids: List[ObjectId], 
                                parameters: Dict[str, Any]) -> bool:
        """Execute bulk inventory update operation."""
        update_type = parameters.get('update_type', 'set')  # set, add, subtract
        quantity = parameters.get('quantity', 0)
        
        processed = 0
        failed = 0
        
        for product_id in product_ids:
            try:
                product = self.products_collection.find_one({'_id': product_id})
                if not product:
                    failed += 1
                    self._add_operation_error(operation_id, f"Product {product_id} not found")
                    continue
                
                current_stock = product.get('inventory', {}).get('stock', 0)
                
                if update_type == 'set':
                    new_stock = quantity
                elif update_type == 'add':
                    new_stock = current_stock + quantity
                elif update_type == 'subtract':
                    new_stock = max(0, current_stock - quantity)
                else:
                    new_stock = current_stock
                
                # Update product
                result = self.products_collection.update_one(
                    {'_id': product_id},
                    {
                        '$set': {
                            'inventory': {
                                **product.get('inventory', {}),
                                'stock': new_stock
                            },
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    processed += 1
                    self._add_operation_result(operation_id, {
                        'product_id': product_id,
                        'old_stock': current_stock,
                        'new_stock': new_stock,
                        'status': 'success'
                    })
                else:
                    failed += 1
                    self._add_operation_error(operation_id, f"Failed to update inventory for product {product_id}")
                
            except Exception as e:
                failed += 1
                self._add_operation_error(operation_id, f"Error updating product {product_id}: {str(e)}")
            
            # Update progress
            self._update_operation_progress(operation_id, processed + failed, processed, failed)
        
        return failed == 0
    
    def _execute_delete(self, operation_id: ObjectId, product_ids: List[ObjectId], 
                       parameters: Dict[str, Any]) -> bool:
        """Execute bulk delete operation."""
        processed = 0
        failed = 0
        
        for product_id in product_ids:
            try:
                result = self.products_collection.delete_one({'_id': product_id})
                
                if result.deleted_count > 0:
                    processed += 1
                    self._add_operation_result(operation_id, {
                        'product_id': product_id,
                        'status': 'deleted'
                    })
                else:
                    failed += 1
                    self._add_operation_error(operation_id, f"Failed to delete product {product_id}")
                
            except Exception as e:
                failed += 1
                self._add_operation_error(operation_id, f"Error deleting product {product_id}: {str(e)}")
            
            # Update progress
            self._update_operation_progress(operation_id, processed + failed, processed, failed)
        
        return failed == 0
    
    def _execute_duplicate(self, operation_id: ObjectId, product_ids: List[ObjectId], 
                         parameters: Dict[str, Any]) -> bool:
        """Execute bulk duplicate operation."""
        suffix = parameters.get('suffix', ' (Copy)')
        processed = 0
        failed = 0
        
        for product_id in product_ids:
            try:
                product = self.products_collection.find_one({'_id': product_id})
                if not product:
                    failed += 1
                    self._add_operation_error(operation_id, f"Product {product_id} not found")
                    continue
                
                # Create duplicate
                duplicate = product.copy()
                duplicate.pop('_id', None)
                duplicate['basic_info']['name'] += suffix
                duplicate['status'] = ProductStatus.DRAFT.value
                duplicate['created_at'] = datetime.utcnow()
                duplicate['updated_at'] = datetime.utcnow()
                
                result = self.products_collection.insert_one(duplicate)
                
                if result.inserted_id:
                    processed += 1
                    self._add_operation_result(operation_id, {
                        'original_product_id': product_id,
                        'duplicate_product_id': result.inserted_id,
                        'status': 'duplicated'
                    })
                else:
                    failed += 1
                    self._add_operation_error(operation_id, f"Failed to duplicate product {product_id}")
                
            except Exception as e:
                failed += 1
                self._add_operation_error(operation_id, f"Error duplicating product {product_id}: {str(e)}")
            
            # Update progress
            self._update_operation_progress(operation_id, processed + failed, processed, failed)
        
        return failed == 0
    
    # Helper methods
    
    def _update_operation_status(self, operation_id: ObjectId, status: str, **kwargs):
        """Update operation status and timestamps."""
        update_data = {'status': status}
        update_data.update(kwargs)
        
        self.collection.update_one(
            {'_id': operation_id},
            {'$set': update_data}
        )
    
    def _update_operation_progress(self, operation_id: ObjectId, processed_items: int, 
                                 successful_items: int, failed_items: int):
        """Update operation progress."""
        operation = self.collection.find_one({'_id': operation_id})
        total_items = operation.get('total_items', 0)
        progress = int((processed_items / total_items) * 100) if total_items > 0 else 0
        
        self.collection.update_one(
            {'_id': operation_id},
            {
                '$set': {
                    'processed_items': processed_items,
                    'progress': progress,
                    'successful_items': successful_items,
                    'failed_items': failed_items
                }
            }
        )
    
    def _add_operation_result(self, operation_id: ObjectId, result: Dict[str, Any]):
        """Add a result to the operation."""
        self.collection.update_one(
            {'_id': operation_id},
            {'$push': {'results': result}}
        )
    
    def _add_operation_error(self, operation_id: ObjectId, error: str):
        """Add an error to the operation."""
        self.collection.update_one(
            {'_id': operation_id},
            {'$push': {'errors': {'message': error, 'timestamp': datetime.utcnow()}}}
        )