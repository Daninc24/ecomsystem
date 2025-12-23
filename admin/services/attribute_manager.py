"""
Attribute Manager Service
Manages product attributes for consistent product data structure
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from bson import ObjectId
import re

from .base_service import BaseService
from ..models.product import ProductAttribute


class AttributeManager(BaseService):
    """Service for managing product attributes and ensuring consistency."""
    
    def __init__(self, db):
        self.products_collection = db.products
        self.categories_collection = db.product_categories
        super().__init__(db)
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'product_attributes'
    
    def create_attribute(self, attribute_data: Dict[str, Any], user_id: ObjectId) -> ObjectId:
        """Create a new product attribute."""
        attribute = ProductAttribute(**attribute_data)
        attribute.created_by = user_id
        attribute.updated_by = user_id
        attribute.created_at = datetime.utcnow()
        attribute.updated_at = datetime.utcnow()
        
        # Generate slug if not provided
        if not attribute.slug:
            attribute.slug = self._generate_attribute_slug(attribute.name)
        
        # Validate attribute configuration
        if not self._validate_attribute(attribute):
            raise ValueError("Invalid attribute configuration")
        
        result = self.collection.insert_one(attribute.__dict__)
        return result.inserted_id
    
    def update_attribute(self, attribute_id: ObjectId, updates: Dict[str, Any], user_id: ObjectId) -> bool:
        """Update an existing product attribute."""
        updates['updated_by'] = user_id
        updates['updated_at'] = datetime.utcnow()
        
        # Validate updates
        current_attribute = self.collection.find_one({'_id': attribute_id})
        if not current_attribute:
            return False
        
        # Apply updates for validation
        temp_attribute_data = current_attribute.copy()
        temp_attribute_data.update(updates)
        temp_attribute = ProductAttribute(**temp_attribute_data)
        
        if not self._validate_attribute(temp_attribute):
            raise ValueError("Invalid attribute configuration")
        
        result = self.collection.update_one(
            {'_id': attribute_id},
            {'$set': updates}
        )
        
        # If attribute type or validation rules changed, update existing products
        if 'type' in updates or 'validation_rules' in updates or 'options' in updates:
            self._update_products_with_attribute_changes(attribute_id, updates)
        
        return result.modified_count > 0
    
    def delete_attribute(self, attribute_id: ObjectId, user_id: ObjectId) -> bool:
        """Delete a product attribute."""
        attribute = self.collection.find_one({'_id': attribute_id})
        if not attribute:
            return False
        
        # Check if attribute is used in products
        products_using_attribute = self.products_collection.count_documents({
            f'attributes.{attribute["slug"]}': {'$exists': True}
        })
        
        if products_using_attribute > 0:
            # Option 1: Prevent deletion if in use
            # raise ValueError(f"Cannot delete attribute '{attribute['name']}' - it is used by {products_using_attribute} products")
            
            # Option 2: Remove attribute from all products (chosen approach)
            self.products_collection.update_many(
                {f'attributes.{attribute["slug"]}': {'$exists': True}},
                {'$unset': {f'attributes.{attribute["slug"]}': ""}}
            )
        
        result = self.collection.delete_one({'_id': attribute_id})
        return result.deleted_count > 0
    
    def get_attribute(self, attribute_id: ObjectId) -> Optional[Dict[str, Any]]:
        """Get a single product attribute."""
        return self.collection.find_one({'_id': attribute_id})
    
    def get_attribute_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get a product attribute by slug."""
        return self.collection.find_one({'slug': slug})
    
    def list_attributes(self, filters: Dict[str, Any] = None, 
                       page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """List product attributes with filtering and pagination."""
        query = filters or {}
        skip = (page - 1) * limit
        
        attributes = list(self.collection.find(query).sort('sort_order', 1).skip(skip).limit(limit))
        total = self.collection.count_documents(query)
        
        return {
            'attributes': attributes,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit
        }
    
    def get_attributes_for_category(self, category_id: ObjectId) -> List[Dict[str, Any]]:
        """Get all attributes applicable to a specific category."""
        # Get attributes that apply to this category or all categories
        query = {
            '$or': [
                {'categories': category_id},
                {'categories': {'$size': 0}}  # Attributes that apply to all categories
            ]
        }
        
        return list(self.collection.find(query).sort('sort_order', 1))
    
    def validate_product_attributes(self, product_attributes: Dict[str, Any], 
                                  category_id: ObjectId = None) -> Dict[str, Any]:
        """Validate product attributes against their definitions."""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Get applicable attributes
        if category_id:
            applicable_attributes = self.get_attributes_for_category(category_id)
        else:
            applicable_attributes = list(self.collection.find({}))
        
        attribute_map = {attr['slug']: attr for attr in applicable_attributes}
        
        # Check required attributes
        for attr in applicable_attributes:
            if attr['is_required'] and attr['slug'] not in product_attributes:
                validation_result['errors'].append(f"Required attribute '{attr['name']}' is missing")
                validation_result['valid'] = False
        
        # Validate provided attributes
        for attr_slug, attr_value in product_attributes.items():
            if attr_slug not in attribute_map:
                validation_result['warnings'].append(f"Unknown attribute '{attr_slug}'")
                continue
            
            attr_def = attribute_map[attr_slug]
            attr_validation = self._validate_attribute_value(attr_def, attr_value)
            
            if not attr_validation['valid']:
                validation_result['errors'].extend(attr_validation['errors'])
                validation_result['valid'] = False
        
        return validation_result
    
    def normalize_product_attributes(self, product_attributes: Dict[str, Any], 
                                   category_id: ObjectId = None) -> Dict[str, Any]:
        """Normalize product attributes according to their definitions."""
        if category_id:
            applicable_attributes = self.get_attributes_for_category(category_id)
        else:
            applicable_attributes = list(self.collection.find({}))
        
        attribute_map = {attr['slug']: attr for attr in applicable_attributes}
        normalized_attributes = {}
        
        for attr_slug, attr_value in product_attributes.items():
            if attr_slug in attribute_map:
                attr_def = attribute_map[attr_slug]
                normalized_value = self._normalize_attribute_value(attr_def, attr_value)
                normalized_attributes[attr_slug] = normalized_value
            else:
                # Keep unknown attributes as-is
                normalized_attributes[attr_slug] = attr_value
        
        # Add default values for missing attributes
        for attr in applicable_attributes:
            if attr['slug'] not in normalized_attributes and attr.get('default_value') is not None:
                normalized_attributes[attr['slug']] = attr['default_value']
        
        return normalized_attributes
    
    def get_attribute_usage_stats(self, attribute_id: ObjectId) -> Dict[str, Any]:
        """Get usage statistics for an attribute."""
        attribute = self.collection.find_one({'_id': attribute_id})
        if not attribute:
            return {}
        
        # Count products using this attribute
        products_with_attribute = self.products_collection.count_documents({
            f'attributes.{attribute["slug"]}': {'$exists': True}
        })
        
        # Get value distribution (for select/multiselect attributes)
        value_distribution = {}
        if attribute['type'] in ['select', 'multiselect']:
            pipeline = [
                {'$match': {f'attributes.{attribute["slug"]}': {'$exists': True}}},
                {'$group': {
                    '_id': f'$attributes.{attribute["slug"]}',
                    'count': {'$sum': 1}
                }},
                {'$sort': {'count': -1}}
            ]
            
            results = list(self.products_collection.aggregate(pipeline))
            value_distribution = {result['_id']: result['count'] for result in results}
        
        return {
            'attribute_id': attribute_id,
            'attribute_name': attribute['name'],
            'products_using': products_with_attribute,
            'value_distribution': value_distribution,
            'usage_percentage': (products_with_attribute / max(1, self.products_collection.count_documents({}))) * 100
        }
    
    def bulk_update_attribute_values(self, attribute_id: ObjectId, 
                                   value_mapping: Dict[str, Any], user_id: ObjectId) -> Dict[str, Any]:
        """Bulk update attribute values across products."""
        attribute = self.collection.find_one({'_id': attribute_id})
        if not attribute:
            return {'success': False, 'error': 'Attribute not found'}
        
        results = {
            'success': True,
            'products_updated': 0,
            'errors': []
        }
        
        for old_value, new_value in value_mapping.items():
            try:
                # Validate new value
                validation = self._validate_attribute_value(attribute, new_value)
                if not validation['valid']:
                    results['errors'].append(f"Invalid new value '{new_value}': {', '.join(validation['errors'])}")
                    continue
                
                # Update products with this attribute value
                update_result = self.products_collection.update_many(
                    {f'attributes.{attribute["slug"]}': old_value},
                    {
                        '$set': {
                            f'attributes.{attribute["slug"]}': new_value,
                            'updated_at': datetime.utcnow(),
                            'updated_by': user_id
                        }
                    }
                )
                
                results['products_updated'] += update_result.modified_count
                
            except Exception as e:
                results['errors'].append(f"Error updating '{old_value}' to '{new_value}': {str(e)}")
        
        if results['errors']:
            results['success'] = len(results['errors']) == 0
        
        return results
    
    def reorder_attributes(self, attribute_orders: List[Dict[str, Any]], user_id: ObjectId) -> bool:
        """Reorder attributes by updating their sort_order values."""
        try:
            for order_data in attribute_orders:
                attribute_id = ObjectId(order_data['attribute_id'])
                sort_order = order_data['sort_order']
                
                self.collection.update_one(
                    {'_id': attribute_id},
                    {
                        '$set': {
                            'sort_order': sort_order,
                            'updated_by': user_id,
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
            
            return True
        except Exception:
            return False
    
    # Private methods
    
    def _validate_attribute(self, attribute: ProductAttribute) -> bool:
        """Validate an attribute configuration."""
        # Check required fields
        if not attribute.name or not attribute.type:
            return False
        
        # Validate attribute type
        valid_types = ['text', 'number', 'boolean', 'select', 'multiselect', 'date', 'url', 'email']
        if attribute.type not in valid_types:
            return False
        
        # Validate options for select/multiselect types
        if attribute.type in ['select', 'multiselect']:
            if not attribute.options or len(attribute.options) == 0:
                return False
        
        # Validate validation rules
        if attribute.validation_rules:
            if not self._validate_validation_rules(attribute.type, attribute.validation_rules):
                return False
        
        return True
    
    def _validate_validation_rules(self, attribute_type: str, validation_rules: Dict[str, Any]) -> bool:
        """Validate the validation rules for an attribute type."""
        valid_rules = {
            'text': ['min_length', 'max_length', 'pattern', 'required'],
            'number': ['min_value', 'max_value', 'decimal_places', 'required'],
            'boolean': ['required'],
            'select': ['required'],
            'multiselect': ['min_selections', 'max_selections', 'required'],
            'date': ['min_date', 'max_date', 'required'],
            'url': ['required'],
            'email': ['required']
        }
        
        allowed_rules = valid_rules.get(attribute_type, [])
        
        for rule_name in validation_rules.keys():
            if rule_name not in allowed_rules:
                return False
        
        return True
    
    def _validate_attribute_value(self, attribute_def: Dict[str, Any], value: Any) -> Dict[str, Any]:
        """Validate a single attribute value against its definition."""
        validation_result = {'valid': True, 'errors': []}
        
        attr_type = attribute_def['type']
        validation_rules = attribute_def.get('validation_rules', {})
        
        # Check if required
        if validation_rules.get('required', False) and (value is None or value == ''):
            validation_result['errors'].append(f"Attribute '{attribute_def['name']}' is required")
            validation_result['valid'] = False
            return validation_result
        
        # Skip validation if value is empty and not required
        if value is None or value == '':
            return validation_result
        
        # Type-specific validation
        if attr_type == 'text':
            if not isinstance(value, str):
                validation_result['errors'].append("Value must be a string")
                validation_result['valid'] = False
            else:
                if 'min_length' in validation_rules and len(value) < validation_rules['min_length']:
                    validation_result['errors'].append(f"Value must be at least {validation_rules['min_length']} characters")
                    validation_result['valid'] = False
                
                if 'max_length' in validation_rules and len(value) > validation_rules['max_length']:
                    validation_result['errors'].append(f"Value must be at most {validation_rules['max_length']} characters")
                    validation_result['valid'] = False
                
                if 'pattern' in validation_rules:
                    pattern = validation_rules['pattern']
                    if not re.match(pattern, value):
                        validation_result['errors'].append(f"Value does not match required pattern")
                        validation_result['valid'] = False
        
        elif attr_type == 'number':
            try:
                numeric_value = float(value)
                
                if 'min_value' in validation_rules and numeric_value < validation_rules['min_value']:
                    validation_result['errors'].append(f"Value must be at least {validation_rules['min_value']}")
                    validation_result['valid'] = False
                
                if 'max_value' in validation_rules and numeric_value > validation_rules['max_value']:
                    validation_result['errors'].append(f"Value must be at most {validation_rules['max_value']}")
                    validation_result['valid'] = False
                
            except (ValueError, TypeError):
                validation_result['errors'].append("Value must be a number")
                validation_result['valid'] = False
        
        elif attr_type == 'boolean':
            if not isinstance(value, bool):
                validation_result['errors'].append("Value must be true or false")
                validation_result['valid'] = False
        
        elif attr_type == 'select':
            if value not in attribute_def.get('options', []):
                validation_result['errors'].append(f"Value must be one of: {', '.join(attribute_def.get('options', []))}")
                validation_result['valid'] = False
        
        elif attr_type == 'multiselect':
            if not isinstance(value, list):
                validation_result['errors'].append("Value must be a list")
                validation_result['valid'] = False
            else:
                options = attribute_def.get('options', [])
                for item in value:
                    if item not in options:
                        validation_result['errors'].append(f"'{item}' is not a valid option")
                        validation_result['valid'] = False
                
                if 'min_selections' in validation_rules and len(value) < validation_rules['min_selections']:
                    validation_result['errors'].append(f"Must select at least {validation_rules['min_selections']} options")
                    validation_result['valid'] = False
                
                if 'max_selections' in validation_rules and len(value) > validation_rules['max_selections']:
                    validation_result['errors'].append(f"Must select at most {validation_rules['max_selections']} options")
                    validation_result['valid'] = False
        
        elif attr_type == 'email':
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, str(value)):
                validation_result['errors'].append("Value must be a valid email address")
                validation_result['valid'] = False
        
        elif attr_type == 'url':
            url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
            if not re.match(url_pattern, str(value)):
                validation_result['errors'].append("Value must be a valid URL")
                validation_result['valid'] = False
        
        return validation_result
    
    def _normalize_attribute_value(self, attribute_def: Dict[str, Any], value: Any) -> Any:
        """Normalize an attribute value according to its type."""
        attr_type = attribute_def['type']
        
        if value is None or value == '':
            return value
        
        if attr_type == 'text':
            return str(value).strip()
        
        elif attr_type == 'number':
            try:
                return float(value)
            except (ValueError, TypeError):
                return value
        
        elif attr_type == 'boolean':
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                return value.lower() in ['true', '1', 'yes', 'on']
            else:
                return bool(value)
        
        elif attr_type in ['select', 'multiselect']:
            return value
        
        elif attr_type == 'email':
            return str(value).strip().lower()
        
        elif attr_type == 'url':
            url = str(value).strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            return url
        
        return value
    
    def _generate_attribute_slug(self, name: str) -> str:
        """Generate a URL-friendly slug for an attribute."""
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name.lower())
        slug = re.sub(r'\s+', '_', slug.strip())
        
        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while self.collection.find_one({'slug': slug}):
            slug = f"{base_slug}_{counter}"
            counter += 1
        
        return slug
    
    def _update_products_with_attribute_changes(self, attribute_id: ObjectId, updates: Dict[str, Any]):
        """Update products when attribute definition changes."""
        attribute = self.collection.find_one({'_id': attribute_id})
        if not attribute:
            return
        
        # If attribute type changed, we might need to convert values
        if 'type' in updates:
            # This is a complex operation that would require careful handling
            # For now, we'll just log that products need manual review
            pass
        
        # If options changed for select/multiselect, validate existing values
        if 'options' in updates and attribute['type'] in ['select', 'multiselect']:
            new_options = updates['options']
            
            # Find products with invalid values
            if attribute['type'] == 'select':
                invalid_products = self.products_collection.find({
                    f'attributes.{attribute["slug"]}': {'$nin': new_options}
                })
            else:  # multiselect
                invalid_products = self.products_collection.find({
                    f'attributes.{attribute["slug"]}': {'$not': {'$all': new_options}}
                })
            
            # For now, we'll leave invalid values as-is
            # In a production system, you might want to:
            # 1. Remove invalid values
            # 2. Set to default value
            # 3. Flag for manual review