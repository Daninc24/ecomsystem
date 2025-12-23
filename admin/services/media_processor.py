"""
Media Processing Service
Handles image optimization and format generation
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from ..models.content import MediaAsset
from ..database.collections import get_collection


class MediaProcessor:
    """Handles media asset processing, optimization, and format generation."""
    
    def __init__(self, db):
        self.db = db
        self.media_assets = get_collection(db, 'media_assets')
        self.upload_path = "static/uploads"
        self.supported_image_formats = ['jpg', 'jpeg', 'png', 'gif', 'webp']
        self.supported_video_formats = ['mp4', 'webm', 'ogg']
        self.supported_document_formats = ['pdf', 'doc', 'docx', 'txt']
    
    def upload_media(self, file_data: bytes, filename: str, mime_type: str,
                    user_id: ObjectId = None, alt_text: str = "", 
                    tags: List[str] = None) -> ObjectId:
        """Upload and process a media file."""
        if tags is None:
            tags = []
        
        # Determine file type and extension
        file_extension = filename.split('.')[-1].lower() if '.' in filename else ''
        file_type = self._determine_file_type(file_extension, mime_type)
        
        # Generate unique filename
        unique_filename = f"{ObjectId()}_{filename}"
        file_path = os.path.join(self.upload_path, unique_filename)
        
        # Create media asset record
        media_asset = MediaAsset(
            filename=unique_filename,
            original_filename=filename,
            file_path=file_path,
            file_size=len(file_data),
            mime_type=mime_type,
            file_type=file_type,
            alt_text=alt_text,
            tags=tags,
            is_optimized=False,
            created_by=user_id or ObjectId(),
            updated_by=user_id or ObjectId()
        )
        
        # For images, extract dimensions (simulated)
        if file_type == 'image':
            media_asset.dimensions = self._extract_image_dimensions(file_data, file_extension)
        
        # Save to database
        asset_data = media_asset.to_dict()
        result = self.media_assets.insert_one(asset_data)
        asset_id = result.inserted_id
        
        # Process and optimize the media
        self._process_media_file(asset_id, file_data, file_extension)
        
        return asset_id
    
    def optimize_media(self, asset_id: ObjectId) -> List[Dict[str, Any]]:
        """Optimize a media asset and generate variants."""
        asset_data = self.media_assets.find_one({'_id': asset_id})
        if not asset_data:
            return []
        
        asset = MediaAsset(**asset_data)
        variants = []
        
        if asset.file_type == 'image':
            variants = self._generate_image_variants(asset)
        elif asset.file_type == 'video':
            variants = self._generate_video_variants(asset)
        elif asset.file_type == 'document':
            # For documents, we don't generate variants but still mark as optimized
            variants = []
        
        # Update asset with variants and mark as optimized
        if variants:
            for variant in variants:
                asset.add_variant(variant)
        
        # Mark as optimized regardless of whether variants were generated
        asset.is_optimized = True
        asset.updated_at = datetime.utcnow()
        
        # Save updated asset
        self.media_assets.update_one(
            {'_id': asset_id},
            {'$set': {
                'variants': asset.variants,
                'is_optimized': asset.is_optimized,
                'updated_at': asset.updated_at
            }}
        )
        
        return variants
    
    def get_media_asset(self, asset_id: ObjectId) -> Optional[MediaAsset]:
        """Get a media asset by ID."""
        asset_data = self.media_assets.find_one({'_id': asset_id})
        if asset_data:
            return MediaAsset(**asset_data)
        return None
    
    def get_media_by_tags(self, tags: List[str]) -> List[MediaAsset]:
        """Get media assets by tags."""
        assets_data = list(self.media_assets.find({
            'tags': {'$in': tags}
        }).sort('created_at', -1))
        
        return [MediaAsset(**data) for data in assets_data]
    
    def update_media_metadata(self, asset_id: ObjectId, alt_text: str = None,
                             tags: List[str] = None, user_id: ObjectId = None) -> bool:
        """Update media asset metadata."""
        update_data = {'updated_at': datetime.utcnow()}
        
        if user_id:
            update_data['updated_by'] = user_id
        
        if alt_text is not None:
            update_data['alt_text'] = alt_text
        
        if tags is not None:
            update_data['tags'] = tags
        
        result = self.media_assets.update_one(
            {'_id': asset_id},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    def delete_media_asset(self, asset_id: ObjectId, user_id: ObjectId = None) -> bool:
        """Delete a media asset and its variants."""
        try:
            # Get asset info for cleanup
            asset_data = self.media_assets.find_one({'_id': asset_id})
            if not asset_data:
                return False
            
            asset = MediaAsset(**asset_data)
            
            # Delete from database
            result = self.media_assets.delete_one({'_id': asset_id})
            
            # In a real implementation, we would also delete the physical files
            # For now, we'll just simulate this
            self._cleanup_media_files(asset)
            
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting media asset: {e}")
            return False
    
    def get_usage_statistics(self, asset_id: ObjectId) -> Dict[str, Any]:
        """Get usage statistics for a media asset."""
        asset_data = self.media_assets.find_one({'_id': asset_id})
        if not asset_data:
            return {}
        
        asset = MediaAsset(**asset_data)
        
        return {
            'asset_id': asset_id,
            'filename': asset.original_filename,
            'usage_count': asset.usage_count,
            'file_size': asset.file_size,
            'variants_count': len(asset.variants),
            'is_optimized': asset.is_optimized,
            'created_at': asset.created_at,
            'last_used': asset.updated_at  # Approximation
        }
    
    def _determine_file_type(self, extension: str, mime_type: str) -> str:
        """Determine the file type based on extension and MIME type."""
        if extension in self.supported_image_formats or mime_type.startswith('image/'):
            return 'image'
        elif extension in self.supported_video_formats or mime_type.startswith('video/'):
            return 'video'
        elif extension in self.supported_document_formats or mime_type.startswith('application/'):
            return 'document'
        else:
            return 'other'
    
    def _extract_image_dimensions(self, file_data: bytes, extension: str) -> Dict[str, int]:
        """Extract image dimensions (simulated implementation)."""
        # In a real implementation, this would use PIL or similar library
        # For testing, we'll return simulated dimensions based on file size
        file_size = len(file_data)
        
        if file_size < 10000:  # Small file
            return {'width': 200, 'height': 150}
        elif file_size < 100000:  # Medium file
            return {'width': 800, 'height': 600}
        else:  # Large file
            return {'width': 1920, 'height': 1080}
    
    def _process_media_file(self, asset_id: ObjectId, file_data: bytes, extension: str) -> None:
        """Process the uploaded media file (simulated)."""
        # In a real implementation, this would:
        # 1. Save the file to disk
        # 2. Run optimization tools
        # 3. Generate thumbnails/variants
        # For testing, we'll just simulate this
        pass
    
    def _generate_image_variants(self, asset: MediaAsset) -> List[Dict[str, Any]]:
        """Generate image variants for different sizes and formats."""
        variants = []
        
        if not asset.dimensions:
            return variants
        
        original_width = asset.dimensions.get('width', 800)
        original_height = asset.dimensions.get('height', 600)
        
        # Generate common variants
        variant_configs = [
            {'name': 'thumbnail', 'width': 150, 'height': 150},
            {'name': 'small', 'width': 300, 'height': int(300 * original_height / original_width)},
            {'name': 'medium', 'width': 600, 'height': int(600 * original_height / original_width)},
            {'name': 'large', 'width': 1200, 'height': int(1200 * original_height / original_width)}
        ]
        
        for config in variant_configs:
            # Only create variant if it's smaller than original
            if config['width'] < original_width:
                variant = {
                    'name': config['name'],
                    'file_path': f"{asset.file_path}_{config['name']}.webp",
                    'dimensions': {'width': config['width'], 'height': config['height']},
                    'file_size': int(asset.file_size * (config['width'] / original_width) * 0.8),  # Estimate
                    'format': 'webp'
                }
                variants.append(variant)
        
        return variants
    
    def _generate_video_variants(self, asset: MediaAsset) -> List[Dict[str, Any]]:
        """Generate video variants for different qualities."""
        variants = []
        
        # Generate common video variants
        variant_configs = [
            {'name': 'low', 'quality': '480p', 'bitrate': '500k'},
            {'name': 'medium', 'quality': '720p', 'bitrate': '1500k'},
            {'name': 'high', 'quality': '1080p', 'bitrate': '3000k'}
        ]
        
        for config in variant_configs:
            variant = {
                'name': config['name'],
                'file_path': f"{asset.file_path}_{config['name']}.mp4",
                'file_size': int(asset.file_size * 0.7),  # Estimate compressed size
                'format': 'mp4',
                'quality': config['quality'],
                'bitrate': config['bitrate']
            }
            variants.append(variant)
        
        return variants
    
    def _cleanup_media_files(self, asset: MediaAsset) -> None:
        """Clean up physical media files (simulated)."""
        # In a real implementation, this would delete:
        # 1. The original file
        # 2. All variant files
        # For testing, we'll just simulate this
        pass