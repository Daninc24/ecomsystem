"""
Content Management Service
Handles content editing, versioning, and publishing
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from ..models.content import ContentVersion, MediaAsset
from ..database.collections import get_collection


class ContentManager:
    """Manages content editing, versioning, and publishing."""
    
    def __init__(self, db):
        self.db = db
        self.content_versions = get_collection(db, 'content_versions')
        self.media_assets = get_collection(db, 'media_assets')
    
    def create_content(self, element_id: str, content: str, content_type: str = 'html', 
                      user_id: ObjectId = None, metadata: Dict[str, Any] = None) -> ObjectId:
        """Create new content with initial version."""
        if metadata is None:
            metadata = {}
        
        content_version = ContentVersion(
            element_id=element_id,
            content=content,
            content_type=content_type,
            version_number=1,
            is_published=True,  # First version is automatically published
            metadata=metadata,
            change_summary="Initial content creation",
            created_by=user_id or ObjectId(),
            updated_by=user_id or ObjectId()
        )
        
        version_data = content_version.to_dict()
        result = self.content_versions.insert_one(version_data)
        return result.inserted_id
    
    def edit_content(self, element_id: str, new_content: str, user_id: ObjectId = None,
                    change_summary: str = "", metadata: Dict[str, Any] = None) -> ObjectId:
        """Edit existing content, creating a new version."""
        if metadata is None:
            metadata = {}
        
        # Get the latest version for this element
        latest_version = self.get_latest_version(element_id)
        if not latest_version:
            # Create initial content if none exists
            return self.create_content(element_id, new_content, user_id=user_id, metadata=metadata)
        
        # Create new version
        new_version_number = latest_version.version_number + 1
        content_version = ContentVersion(
            element_id=element_id,
            content=new_content,
            content_type=latest_version.content_type,
            version_number=new_version_number,
            is_published=False,  # New versions start unpublished
            metadata=metadata,
            change_summary=change_summary or f"Content update #{new_version_number}",
            parent_version_id=latest_version.id,
            created_by=user_id or ObjectId(),
            updated_by=user_id or ObjectId()
        )
        
        version_data = content_version.to_dict()
        result = self.content_versions.insert_one(version_data)
        return result.inserted_id
    
    def publish_content(self, version_id: ObjectId, user_id: ObjectId = None) -> bool:
        """Publish a specific content version."""
        try:
            # Get the version to publish
            version_data = self.content_versions.find_one({'_id': version_id})
            if not version_data:
                return False
            
            version = ContentVersion(**version_data)
            
            # Unpublish all other versions of the same element
            self.content_versions.update_many(
                {'element_id': version.element_id, '_id': {'$ne': version_id}},
                {'$set': {'is_published': False, 'updated_at': datetime.utcnow()}}
            )
            
            # Publish this version
            self.content_versions.update_one(
                {'_id': version_id},
                {
                    '$set': {
                        'is_published': True,
                        'updated_at': datetime.utcnow(),
                        'updated_by': user_id or ObjectId()
                    }
                }
            )
            
            return True
        except Exception as e:
            print(f"Error publishing content: {e}")
            return False
    
    def get_published_content(self, element_id: str) -> Optional[ContentVersion]:
        """Get the currently published content for an element."""
        version_data = self.content_versions.find_one({
            'element_id': element_id,
            'is_published': True
        })
        
        if version_data:
            return ContentVersion(**version_data)
        return None
    
    def get_latest_version(self, element_id: str) -> Optional[ContentVersion]:
        """Get the latest version (published or unpublished) for an element."""
        versions_data = list(self.content_versions.find(
            {'element_id': element_id}
        ).sort('version_number', -1).limit(1))
        
        if versions_data:
            return ContentVersion(**versions_data[0])
        return None
    
    def get_version_history(self, element_id: str) -> List[ContentVersion]:
        """Get all versions for an element, ordered by version number."""
        versions_data = list(self.content_versions.find(
            {'element_id': element_id}
        ).sort('version_number', -1))
        
        return [ContentVersion(**data) for data in versions_data]
    
    def rollback_content(self, element_id: str, target_version_number: int, 
                        user_id: ObjectId = None) -> Optional[ObjectId]:
        """Rollback content to a specific version by creating a new version with old content."""
        # Find the target version
        target_version_data = self.content_versions.find_one({
            'element_id': element_id,
            'version_number': target_version_number
        })
        
        if not target_version_data:
            return None
        
        target_version = ContentVersion(**target_version_data)
        
        # Create a new version with the old content
        latest_version = self.get_latest_version(element_id)
        new_version_number = latest_version.version_number + 1 if latest_version else 1
        
        rollback_version = ContentVersion(
            element_id=element_id,
            content=target_version.content,
            content_type=target_version.content_type,
            version_number=new_version_number,
            is_published=False,
            metadata=target_version.metadata.copy(),
            change_summary=f"Rollback to version {target_version_number}",
            parent_version_id=target_version.id,
            created_by=user_id or ObjectId(),
            updated_by=user_id or ObjectId()
        )
        
        version_data = rollback_version.to_dict()
        result = self.content_versions.insert_one(version_data)
        
        # Auto-publish the rollback version
        self.publish_content(result.inserted_id, user_id)
        
        return result.inserted_id
    
    def get_content_by_version_id(self, version_id: ObjectId) -> Optional[ContentVersion]:
        """Get a specific content version by its ID."""
        version_data = self.content_versions.find_one({'_id': version_id})
        if version_data:
            return ContentVersion(**version_data)
        return None
    
    def delete_content_element(self, element_id: str, user_id: ObjectId = None) -> bool:
        """Delete all versions of a content element."""
        try:
            result = self.content_versions.delete_many({'element_id': element_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting content element: {e}")
            return False