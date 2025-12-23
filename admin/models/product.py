"""
Product Management Models
Data models for product and inventory management in the admin system
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from bson import ObjectId
from enum import Enum
from .base import BaseModel


class ProductStatus(Enum):
    """Product status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"
    OUT_OF_STOCK = "out_of_stock"


class BulkOperationType(Enum):
    """Types of bulk operations that can be performed on products."""
    UPDATE_PRICE = "update_price"
    UPDATE_CATEGORY = "update_category"
    UPDATE_STATUS = "update_status"
    UPDATE_INVENTORY = "update_inventory"
    DELETE = "delete"
    DUPLICATE = "duplicate"
    EXPORT = "export"


class ImportStatus(Enum):
    """Status of data import operations."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class RuleConditionType(Enum):
    """Types of conditions for automation rules."""
    INVENTORY_LEVEL = "inventory_level"
    PRICE_RANGE = "price_range"
    CATEGORY = "category"
    VENDOR = "vendor"
    DATE_RANGE = "date_range"
    SALES_VOLUME = "sales_volume"


class RuleActionType(Enum):
    """Types of actions for automation rules."""
    UPDATE_PRICE = "update_price"
    UPDATE_INVENTORY = "update_inventory"
    CHANGE_STATUS = "change_status"
    SEND_NOTIFICATION = "send_notification"
    CREATE_PROMOTION = "create_promotion"


class Product(BaseModel):
    """Product model for admin management."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vendor_id: ObjectId = kwargs.get('vendor_id')
        self.basic_info: Dict[str, Any] = kwargs.get('basic_info', {})
        self.category_id: ObjectId = kwargs.get('category_id')
        self.category_path: List[str] = kwargs.get('category_path', [])
        self.pricing: Dict[str, Any] = kwargs.get('pricing', {})
        self.inventory: Dict[str, Any] = kwargs.get('inventory', {})
        self.attributes: Dict[str, Any] = kwargs.get('attributes', {})
        self.media: List[Dict[str, Any]] = kwargs.get('media', [])
        self.seo: Dict[str, Any] = kwargs.get('seo', {})
        self.status: ProductStatus = ProductStatus(kwargs.get('status', ProductStatus.DRAFT.value))
        self.is_featured: bool = kwargs.get('is_featured', False)
        self.tags: List[str] = kwargs.get('tags', [])
        self.variants: List[Dict[str, Any]] = kwargs.get('variants', [])
        self.shipping: Dict[str, Any] = kwargs.get('shipping', {})
        self.analytics: Dict[str, Any] = kwargs.get('analytics', {})


class ProductCategory(BaseModel):
    """Product category model with hierarchical support."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name: str = kwargs.get('name', '')
        self.slug: str = kwargs.get('slug', '')
        self.description: str = kwargs.get('description', '')
        self.parent_id: Optional[ObjectId] = kwargs.get('parent_id')
        self.path: List[str] = kwargs.get('path', [])
        self.level: int = kwargs.get('level', 0)
        self.sort_order: int = kwargs.get('sort_order', 0)
        self.icon: str = kwargs.get('icon', '')
        self.color: str = kwargs.get('color', '')
        self.is_active: bool = kwargs.get('is_active', True)
        self.seo: Dict[str, Any] = kwargs.get('seo', {})
        self.product_count: int = kwargs.get('product_count', 0)
        self.children: List[ObjectId] = kwargs.get('children', [])


class BulkOperation(BaseModel):
    """Model for tracking bulk operations on products."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.operation_type: BulkOperationType = BulkOperationType(kwargs.get('operation_type'))
        self.product_ids: List[ObjectId] = kwargs.get('product_ids', [])
        self.parameters: Dict[str, Any] = kwargs.get('parameters', {})
        self.status: str = kwargs.get('status', 'pending')
        self.progress: int = kwargs.get('progress', 0)
        self.total_items: int = kwargs.get('total_items', 0)
        self.processed_items: int = kwargs.get('processed_items', 0)
        self.failed_items: int = kwargs.get('failed_items', 0)
        self.results: List[Dict[str, Any]] = kwargs.get('results', [])
        self.errors: List[Dict[str, Any]] = kwargs.get('errors', [])
        self.started_at: Optional[datetime] = kwargs.get('started_at')
        self.completed_at: Optional[datetime] = kwargs.get('completed_at')
        self.created_by: ObjectId = kwargs.get('created_by')


