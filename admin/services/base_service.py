"""
Base service class for admin services
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime
from bson import ObjectId


class BaseService(ABC):
    """Base service class with common functionality."""
    
    def __init__(self, mongo_db):
        """Initialize base service with database connection."""
        self.db = mongo_db
        self.collection_name = self._get_collection_name()
        self.collection = getattr(self.db, self.collection_name)
    
    @abstractmethod
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        pass
    
    def create(self, data: Dict[str, Any], user_id: Optional[ObjectId] = None) -> ObjectId:
        """Create a new document in the collection."""
        now = datetime.utcnow()
        data.update({
            'created_at': now,
            'updated_at': now,
            'created_by': user_id,
            'updated_by': user_id
        })
        
        result = self.collection.insert_one(data)
        return result.inserted_id
    
    def get_by_id(self, doc_id: ObjectId) -> Optional[Dict[str, Any]]:
        """Get a document by its ID."""
        return self.collection.find_one({'_id': doc_id})
    
    def update(self, doc_id: ObjectId, data: Dict[str, Any], user_id: Optional[ObjectId] = None) -> bool:
        """Update a document by its ID."""
        data.update({
            'updated_at': datetime.utcnow(),
            'updated_by': user_id
        })
        
        result = self.collection.update_one(
            {'_id': doc_id},
            {'$set': data}
        )
        return result.modified_count > 0
    
    def delete(self, doc_id: ObjectId) -> bool:
        """Delete a document by its ID."""
        result = self.collection.delete_one({'_id': doc_id})
        return result.deleted_count > 0
    
    def find(self, query: Dict[str, Any] = None, limit: int = None, sort: List[tuple] = None) -> List[Dict[str, Any]]:
        """Find documents matching the query."""
        if query is None:
            query = {}
        
        cursor = self.collection.find(query)
        
        if sort:
            cursor = cursor.sort(sort)
        
        if limit:
            cursor = cursor.limit(limit)
        
        return list(cursor)
    
    def count(self, query: Dict[str, Any] = None) -> int:
        """Count documents matching the query."""
        if query is None:
            query = {}
        return self.collection.count_documents(query)
    
    def exists(self, query: Dict[str, Any]) -> bool:
        """Check if a document exists matching the query."""
        return self.collection.find_one(query) is not None