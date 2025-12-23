"""
Content management models
"""

from datetime import datetime
from typing import Any, Dict, Optional, List
from bson import ObjectId
from .base import BaseModel


class ContentVersion(BaseModel):
    """Model for content version history."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.element_id: str = kwargs.get('element_id', '')
        self.content: str = kwargs.get('content', '')
        self.content_type: str = kwargs.get('content_type', 'html')  # html, text, markdown
        self.version_number: int = kwargs.get('version_number', 1)
        self.is_published: bool = kwargs.get('is_published', False)
        self.metadata: Dict[str, Any] = kwargs.get('metadata', {})
        self.change_summary: str = kwargs.get('change_summary', '')
        
        # Handle parent_version_id conversion from string to ObjectId if needed
        parent_id = kwargs.get('parent_version_id')
        if parent_id is not None:
            if isinstance(parent_id, str):
                try:
                    self.parent_version_id = ObjectId(parent_id)
                except:
                    self.parent_version_id = None
            else:
                self.parent_version_id = parent_id
        else:
            self.parent_version_id = None
    
    def get_content_preview(self, max_length: int = 100) -> str:
        """Get a preview of the content."""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."


class MediaAsset(BaseModel):
    """Model for media assets (images, videos, documents)."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filename: str = kwargs.get('filename', '')
        self.original_filename: str = kwargs.get('original_filename', '')
        self.file_path: str = kwargs.get('file_path', '')
        self.file_size: int = kwargs.get('file_size', 0)
        self.mime_type: str = kwargs.get('mime_type', '')
        self.file_type: str = kwargs.get('file_type', '')  # image, video, document
        self.dimensions: Optional[Dict[str, int]] = kwargs.get('dimensions')  # width, height for images
        self.variants: List[Dict[str, Any]] = kwargs.get('variants', [])  # different sizes/formats
        self.alt_text: str = kwargs.get('alt_text', '')
        self.tags: List[str] = kwargs.get('tags', [])
        self.usage_count: int = kwargs.get('usage_count', 0)
        self.is_optimized: bool = kwargs.get('is_optimized', False)
    
    def add_variant(self, variant_data: Dict[str, Any]) -> None:
        """Add a new variant of this media asset."""
        self.variants.append({
            'name': variant_data.get('name', ''),
            'file_path': variant_data.get('file_path', ''),
            'dimensions': variant_data.get('dimensions'),
            'file_size': variant_data.get('file_size', 0),
            'format': variant_data.get('format', ''),
            'created_at': datetime.utcnow()
        })
    
    def get_variant(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific variant by name."""
        for variant in self.variants:
            if variant.get('name') == name:
                return variant
        return None
    
    def increment_usage(self) -> None:
        """Increment the usage count for this asset."""
        self.usage_count += 1
        self.updated_at = datetime.utcnow()