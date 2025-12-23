"""
Asset Manager Service
Manages theme assets like logos, favicons, and other media files
"""

import os
import shutil
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from bson import ObjectId
from PIL import Image
import io
import base64

from ..models.content import MediaAsset
from .base_service import BaseService


class AssetManager(BaseService):
    """Manages theme assets including logos, favicons, and media files."""
    
    def __init__(self, db, user_id: Optional[ObjectId] = None):
        self.user_id = user_id
        super().__init__(db)
        self.collection = db.media_assets
        self.assets_directory = os.path.join('static', 'images')
        self.supported_formats = {
            'logo': ['png', 'jpg', 'jpeg', 'svg', 'webp'],
            'favicon': ['ico', 'png'],
            'background': ['jpg', 'jpeg', 'png', 'webp'],
            'icon': ['png', 'jpg', 'jpeg', 'svg', 'webp']
        }
        
        # Ensure assets directory exists
        os.makedirs(self.assets_directory, exist_ok=True)
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'media_assets'
    
    def upload_theme_asset(self, file_data: bytes, filename: str, 
                          asset_type: str, description: str = "") -> MediaAsset:
        """Upload a theme asset (logo, favicon, etc.)."""
        if not self._validate_asset_type(filename, asset_type):
            raise ValueError(f"Invalid file format for {asset_type}")
        
        # Generate unique filename
        file_hash = hashlib.md5(file_data).hexdigest()
        file_extension = filename.split('.')[-1].lower()
        unique_filename = f"{asset_type}_{file_hash}.{file_extension}"
        file_path = os.path.join(self.assets_directory, unique_filename)
        
        # Save file to disk
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        # Generate variants if needed
        variants = self._generate_asset_variants(file_path, asset_type, file_extension)
        
        # Create media asset record
        media_asset = MediaAsset(
            filename=unique_filename,
            original_filename=filename,
            file_path=file_path,
            file_size=len(file_data),
            file_type=asset_type,
            mime_type=self._get_mime_type(file_extension),
            description=description,
            variants=variants,
            tags=[asset_type, 'theme'],
            usage_count=0,
            created_by=self.user_id,
            updated_by=self.user_id
        )
        
        # Save to database
        result = self.collection.insert_one(media_asset.to_dict())
        media_asset.id = result.inserted_id
        
        return media_asset
    
    def get_theme_asset(self, asset_type: str) -> Optional[MediaAsset]:
        """Get the current theme asset of a specific type."""
        asset_data = self.collection.find_one({
            'file_type': asset_type,
            'tags': 'theme',
            'is_active': True
        })
        
        if asset_data:
            return MediaAsset(**asset_data)
        return None
    
    def set_active_asset(self, asset_id: ObjectId, asset_type: str) -> bool:
        """Set an asset as the active asset for its type."""
        # Deactivate current active asset of this type
        self.collection.update_many(
            {'file_type': asset_type, 'tags': 'theme'},
            {'$set': {'is_active': False, 'updated_at': datetime.utcnow()}}
        )
        
        # Activate the new asset
        result = self.collection.update_one(
            {'_id': asset_id},
            {'$set': {
                'is_active': True,
                'updated_at': datetime.utcnow(),
                'updated_by': self.user_id
            }}
        )
        
        return result.modified_count > 0
    
    def generate_favicon_set(self, logo_asset_id: ObjectId) -> List[MediaAsset]:
        """Generate a complete favicon set from a logo."""
        logo_asset = self.get_asset_by_id(logo_asset_id)
        if not logo_asset:
            raise ValueError(f"Logo asset with ID {logo_asset_id} not found")
        
        favicon_sizes = [16, 32, 48, 64, 128, 180, 192, 512]
        favicon_assets = []
        
        # Load the original image
        with Image.open(logo_asset.file_path) as img:
            # Convert to RGBA if not already
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Generate favicons for each size
            for size in favicon_sizes:
                # Resize image
                resized_img = img.resize((size, size), Image.Resampling.LANCZOS)
                
                # Save as PNG
                filename = f"favicon-{size}x{size}.png"
                file_path = os.path.join(self.assets_directory, filename)
                resized_img.save(file_path, 'PNG')
                
                # Create media asset record
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                favicon_asset = MediaAsset(
                    filename=filename,
                    original_filename=f"favicon-{size}x{size}.png",
                    file_path=file_path,
                    file_size=len(file_data),
                    file_type='favicon',
                    mime_type='image/png',
                    description=f"Favicon {size}x{size}",
                    dimensions={'width': size, 'height': size},
                    tags=['favicon', 'theme', 'generated'],
                    usage_count=0,
                    created_by=self.user_id,
                    updated_by=self.user_id
                )
                
                # Save to database
                result = self.collection.insert_one(favicon_asset.to_dict())
                favicon_asset.id = result.inserted_id
                favicon_assets.append(favicon_asset)
            
            # Generate ICO file for legacy support
            ico_sizes = [(16, 16), (32, 32), (48, 48)]
            ico_images = []
            
            for width, height in ico_sizes:
                resized_img = img.resize((width, height), Image.Resampling.LANCZOS)
                ico_images.append(resized_img)
            
            # Save as ICO
            ico_filename = "favicon.ico"
            ico_path = os.path.join(self.assets_directory, ico_filename)
            ico_images[0].save(ico_path, format='ICO', sizes=ico_sizes)
            
            # Create ICO asset record
            with open(ico_path, 'rb') as f:
                ico_data = f.read()
            
            ico_asset = MediaAsset(
                filename=ico_filename,
                original_filename="favicon.ico",
                file_path=ico_path,
                file_size=len(ico_data),
                file_type='favicon',
                mime_type='image/x-icon',
                description="Legacy favicon ICO file",
                tags=['favicon', 'theme', 'generated', 'ico'],
                usage_count=0,
                created_by=self.user_id,
                updated_by=self.user_id
            )
            
            result = self.collection.insert_one(ico_asset.to_dict())
            ico_asset.id = result.inserted_id
            favicon_assets.append(ico_asset)
        
        return favicon_assets
    
    def optimize_asset(self, asset_id: ObjectId, quality: int = 85) -> MediaAsset:
        """Optimize an asset for web use."""
        asset = self.get_asset_by_id(asset_id)
        if not asset:
            raise ValueError(f"Asset with ID {asset_id} not found")
        
        if not asset.file_path or not os.path.exists(asset.file_path):
            raise ValueError("Asset file not found on disk")
        
        # Only optimize image files
        if not asset.mime_type.startswith('image/'):
            return asset
        
        # Skip SVG files
        if asset.mime_type == 'image/svg+xml':
            return asset
        
        # Create optimized version
        optimized_filename = f"optimized_{asset.filename}"
        optimized_path = os.path.join(self.assets_directory, optimized_filename)
        
        with Image.open(asset.file_path) as img:
            # Convert to RGB if necessary (for JPEG)
            if asset.mime_type == 'image/jpeg' and img.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparency
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Save optimized version
            save_kwargs = {'optimize': True}
            if asset.mime_type == 'image/jpeg':
                save_kwargs['quality'] = quality
            elif asset.mime_type == 'image/png':
                save_kwargs['compress_level'] = 6
            
            img.save(optimized_path, **save_kwargs)
        
        # Update asset record
        with open(optimized_path, 'rb') as f:
            optimized_data = f.read()
        
        # Replace original file
        shutil.move(optimized_path, asset.file_path)
        
        # Update database record
        self.collection.update_one(
            {'_id': asset_id},
            {'$set': {
                'file_size': len(optimized_data),
                'optimized': True,
                'optimization_quality': quality,
                'updated_at': datetime.utcnow(),
                'updated_by': self.user_id
            }}
        )
        
        # Refresh asset data
        return self.get_asset_by_id(asset_id)
    
    def get_asset_by_id(self, asset_id: ObjectId) -> Optional[MediaAsset]:
        """Get an asset by its ID."""
        asset_data = self.collection.find_one({'_id': asset_id})
        if asset_data:
            return MediaAsset(**asset_data)
        return None
    
    def get_assets_by_type(self, asset_type: str) -> List[MediaAsset]:
        """Get all assets of a specific type."""
        assets = []
        for asset_data in self.collection.find({'file_type': asset_type}):
            assets.append(MediaAsset(**asset_data))
        return assets
    
    def delete_asset(self, asset_id: ObjectId) -> bool:
        """Delete an asset and its file."""
        asset = self.get_asset_by_id(asset_id)
        if not asset:
            return False
        
        # Don't delete if asset is in use
        if asset.usage_count > 0:
            raise ValueError("Cannot delete asset that is currently in use")
        
        # Delete file from disk
        if asset.file_path and os.path.exists(asset.file_path):
            os.remove(asset.file_path)
        
        # Delete variants
        if asset.variants:
            for variant in asset.variants:
                variant_path = variant.get('file_path')
                if variant_path and os.path.exists(variant_path):
                    os.remove(variant_path)
        
        # Delete from database
        result = self.collection.delete_one({'_id': asset_id})
        return result.deleted_count > 0
    
    def get_asset_url(self, asset: MediaAsset) -> str:
        """Get the public URL for an asset."""
        if not asset.filename:
            return ""
        
        # Return relative URL from static directory
        return f"/static/images/{asset.filename}"
    
    def get_asset_data_url(self, asset: MediaAsset) -> str:
        """Get a data URL for an asset (base64 encoded)."""
        if not asset.file_path or not os.path.exists(asset.file_path):
            return ""
        
        with open(asset.file_path, 'rb') as f:
            file_data = f.read()
        
        encoded_data = base64.b64encode(file_data).decode('utf-8')
        return f"data:{asset.mime_type};base64,{encoded_data}"
    
    def _validate_asset_type(self, filename: str, asset_type: str) -> bool:
        """Validate that the file format is supported for the asset type."""
        if asset_type not in self.supported_formats:
            return False
        
        file_extension = filename.split('.')[-1].lower()
        return file_extension in self.supported_formats[asset_type]
    
    def _get_mime_type(self, file_extension: str) -> str:
        """Get MIME type for a file extension."""
        mime_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'svg': 'image/svg+xml',
            'webp': 'image/webp',
            'ico': 'image/x-icon'
        }
        return mime_types.get(file_extension.lower(), 'application/octet-stream')
    
    def _generate_asset_variants(self, file_path: str, asset_type: str, 
                               file_extension: str) -> List[Dict[str, Any]]:
        """Generate different variants of an asset."""
        variants = []
        
        # Skip variant generation for SVG and ICO files
        if file_extension.lower() in ['svg', 'ico']:
            return variants
        
        try:
            with Image.open(file_path) as img:
                original_width, original_height = img.size
                
                # Define variant sizes based on asset type
                if asset_type == 'logo':
                    variant_sizes = [
                        ('small', 100, 100),
                        ('medium', 200, 200),
                        ('large', 400, 400)
                    ]
                elif asset_type == 'background':
                    variant_sizes = [
                        ('thumbnail', 300, 200),
                        ('medium', 800, 600),
                        ('large', 1200, 800)
                    ]
                else:
                    variant_sizes = [
                        ('small', 64, 64),
                        ('medium', 128, 128),
                        ('large', 256, 256)
                    ]
                
                for variant_name, max_width, max_height in variant_sizes:
                    # Calculate new dimensions maintaining aspect ratio
                    ratio = min(max_width / original_width, max_height / original_height)
                    if ratio >= 1:  # Don't upscale
                        continue
                    
                    new_width = int(original_width * ratio)
                    new_height = int(original_height * ratio)
                    
                    # Create variant
                    variant_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Save variant
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    variant_filename = f"{base_name}_{variant_name}.{file_extension}"
                    variant_path = os.path.join(self.assets_directory, variant_filename)
                    
                    variant_img.save(variant_path)
                    
                    # Get file size
                    variant_size = os.path.getsize(variant_path)
                    
                    variants.append({
                        'name': variant_name,
                        'filename': variant_filename,
                        'file_path': variant_path,
                        'file_size': variant_size,
                        'dimensions': {
                            'width': new_width,
                            'height': new_height
                        }
                    })
        
        except Exception as e:
            # If variant generation fails, log but don't fail the upload
            print(f"Warning: Could not generate variants for {file_path}: {e}")
        
        return variants