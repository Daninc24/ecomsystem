"""
Product Manager Service
Handles product management operations including drag-and-drop category organization
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from .base_service import BaseService
from ..models.product import (
    Product, ProductCategory, ProductStatus, InventoryTransaction
)


class ProductManager(BaseService):
    """Service for managing products and categories with drag-and-drop organization."""
    
    def __init__(self, db):
        self.categories_collection = db.product_categories
        self.inventory_transactions_collection = db.inventory_transactions
        super().__init__(db)
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'products'
    
    def create_product(self, product_data: Dict[str, Any], user_id: ObjectId) -> ObjectId:
        """Create a new product."""
        product = Product(**product_data)
        product.created_by = user_id
        product.updated_by = user_id
        product.created_at = datetime.utcnow()
        product.updated_at = datetime.utcnow()
        
        # Generate category path if category_id is provided
        if product.category_id:
            category_path = self._get_category_path(product.category_id)
            product.category_path = category_path
        
        # Initialize analytics
        product.analytics = {
            'views': 0,
            'favorites': 0,
            'sales': 0,
            'conversion_rate': 0.0,
            'last_viewed': None
        }
        
        result = self.collection.insert_one(product.__dict__)
        
        # Update category product count
        if product.category_id:
            self._update_category_product_count(product.category_id, 1)
        
        return result.inserted_id
    
    def update_product(self, product_id: ObjectId, updates: Dict[str, Any], user_id: ObjectId) -> bool:
        """Update an existing product."""
        updates['updated_by'] = user_id
        updates['updated_at'] = datetime.utcnow()
        
        # Get current product for category change tracking
        current_product = self.collection.find_one({'_id': product_id})
        if not current_product:
            return False
        
        old_category_id = current_product.get('category_id')
        new_category_id = updates.get('category_id', old_category_id)
        
        # Update category path if category changed
        if new_category_id and new_category_id != old_category_id:
            updates['category_path'] = self._get_category_path(new_category_id)
        
        result = self.collection.update_one(
            {'_id': product_id},
            {'$set': updates}
        )
        
        # Update category product counts
        if old_category_id != new_category_id:
            if old_category_id:
                self._update_category_product_count(old_category_id, -1)
            if new_category_id:
                self._update_category_product_count(new_category_id, 1)
        
        return result.modified_count > 0
    
    def delete_product(self, product_id: ObjectId, user_id: ObjectId) -> bool:
        """Delete a product."""
        product = self.collection.find_one({'_id': product_id})
        if not product:
            return False
        
        result = self.collection.delete_one({'_id': product_id})
        
        # Update category product count
        if product.get('category_id'):
            self._update_category_product_count(product['category_id'], -1)
        
        return result.deleted_count > 0
    
    def get_product(self, product_id: ObjectId) -> Optional[Dict[str, Any]]:
        """Get a single product by ID."""
        return self.collection.find_one({'_id': product_id})
    
    def list_products(self, filters: Dict[str, Any] = None, 
                     page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """List products with filtering and pagination."""
        query = filters or {}
        skip = (page - 1) * limit
        
        # Build aggregation pipeline for enhanced product listing
        pipeline = [
            {'$match': query},
            {
                '$lookup': {
                    'from': 'product_categories',
                    'localField': 'category_id',
                    'foreignField': '_id',
                    'as': 'category_info'
                }
            },
            {
                '$lookup': {
                    'from': 'vendors',
                    'localField': 'vendor_id',
                    'foreignField': '_id',
                    'as': 'vendor_info'
                }
            },
            {'$skip': skip},
            {'$limit': limit}
        ]
        
        products = list(self.collection.aggregate(pipeline))
        total = self.collection.count_documents(query)
        
        return {
            'products': products,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit
        }
    
    # Category Management Methods
    
    def create_category(self, category_data: Dict[str, Any], user_id: ObjectId) -> ObjectId:
        """Create a new product category."""
        category = ProductCategory(**category_data)
        category.created_by = user_id
        category.updated_by = user_id
        category.created_at = datetime.utcnow()
        category.updated_at = datetime.utcnow()
        
        # Generate path and level based on parent
        if category.parent_id:
            parent = self.categories_collection.find_one({'_id': category.parent_id})
            if parent:
                category.path = parent['path'] + [category.name]
                category.level = parent['level'] + 1
            else:
                category.path = [category.name]
                category.level = 0
        else:
            category.path = [category.name]
            category.level = 0
        
        # Generate slug if not provided
        if not category.slug:
            category.slug = self._generate_category_slug(category.name)
        
        result = self.categories_collection.insert_one(category.__dict__)
        category_id = result.inserted_id
        
        # Add to parent's children after we have the ID
        if category.parent_id:
            self.categories_collection.update_one(
                {'_id': category.parent_id},
                {'$addToSet': {'children': category_id}}
            )
        
        return category_id
    
    def update_category(self, category_id: ObjectId, updates: Dict[str, Any], user_id: ObjectId) -> bool:
        """Update a category."""
        updates['updated_by'] = user_id
        updates['updated_at'] = datetime.utcnow()
        
        result = self.categories_collection.update_one(
            {'_id': category_id},
            {'$set': updates}
        )
        
        return result.modified_count > 0
    
    def move_category(self, category_id: ObjectId, new_parent_id: Optional[ObjectId], 
                     new_sort_order: int, user_id: ObjectId) -> bool:
        """Move a category to a new parent with drag-and-drop support."""
        category = self.categories_collection.find_one({'_id': category_id})
        if not category:
            return False
        
        old_parent_id = category.get('parent_id')
        
        # Remove from old parent's children
        if old_parent_id:
            self.categories_collection.update_one(
                {'_id': old_parent_id},
                {'$pull': {'children': category_id}}
            )
        
        # Add to new parent's children
        if new_parent_id:
            self.categories_collection.update_one(
                {'_id': new_parent_id},
                {'$addToSet': {'children': category_id}}
            )
        
        # Update category path and level
        if new_parent_id:
            parent = self.categories_collection.find_one({'_id': new_parent_id})
            if parent:
                new_path = parent['path'] + [category['name']]
                new_level = parent['level'] + 1
            else:
                new_path = [category['name']]
                new_level = 0
        else:
            new_path = [category['name']]
            new_level = 0
        
        # Update the category
        updates = {
            'parent_id': new_parent_id,
            'path': new_path,
            'level': new_level,
            'sort_order': new_sort_order,
            'updated_by': user_id,
            'updated_at': datetime.utcnow()
        }
        
        result = self.categories_collection.update_one(
            {'_id': category_id},
            {'$set': updates}
        )
        
        # Update all child categories' paths recursively
        self._update_child_category_paths(category_id, new_path)
        
        # Update all products in this category and its children
        self._update_products_category_paths(category_id)
        
        return result.modified_count > 0
    
    def get_category_tree(self) -> List[Dict[str, Any]]:
        """Get the complete category tree with hierarchical structure."""
        # Get all categories sorted by level and sort_order
        categories = list(self.categories_collection.find(
            {'is_active': True}
        ).sort([('level', 1), ('sort_order', 1)]))
        
        # Build tree structure
        category_map = {str(cat['_id']): cat for cat in categories}
        tree = []
        
        for category in categories:
            category['children_data'] = []
            if not category.get('parent_id'):
                tree.append(category)
            else:
                parent_id = str(category['parent_id'])
                if parent_id in category_map:
                    category_map[parent_id]['children_data'].append(category)
        
        return tree
    
    def delete_category(self, category_id: ObjectId, user_id: ObjectId) -> bool:
        """Delete a category and handle products and children."""
        category = self.categories_collection.find_one({'_id': category_id})
        if not category:
            return False
        
        # Check if category has products
        product_count = self.collection.count_documents({'category_id': category_id})
        if product_count > 0:
            # Move products to parent category or uncategorized
            new_category_id = category.get('parent_id')
            self.collection.update_many(
                {'category_id': category_id},
                {'$set': {'category_id': new_category_id}}
            )
        
        # Handle child categories
        child_categories = list(self.categories_collection.find({'parent_id': category_id}))
        for child in child_categories:
            # Move children to the parent of the deleted category
            self.move_category(child['_id'], category.get('parent_id'), child['sort_order'], user_id)
        
        # Remove from parent's children
        if category.get('parent_id'):
            self.categories_collection.update_one(
                {'_id': category['parent_id']},
                {'$pull': {'children': category_id}}
            )
        
        # Delete the category
        result = self.categories_collection.delete_one({'_id': category_id})
        return result.deleted_count > 0
    
    # Inventory Management Methods
    
    def update_inventory(self, product_id: ObjectId, quantity_change: int, 
                        transaction_type: str, reason: str = '', 
                        user_id: ObjectId = None, reference_id: ObjectId = None) -> bool:
        """Update product inventory and log the transaction."""
        product = self.collection.find_one({'_id': product_id})
        if not product:
            return False
        
        current_stock = product.get('inventory', {}).get('stock', 0)
        new_stock = max(0, current_stock + quantity_change)
        
        # Update product inventory
        result = self.collection.update_one(
            {'_id': product_id},
            {
                '$set': {
                    'inventory.stock': new_stock,
                    'updated_at': datetime.utcnow(),
                    'updated_by': user_id
                }
            }
        )
        
        # Log inventory transaction
        if result.modified_count > 0:
            transaction = InventoryTransaction(
                product_id=product_id,
                transaction_type=transaction_type,
                quantity_change=quantity_change,
                previous_quantity=current_stock,
                new_quantity=new_stock,
                reason=reason,
                reference_id=reference_id,
                created_by=user_id,
                created_at=datetime.utcnow()
            )
            
            self.inventory_transactions_collection.insert_one(transaction.__dict__)
        
        return result.modified_count > 0
    
    def get_inventory_history(self, product_id: ObjectId, limit: int = 50) -> List[Dict[str, Any]]:
        """Get inventory transaction history for a product."""
        return list(self.inventory_transactions_collection.find(
            {'product_id': product_id}
        ).sort('created_at', -1).limit(limit))
    
    def get_low_stock_products(self, threshold_multiplier: float = 1.0) -> List[Dict[str, Any]]:
        """Get products that are low on stock."""
        pipeline = [
            {
                '$match': {
                    'status': ProductStatus.ACTIVE.value,
                    'inventory.track_inventory': True,
                    '$expr': {
                        '$lte': [
                            '$inventory.stock',
                            {'$multiply': ['$inventory.low_stock_threshold', threshold_multiplier]}
                        ]
                    }
                }
            },
            {
                '$lookup': {
                    'from': 'product_categories',
                    'localField': 'category_id',
                    'foreignField': '_id',
                    'as': 'category_info'
                }
            },
            {'$sort': {'inventory.stock': 1}}
        ]
        
        return list(self.collection.aggregate(pipeline))
    
    # Helper Methods
    
    def _get_category_path(self, category_id: ObjectId) -> List[str]:
        """Get the full path for a category."""
        category = self.categories_collection.find_one({'_id': category_id})
        return category.get('path', []) if category else []
    
    def _update_category_product_count(self, category_id: ObjectId, change: int):
        """Update the product count for a category."""
        self.categories_collection.update_one(
            {'_id': category_id},
            {'$inc': {'product_count': change}}
        )
    
    def _generate_category_slug(self, name: str) -> str:
        """Generate a URL-friendly slug for a category."""
        import re
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name.lower())
        slug = re.sub(r'\s+', '-', slug.strip())
        
        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while self.categories_collection.find_one({'slug': slug}):
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    def _update_child_category_paths(self, parent_id: ObjectId, parent_path: List[str]):
        """Recursively update paths for all child categories."""
        children = list(self.categories_collection.find({'parent_id': parent_id}))
        
        for child in children:
            new_path = parent_path + [child['name']]
            new_level = len(new_path) - 1
            
            self.categories_collection.update_one(
                {'_id': child['_id']},
                {
                    '$set': {
                        'path': new_path,
                        'level': new_level,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            # Recursively update children
            self._update_child_category_paths(child['_id'], new_path)
    
    def _update_products_category_paths(self, category_id: ObjectId):
        """Update category paths for all products in a category and its children."""
        # Get all categories in the subtree
        category_ids = [category_id]
        self._collect_child_category_ids(category_id, category_ids)
        
        # Update products in all these categories
        for cat_id in category_ids:
            category_path = self._get_category_path(cat_id)
            self.collection.update_many(
                {'category_id': cat_id},
                {'$set': {'category_path': category_path}}
            )
    
    def _collect_child_category_ids(self, parent_id: ObjectId, category_ids: List[ObjectId]):
        """Recursively collect all child category IDs."""
        children = list(self.categories_collection.find({'parent_id': parent_id}))
        for child in children:
            category_ids.append(child['_id'])
            self._collect_child_category_ids(child['_id'], category_ids)