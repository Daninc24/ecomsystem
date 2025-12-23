"""
Content Publishing Service
Handles real-time content updates and publishing
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from bson import ObjectId
from ..models.content import ContentVersion
from ..database.collections import get_collection
from .change_notifier import ChangeNotifier


class ContentPublisher:
    """Manages content publishing and real-time updates."""
    
    def __init__(self, db):
        self.db = db
        self.content_versions = get_collection(db, 'content_versions')
        self.published_content = get_collection(db, 'published_content')
        self.change_notifier = ChangeNotifier()
        self.cache_invalidation_queue = []
    
    def publish_version(self, version_id: ObjectId, user_id: ObjectId = None) -> bool:
        """Publish a content version and trigger real-time updates."""
        try:
            # Get the version to publish
            version_data = self.content_versions.find_one({'_id': version_id})
            if not version_data:
                return False
            
            version = ContentVersion(**version_data)
            
            # Unpublish any existing published version for this element
            self._unpublish_existing_versions(version.element_id)
            
            # Mark this version as published
            self.content_versions.update_one(
                {'_id': version_id},
                {
                    '$set': {
                        'is_published': True,
                        'published_at': datetime.utcnow(),
                        'published_by': user_id or ObjectId(),
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            # Update the published content cache
            self._update_published_content_cache(version)
            
            # Invalidate related caches
            self._invalidate_caches(version.element_id)
            
            # Notify subscribers of the content change
            self._notify_content_change(version, 'published', user_id)
            
            return True
            
        except Exception as e:
            print(f"Error publishing content version: {e}")
            return False
    
    def unpublish_content(self, element_id: str, user_id: ObjectId = None) -> bool:
        """Unpublish content for an element."""
        try:
            # Unpublish all versions for this element
            result = self.content_versions.update_many(
                {'element_id': element_id, 'is_published': True},
                {
                    '$set': {
                        'is_published': False,
                        'unpublished_at': datetime.utcnow(),
                        'unpublished_by': user_id or ObjectId(),
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                # Remove from published content cache
                self.published_content.delete_many({'element_id': element_id})
                
                # Invalidate caches
                self._invalidate_caches(element_id)
                
                # Notify subscribers
                self.change_notifier.broadcast_change(
                    key=f'content_unpublished_{element_id}',
                    old_value=None,
                    new_value={
                        'event_type': 'content_unpublished',
                        'element_id': element_id,
                        'user_id': user_id,
                        'timestamp': datetime.utcnow(),
                        'metadata': {'unpublished_versions': result.modified_count}
                    },
                    user_id=str(user_id) if user_id else None
                )
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Error unpublishing content: {e}")
            return False
    
    def get_published_content(self, element_id: str, use_cache: bool = True) -> Optional[ContentVersion]:
        """Get the currently published content for an element."""
        if use_cache:
            # Try cache first
            cached_data = self.published_content.find_one({'element_id': element_id})
            if cached_data:
                return ContentVersion(**cached_data['content'])
        
        # Fallback to direct query
        version_data = self.content_versions.find_one({
            'element_id': element_id,
            'is_published': True
        })
        
        if version_data:
            version = ContentVersion(**version_data)
            
            # Update cache if using cache
            if use_cache:
                self._update_published_content_cache(version)
            
            return version
        
        return None
    
    def get_all_published_content(self) -> Dict[str, ContentVersion]:
        """Get all currently published content."""
        published_content = {}
        
        # Get all published versions
        versions_data = self.content_versions.find({'is_published': True})
        
        for version_data in versions_data:
            version = ContentVersion(**version_data)
            published_content[version.element_id] = version
        
        return published_content
    
    def schedule_publication(self, version_id: ObjectId, publish_at: datetime, 
                           user_id: ObjectId = None) -> bool:
        """Schedule a content version for future publication."""
        try:
            # In a real implementation, this would use a job queue or scheduler
            # For now, we'll just store the schedule in the version metadata
            self.content_versions.update_one(
                {'_id': version_id},
                {
                    '$set': {
                        'scheduled_publish_at': publish_at,
                        'scheduled_by': user_id or ObjectId(),
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Error scheduling publication: {e}")
            return False
    
    def cancel_scheduled_publication(self, version_id: ObjectId, user_id: ObjectId = None) -> bool:
        """Cancel a scheduled publication."""
        try:
            result = self.content_versions.update_one(
                {'_id': version_id},
                {
                    '$unset': {
                        'scheduled_publish_at': '',
                        'scheduled_by': ''
                    },
                    '$set': {
                        'updated_at': datetime.utcnow(),
                        'updated_by': user_id or ObjectId()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"Error canceling scheduled publication: {e}")
            return False
    
    def get_scheduled_publications(self) -> List[Dict[str, Any]]:
        """Get all scheduled publications."""
        scheduled_data = list(self.content_versions.find({
            'scheduled_publish_at': {'$exists': True, '$ne': None}
        }).sort('scheduled_publish_at', 1))
        
        scheduled_publications = []
        for data in scheduled_data:
            version = ContentVersion(**data)
            scheduled_publications.append({
                'version_id': version.id,
                'element_id': version.element_id,
                'version_number': version.version_number,
                'scheduled_publish_at': data.get('scheduled_publish_at'),
                'scheduled_by': data.get('scheduled_by'),
                'content_preview': version.get_content_preview(100)
            })
        
        return scheduled_publications
    
    def register_content_change_listener(self, listener_func) -> None:
        """Register a listener for content change events."""
        import uuid
        listener_id = f"content_listener_{uuid.uuid4().hex[:8]}"
        self.change_notifier.register_listener(listener_id, listener_func)
    
    def get_cache_invalidation_queue(self) -> List[str]:
        """Get the current cache invalidation queue."""
        return self.cache_invalidation_queue.copy()
    
    def clear_cache_invalidation_queue(self) -> None:
        """Clear the cache invalidation queue."""
        self.cache_invalidation_queue.clear()
    
    def _unpublish_existing_versions(self, element_id: str) -> None:
        """Unpublish any existing published versions for an element."""
        self.content_versions.update_many(
            {'element_id': element_id, 'is_published': True},
            {
                '$set': {
                    'is_published': False,
                    'unpublished_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            }
        )
    
    def _update_published_content_cache(self, version: ContentVersion) -> None:
        """Update the published content cache."""
        cache_data = {
            'element_id': version.element_id,
            'content': version.to_dict(),
            'cached_at': datetime.utcnow(),
            'cache_key': f"published_content_{version.element_id}"
        }
        
        # Upsert the cache entry
        self.published_content.update_one(
            {'element_id': version.element_id},
            {'$set': cache_data},
            upsert=True
        )
    
    def _invalidate_caches(self, element_id: str) -> None:
        """Invalidate caches related to the content element."""
        # Add to invalidation queue
        cache_keys = [
            f"content_{element_id}",
            f"page_cache_{element_id}",
            f"api_cache_{element_id}"
        ]
        
        self.cache_invalidation_queue.extend(cache_keys)
        
        # In a real implementation, this would trigger cache invalidation
        # across all application servers and CDN nodes
    
    def _notify_content_change(self, version: ContentVersion, action: str, user_id: ObjectId = None) -> None:
        """Notify subscribers of content changes."""
        # Create event dict for compatibility with the test
        event_dict = {
            'event_type': f'content_{action}',
            'element_id': version.element_id,
            'user_id': user_id,
            'timestamp': datetime.utcnow(),
            'metadata': {
                'version_id': str(version.id),
                'version_number': version.version_number,
                'content_type': version.content_type,
                'change_summary': version.change_summary
            }
        }
        
        # Notify using the change notifier
        self.change_notifier.broadcast_change(
            key=f'content_{action}_{version.element_id}',
            old_value=None,
            new_value=event_dict,
            user_id=str(user_id) if user_id else None
        )