class DataImport(BaseModel):
    """Model for tracking data import operations."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filename: str = kwargs.get('filename', '')
        self.file_size: int = kwargs.get('file_size', 0)
        self.file_type: str = kwargs.get('file_type', '')
        self.status: ImportStatus = ImportStatus(kwargs.get('status', ImportStatus.PENDING.value))
        self.total_rows: int = kwargs.get('total_rows', 0)
        self.processed_rows: int = kwargs.get('processed_rows', 0)
        self.successful_rows: int = kwargs.get('successful_rows', 0)
        self.failed_rows: int = kwargs.get('failed_rows', 0)
        self.duplicates_found: int = kwargs.get('duplicates_found', 0)
        self.validation_errors: List[Dict[str, Any]] = kwargs.get('validation_errors', [])
        self.import_log: List[Dict[str, Any]] = kwargs.get('import_log', [])
        self.mapping: Dict[str, str] = kwargs.get('mapping', {})
        self.options: Dict[str, Any] = kwargs.get('options', {})
        self.started_at: Optional[datetime] = kwargs.get('started_at')
        self.completed_at: Optional[datetime] = kwargs.get('completed_at')
        self.created_by: ObjectId = kwargs.get('created_by')


class AutomationRule(BaseModel):
    """Model for automation rules that apply to products."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name: str = kwargs.get('name', '')
        self.description: str = kwargs.get('description', '')
        self.is_active: bool = kwargs.get('is_active', True)
        self.priority: int = kwargs.get('priority', 0)
        self.conditions: List[Dict[str, Any]] = kwargs.get('conditions', [])
        self.actions: List[Dict[str, Any]] = kwargs.get('actions', [])
        self.schedule: Dict[str, Any] = kwargs.get('schedule', {})
        self.last_executed: Optional[datetime] = kwargs.get('last_executed')
        self.execution_count: int = kwargs.get('execution_count', 0)
        self.success_count: int = kwargs.get('success_count', 0)
        self.failure_count: int = kwargs.get('failure_count', 0)
        self.created_by: ObjectId = kwargs.get('created_by')


class ProductAttribute(BaseModel):
    """Model for product attributes and their definitions."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name: str = kwargs.get('name', '')
        self.slug: str = kwargs.get('slug', '')
        self.type: str = kwargs.get('type', 'text')  # text, number, boolean, select, multiselect
        self.is_required: bool = kwargs.get('is_required', False)
        self.is_filterable: bool = kwargs.get('is_filterable', False)
        self.is_searchable: bool = kwargs.get('is_searchable', False)
        self.sort_order: int = kwargs.get('sort_order', 0)
        self.options: List[str] = kwargs.get('options', [])
        self.validation_rules: Dict[str, Any] = kwargs.get('validation_rules', {})
        self.categories: List[ObjectId] = kwargs.get('categories', [])  # Categories this attribute applies to
        self.default_value: Any = kwargs.get('default_value')
        self.unit: str = kwargs.get('unit', '')
        self.description: str = kwargs.get('description', '')


class InventoryTransaction(BaseModel):
    """Model for tracking inventory changes."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.product_id: ObjectId = kwargs.get('product_id')
        self.variant_id: Optional[ObjectId] = kwargs.get('variant_id')
        self.transaction_type: str = kwargs.get('transaction_type')  # adjustment, sale, return, restock
        self.quantity_change: int = kwargs.get('quantity_change', 0)
        self.previous_quantity: int = kwargs.get('previous_quantity', 0)
        self.new_quantity: int = kwargs.get('new_quantity', 0)
        self.reason: str = kwargs.get('reason', '')
        self.reference_id: Optional[ObjectId] = kwargs.get('reference_id')  # Order ID, etc.
        self.notes: str = kwargs.get('notes', '')
        self.created_by: ObjectId = kwargs.get('created_by')