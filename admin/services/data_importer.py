"""
Data Importer Service
Handles data import operations with validation and duplicate detection
"""

import csv
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from bson import ObjectId
import hashlib
import re

from .base_service import BaseService
from ..models.product import DataImport, ImportStatus, Product, ProductStatus


class DataImporter(BaseService):
    """Service for importing product data with validation and duplicate detection."""
    
    def __init__(self, db):
        self.products_collection = db.products
        self.categories_collection = db.product_categories
        super().__init__(db)
        
        # Define required fields for product import
        self.required_fields = ['name', 'price', 'category']
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'data_imports'
        
        # Define field mappings for common variations
        self.field_mappings = {
            'product_name': 'name',
            'title': 'name',
            'product_title': 'name',
            'cost': 'price',
            'amount': 'price',
            'product_price': 'price',
            'category_name': 'category',
            'product_category': 'category',
            'description': 'description',
            'product_description': 'description',
            'stock': 'inventory_stock',
            'quantity': 'inventory_stock',
            'inventory': 'inventory_stock',
            'sku': 'sku',
            'product_code': 'sku',
            'weight': 'shipping_weight',
            'dimensions': 'shipping_dimensions',
            'brand': 'brand',
            'manufacturer': 'brand',
            'tags': 'tags',
            'keywords': 'tags'
        }
    
    def create_import(self, filename: str, file_size: int, file_type: str, 
                     mapping: Dict[str, str], options: Dict[str, Any], 
                     user_id: ObjectId) -> ObjectId:
        """Create a new data import record."""
        data_import = DataImport(
            filename=filename,
            file_size=file_size,
            file_type=file_type,
            mapping=mapping,
            options=options,
            created_by=user_id,
            created_at=datetime.utcnow()
        )
        
        result = self.collection.insert_one(data_import.__dict__)
        return result.inserted_id
    
    def process_import(self, import_id: ObjectId, file_data: bytes) -> bool:
        """Process a data import with validation and duplicate detection."""
        import_record = self.collection.find_one({'_id': import_id})
        if not import_record:
            return False
        
        # Update status to processing
        self._update_import_status(import_id, ImportStatus.PROCESSING, started_at=datetime.utcnow())
        
        try:
            # Parse file data
            parsed_data = self._parse_file_data(file_data, import_record['file_type'])
            if not parsed_data:
                self._update_import_status(import_id, ImportStatus.FAILED, 
                                         completed_at=datetime.utcnow())
                self._add_import_error(import_id, "Failed to parse file data")
                return False
            
            # Update total rows
            self.collection.update_one(
                {'_id': import_id},
                {'$set': {'total_rows': len(parsed_data)}}
            )
            
            # Process each row
            successful_rows = 0
            failed_rows = 0
            duplicates_found = 0
            processed_rows = 0
            
            for row_index, row_data in enumerate(parsed_data):
                try:
                    # Map fields according to user mapping
                    mapped_data = self._map_row_data(row_data, import_record['mapping'])
                    
                    # Validate row data
                    validation_result = self._validate_row_data(mapped_data, row_index + 1)
                    if not validation_result['valid']:
                        failed_rows += 1
                        for error in validation_result['errors']:
                            self._add_validation_error(import_id, row_index + 1, error)
                        continue
                    
                    # Check for duplicates
                    duplicate_check = self._check_for_duplicates(mapped_data, import_record['options'])
                    if duplicate_check['is_duplicate']:
                        duplicates_found += 1
                        action = import_record['options'].get('duplicate_action', 'skip')
                        
                        if action == 'skip':
                            self._add_import_log(import_id, f"Row {row_index + 1}: Skipped duplicate product")
                            continue
                        elif action == 'update':
                            # Update existing product
                            if self._update_existing_product(duplicate_check['product_id'], mapped_data):
                                successful_rows += 1
                                self._add_import_log(import_id, f"Row {row_index + 1}: Updated existing product")
                            else:
                                failed_rows += 1
                                self._add_import_log(import_id, f"Row {row_index + 1}: Failed to update existing product")
                            continue
                    
                    # Create new product
                    product_data = self._build_product_data(mapped_data, import_record['created_by'])
                    if self._create_product(product_data):
                        successful_rows += 1
                        self._add_import_log(import_id, f"Row {row_index + 1}: Created new product")
                    else:
                        failed_rows += 1
                        self._add_import_log(import_id, f"Row {row_index + 1}: Failed to create product")
                    
                except Exception as e:
                    failed_rows += 1
                    self._add_import_log(import_id, f"Row {row_index + 1}: Error - {str(e)}")
                
                processed_rows += 1
                
                # Update progress periodically
                if processed_rows % 10 == 0:
                    self._update_import_progress(import_id, processed_rows, successful_rows, 
                                               failed_rows, duplicates_found)
            
            # Final progress update
            self._update_import_progress(import_id, processed_rows, successful_rows, 
                                       failed_rows, duplicates_found)
            
            # Determine final status
            if failed_rows == 0:
                final_status = ImportStatus.COMPLETED
            elif successful_rows > 0:
                final_status = ImportStatus.PARTIAL
            else:
                final_status = ImportStatus.FAILED
            
            self._update_import_status(import_id, final_status, completed_at=datetime.utcnow())
            return True
            
        except Exception as e:
            self._update_import_status(import_id, ImportStatus.FAILED, completed_at=datetime.utcnow())
            self._add_import_error(import_id, f"Import processing failed: {str(e)}")
            return False
    
    def get_import_status(self, import_id: ObjectId) -> Optional[Dict[str, Any]]:
        """Get the status of a data import."""
        return self.collection.find_one({'_id': import_id})
    
    def list_imports(self, user_id: Optional[ObjectId] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List data imports, optionally filtered by user."""
        query = {}
        if user_id:
            query['created_by'] = user_id
        
        return list(self.collection.find(query).sort('created_at', -1).limit(limit))
    
    def get_field_mapping_suggestions(self, sample_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Suggest field mappings based on sample data."""
        if not sample_data:
            return {}
        
        suggestions = {}
        sample_fields = set()
        
        # Collect all field names from sample data
        for row in sample_data[:5]:  # Use first 5 rows for analysis
            sample_fields.update(row.keys())
        
        # Suggest mappings based on field names
        for field in sample_fields:
            field_lower = field.lower().strip()
            
            # Direct mapping
            if field_lower in self.field_mappings:
                suggestions[field] = self.field_mappings[field_lower]
            else:
                # Fuzzy matching for common patterns
                for pattern, target in self.field_mappings.items():
                    if pattern in field_lower or field_lower in pattern:
                        suggestions[field] = target
                        break
        
        return suggestions
    
    def validate_import_data(self, sample_data: List[Dict[str, Any]], 
                           mapping: Dict[str, str]) -> Dict[str, Any]:
        """Validate sample import data and return validation results."""
        if not sample_data:
            return {'valid': False, 'errors': ['No data provided']}
        
        errors = []
        warnings = []
        
        # Check required fields
        mapped_fields = set(mapping.values())
        missing_required = set(self.required_fields) - mapped_fields
        if missing_required:
            errors.append(f"Missing required fields: {', '.join(missing_required)}")
        
        # Validate sample rows
        for i, row in enumerate(sample_data[:10]):  # Validate first 10 rows
            mapped_row = self._map_row_data(row, mapping)
            validation_result = self._validate_row_data(mapped_row, i + 1)
            
            if not validation_result['valid']:
                errors.extend([f"Row {i + 1}: {error}" for error in validation_result['errors']])
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'sample_count': len(sample_data)
        }
    
    # Private methods
    
    def _parse_file_data(self, file_data: bytes, file_type: str) -> Optional[List[Dict[str, Any]]]:
        """Parse file data based on file type."""
        try:
            if file_type.lower() == 'csv':
                # Decode bytes to string
                content = file_data.decode('utf-8')
                reader = csv.DictReader(content.splitlines())
                return list(reader)
            
            elif file_type.lower() == 'json':
                content = file_data.decode('utf-8')
                data = json.loads(content)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and 'products' in data:
                    return data['products']
                else:
                    return [data]
            
            elif file_type.lower() in ['xlsx', 'xls']:
                # Use pandas to read Excel files
                df = pd.read_excel(file_data)
                return df.to_dict('records')
            
            else:
                return None
                
        except Exception as e:
            return None
    
    def _map_row_data(self, row_data: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """Map row data according to user-defined field mapping."""
        mapped_data = {}
        
        for source_field, target_field in mapping.items():
            if source_field in row_data:
                mapped_data[target_field] = row_data[source_field]
        
        return mapped_data
    
    def _validate_row_data(self, data: Dict[str, Any], row_number: int) -> Dict[str, Any]:
        """Validate a single row of mapped data."""
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate specific fields
        if 'price' in data:
            try:
                price = float(data['price'])
                if price < 0:
                    errors.append("Price cannot be negative")
            except (ValueError, TypeError):
                errors.append("Invalid price format")
        
        if 'inventory_stock' in data:
            try:
                stock = int(data['inventory_stock'])
                if stock < 0:
                    errors.append("Stock cannot be negative")
            except (ValueError, TypeError):
                errors.append("Invalid stock format")
        
        # Validate name length
        if 'name' in data and len(str(data['name'])) > 200:
            errors.append("Product name too long (max 200 characters)")
        
        # Validate category exists
        if 'category' in data:
            category_name = str(data['category']).strip()
            if not self.categories_collection.find_one({'name': category_name}):
                errors.append(f"Category '{category_name}' does not exist")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _check_for_duplicates(self, data: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """Check for duplicate products based on configured criteria."""
        duplicate_criteria = options.get('duplicate_criteria', ['name', 'sku'])
        
        query_conditions = []
        
        for criterion in duplicate_criteria:
            if criterion in data and data[criterion]:
                if criterion == 'name':
                    # Case-insensitive name matching
                    query_conditions.append({'basic_info.name': {'$regex': f'^{re.escape(str(data[criterion]))}$', '$options': 'i'}})
                elif criterion == 'sku':
                    query_conditions.append({'basic_info.sku': str(data[criterion])})
        
        if not query_conditions:
            return {'is_duplicate': False}
        
        # Use OR condition if multiple criteria
        if len(query_conditions) == 1:
            query = query_conditions[0]
        else:
            query = {'$or': query_conditions}
        
        existing_product = self.products_collection.find_one(query)
        
        return {
            'is_duplicate': existing_product is not None,
            'product_id': existing_product['_id'] if existing_product else None
        }
    
    def _build_product_data(self, mapped_data: Dict[str, Any], user_id: ObjectId) -> Dict[str, Any]:
        """Build product data structure from mapped import data."""
        now = datetime.utcnow()
        
        # Find or create category
        category_id = None
        if 'category' in mapped_data:
            category = self.categories_collection.find_one({'name': mapped_data['category']})
            if category:
                category_id = category['_id']
        
        product_data = {
            'basic_info': {
                'name': mapped_data.get('name', ''),
                'description': mapped_data.get('description', ''),
                'sku': mapped_data.get('sku', ''),
                'brand': mapped_data.get('brand', ''),
                'model': mapped_data.get('model', ''),
                'condition': mapped_data.get('condition', 'new')
            },
            'category_id': category_id,
            'pricing': {
                'price': float(mapped_data.get('price', 0)),
                'compare_price': float(mapped_data.get('compare_price', 0)) if mapped_data.get('compare_price') else None,
                'cost_price': float(mapped_data.get('cost_price', 0)) if mapped_data.get('cost_price') else None,
                'currency': mapped_data.get('currency', 'USD')
            },
            'inventory': {
                'stock': int(mapped_data.get('inventory_stock', 0)),
                'low_stock_threshold': int(mapped_data.get('low_stock_threshold', 10)),
                'track_inventory': mapped_data.get('track_inventory', True),
                'allow_backorders': mapped_data.get('allow_backorders', False)
            },
            'shipping': {
                'weight': float(mapped_data.get('shipping_weight', 0)) if mapped_data.get('shipping_weight') else None,
                'dimensions': mapped_data.get('shipping_dimensions', ''),
                'requires_shipping': mapped_data.get('requires_shipping', True)
            },
            'status': ProductStatus.DRAFT.value,
            'is_featured': mapped_data.get('is_featured', False),
            'tags': self._parse_tags(mapped_data.get('tags', '')),
            'created_by': user_id,
            'updated_by': user_id,
            'created_at': now,
            'updated_at': now
        }
        
        return product_data
    
    def _parse_tags(self, tags_string: str) -> List[str]:
        """Parse tags from a string (comma or semicolon separated)."""
        if not tags_string:
            return []
        
        # Split by comma or semicolon and clean up
        tags = re.split(r'[,;]', str(tags_string))
        return [tag.strip() for tag in tags if tag.strip()]
    
    def _create_product(self, product_data: Dict[str, Any]) -> bool:
        """Create a new product from import data."""
        try:
            result = self.products_collection.insert_one(product_data)
            return result.inserted_id is not None
        except Exception:
            return False
    
    def _update_existing_product(self, product_id: ObjectId, mapped_data: Dict[str, Any]) -> bool:
        """Update an existing product with import data."""
        try:
            update_data = {
                'updated_at': datetime.utcnow()
            }
            
            # Update basic info
            if 'name' in mapped_data:
                update_data['basic_info.name'] = mapped_data['name']
            if 'description' in mapped_data:
                update_data['basic_info.description'] = mapped_data['description']
            if 'price' in mapped_data:
                update_data['pricing.price'] = float(mapped_data['price'])
            if 'inventory_stock' in mapped_data:
                update_data['inventory.stock'] = int(mapped_data['inventory_stock'])
            
            result = self.products_collection.update_one(
                {'_id': product_id},
                {'$set': update_data}
            )
            
            return result.modified_count > 0
        except Exception:
            return False
    
    # Helper methods for tracking import progress
    
    def _update_import_status(self, import_id: ObjectId, status: ImportStatus, **kwargs):
        """Update import status."""
        update_data = {'status': status.value}
        update_data.update(kwargs)
        
        self.collection.update_one(
            {'_id': import_id},
            {'$set': update_data}
        )
    
    def _update_import_progress(self, import_id: ObjectId, processed: int, successful: int, 
                              failed: int, duplicates: int):
        """Update import progress."""
        self.collection.update_one(
            {'_id': import_id},
            {
                '$set': {
                    'processed_rows': processed,
                    'successful_rows': successful,
                    'failed_rows': failed,
                    'duplicates_found': duplicates
                }
            }
        )
    
    def _add_validation_error(self, import_id: ObjectId, row_number: int, error: str):
        """Add a validation error."""
        self.collection.update_one(
            {'_id': import_id},
            {
                '$push': {
                    'validation_errors': {
                        'row': row_number,
                        'error': error,
                        'timestamp': datetime.utcnow()
                    }
                }
            }
        )
    
    def _add_import_log(self, import_id: ObjectId, message: str):
        """Add a log entry."""
        self.collection.update_one(
            {'_id': import_id},
            {
                '$push': {
                    'import_log': {
                        'message': message,
                        'timestamp': datetime.utcnow()
                    }
                }
            }
        )
    
    def _add_import_error(self, import_id: ObjectId, error: str):
        """Add an import error."""
        self._add_import_log(import_id, f"ERROR: {error}")