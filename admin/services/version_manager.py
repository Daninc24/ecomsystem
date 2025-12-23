"""
Version Management Service
Handles content version history and rollbacks
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from ..models.content import ContentVersion
from ..database.collections import get_collection


class VersionManager:
    """Manages content version history and rollback operations."""
    
    def __init__(self, db):
        self.db = db
        self.content_versions = get_collection(db, 'content_versions')
    
    def create_version_snapshot(self, element_id: str, content: str, 
                               user_id: ObjectId = None, metadata: Dict[str, Any] = None) -> ObjectId:
        """Create a snapshot version without publishing."""
        if metadata is None:
            metadata = {}
        
        # Get the latest version number
        latest_version = self.content_versions.find_one(
            {'element_id': element_id},
            sort=[('version_number', -1)]
        )
        
        version_number = (latest_version['version_number'] + 1) if latest_version else 1
        
        version = ContentVersion(
            element_id=element_id,
            content=content,
            version_number=version_number,
            is_published=False,
            metadata=metadata,
            change_summary=f"Snapshot version {version_number}",
            created_by=user_id or ObjectId(),
            updated_by=user_id or ObjectId()
        )
        
        version_data = version.to_dict()
        result = self.content_versions.insert_one(version_data)
        return result.inserted_id
    
    def get_version_diff(self, element_id: str, version1: int, version2: int) -> Optional[Dict[str, Any]]:
        """Get the differences between two versions."""
        version1_data = self.content_versions.find_one({
            'element_id': element_id,
            'version_number': version1
        })
        
        version2_data = self.content_versions.find_one({
            'element_id': element_id,
            'version_number': version2
        })
        
        if not version1_data or not version2_data:
            return None
        
        v1 = ContentVersion(**version1_data)
        v2 = ContentVersion(**version2_data)
        
        return {
            'element_id': element_id,
            'version1': {
                'number': v1.version_number,
                'content': v1.content,
                'created_at': v1.created_at,
                'created_by': v1.created_by
            },
            'version2': {
                'number': v2.version_number,
                'content': v2.content,
                'created_at': v2.created_at,
                'created_by': v2.created_by
            },
            'content_changed': v1.content != v2.content,
            'metadata_changed': v1.metadata != v2.metadata
        }
    
    def get_version_tree(self, element_id: str) -> List[Dict[str, Any]]:
        """Get the version tree showing parent-child relationships."""
        versions_data = list(self.content_versions.find(
            {'element_id': element_id}
        ).sort('version_number', 1))
        
        versions = [ContentVersion(**data) for data in versions_data]
        
        # Build tree structure
        tree = []
        for version in versions:
            tree_node = {
                'id': version.id,
                'version_number': version.version_number,
                'content_preview': version.get_content_preview(50),
                'is_published': version.is_published,
                'created_at': version.created_at,
                'created_by': version.created_by,
                'parent_version_id': version.parent_version_id,
                'change_summary': version.change_summary
            }
            tree.append(tree_node)
        
        return tree
    
    def validate_rollback_target(self, element_id: str, target_version: int) -> Tuple[bool, str]:
        """Validate if a rollback to the target version is possible."""
        # Check if target version exists
        target_data = self.content_versions.find_one({
            'element_id': element_id,
            'version_number': target_version
        })
        
        if not target_data:
            return False, f"Version {target_version} not found for element {element_id}"
        
        # Check if there's a current version to rollback from
        current_data = self.content_versions.find_one({
            'element_id': element_id,
            'is_published': True
        })
        
        if not current_data:
            return False, f"No published version found for element {element_id}"
        
        current_version = ContentVersion(**current_data)
        
        # Can't rollback to the same version
        if current_version.version_number == target_version:
            return False, f"Cannot rollback to the currently published version {target_version}"
        
        return True, "Rollback target is valid"
    
    def cleanup_old_versions(self, element_id: str, keep_count: int = 10) -> int:
        """Clean up old versions, keeping only the most recent ones."""
        if keep_count <= 0:
            return 0
        
        # Get all versions sorted by version number (newest first)
        versions_data = list(self.content_versions.find(
            {'element_id': element_id}
        ).sort('version_number', -1))
        
        if len(versions_data) <= keep_count:
            return 0  # Nothing to clean up
        
        # Keep the most recent versions and the currently published version
        published_version = None
        for version_data in versions_data:
            if version_data.get('is_published'):
                published_version = version_data
                break
        
        # Determine which versions to keep
        versions_to_keep = set()
        
        # Keep the most recent versions
        for i in range(min(keep_count, len(versions_data))):
            versions_to_keep.add(versions_data[i]['_id'])
        
        # Always keep the published version
        if published_version:
            versions_to_keep.add(published_version['_id'])
        
        # Delete the rest
        versions_to_delete = [
            version_data['_id'] for version_data in versions_data
            if version_data['_id'] not in versions_to_keep
        ]
        
        if versions_to_delete:
            result = self.content_versions.delete_many({
                '_id': {'$in': versions_to_delete}
            })
            return result.deleted_count
        
        return 0
    
    def get_version_statistics(self, element_id: str) -> Dict[str, Any]:
        """Get statistics about versions for an element."""
        versions_data = list(self.content_versions.find({'element_id': element_id}))
        
        if not versions_data:
            return {
                'total_versions': 0,
                'published_version': None,
                'latest_version': None,
                'first_created': None,
                'last_updated': None
            }
        
        versions = [ContentVersion(**data) for data in versions_data]
        
        published_version = None
        for version in versions:
            if version.is_published:
                published_version = version.version_number
                break
        
        latest_version = max(version.version_number for version in versions)
        first_created = min(version.created_at for version in versions)
        last_updated = max(version.updated_at for version in versions)
        
        return {
            'total_versions': len(versions),
            'published_version': published_version,
            'latest_version': latest_version,
            'first_created': first_created,
            'last_updated': last_updated
        }