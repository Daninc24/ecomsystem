"""
Cache management service for performance optimization
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from bson import ObjectId

from .base_service import BaseService
from ..models.system import CacheEntry


class CacheManager(BaseService):
    """Service for managing application cache for performance optimization."""
    
    def _get_collection_name(self) -> str:
        return "cache_entries"
    
    def __init__(self, mongo_db):
        super().__init__(mongo_db)
        self.default_ttl = 3600  # 1 hour default TTL
        self.max_cache_size = 10000  # Maximum number of cache entries
    
    def set(self, key: str, value: Any, ttl: int = None, namespace: str = "default") -> bool:
        """Set a cache entry with optional TTL."""
        if ttl is None:
            ttl = self.default_ttl
        
        # Create full key with namespace
        full_key = f"{namespace}:{key}"
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        # Serialize value for storage
        serialized_value = self._serialize_value(value)
        
        cache_entry = CacheEntry(
            key=full_key,
            value=serialized_value,
            ttl=ttl,
            expires_at=expires_at,
            hit_count=0,
            last_accessed=datetime.utcnow()
        )
        
        try:
            # Use upsert to replace existing entry
            result = self.collection.replace_one(
                {'key': full_key},
                cache_entry.to_dict(),
                upsert=True
            )
            
            # Clean up expired entries periodically
            if result.upserted_id or result.modified_count > 0:
                self._cleanup_expired_entries()
            
            return True
        
        except Exception as e:
            print(f"Error setting cache entry: {e}")
            return False
    
    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Get a cache entry by key."""
        full_key = f"{namespace}:{key}"
        
        try:
            # Find the cache entry
            cache_entry = self.collection.find_one({'key': full_key})
            
            if not cache_entry:
                return None
            
            # Check if entry has expired
            if datetime.utcnow() > cache_entry['expires_at']:
                # Remove expired entry
                self.collection.delete_one({'_id': cache_entry['_id']})
                return None
            
            # Update hit count and last accessed time
            self.collection.update_one(
                {'_id': cache_entry['_id']},
                {
                    '$inc': {'hit_count': 1},
                    '$set': {'last_accessed': datetime.utcnow()}
                }
            )
            
            # Deserialize and return value
            return self._deserialize_value(cache_entry['value'])
        
        except Exception as e:
            print(f"Error getting cache entry: {e}")
            return None
    
    def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete a cache entry."""
        full_key = f"{namespace}:{key}"
        
        try:
            result = self.collection.delete_one({'key': full_key})
            return result.deleted_count > 0
        
        except Exception as e:
            print(f"Error deleting cache entry: {e}")
            return False
    
    def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if a cache entry exists and is not expired."""
        full_key = f"{namespace}:{key}"
        
        try:
            cache_entry = self.collection.find_one({'key': full_key})
            
            if not cache_entry:
                return False
            
            # Check if expired
            if datetime.utcnow() > cache_entry['expires_at']:
                # Remove expired entry
                self.collection.delete_one({'_id': cache_entry['_id']})
                return False
            
            return True
        
        except Exception as e:
            print(f"Error checking cache entry existence: {e}")
            return False
    
    def clear_namespace(self, namespace: str) -> int:
        """Clear all cache entries in a namespace."""
        try:
            result = self.collection.delete_many({'key': {'$regex': f'^{namespace}:'}})
            return result.deleted_count
        
        except Exception as e:
            print(f"Error clearing namespace: {e}")
            return 0
    
    def clear_all(self) -> int:
        """Clear all cache entries."""
        try:
            result = self.collection.delete_many({})
            return result.deleted_count
        
        except Exception as e:
            print(f"Error clearing all cache: {e}")
            return 0
    
    def extend_ttl(self, key: str, additional_seconds: int, namespace: str = "default") -> bool:
        """Extend the TTL of a cache entry."""
        full_key = f"{namespace}:{key}"
        
        try:
            cache_entry = self.collection.find_one({'key': full_key})
            
            if not cache_entry:
                return False
            
            # Check if already expired
            if datetime.utcnow() > cache_entry['expires_at']:
                return False
            
            # Extend expiration time
            new_expires_at = cache_entry['expires_at'] + timedelta(seconds=additional_seconds)
            new_ttl = cache_entry['ttl'] + additional_seconds
            
            result = self.collection.update_one(
                {'_id': cache_entry['_id']},
                {
                    '$set': {
                        'expires_at': new_expires_at,
                        'ttl': new_ttl
                    }
                }
            )
            
            return result.modified_count > 0
        
        except Exception as e:
            print(f"Error extending TTL: {e}")
            return False
    
    def get_or_set(self, key: str, value_func, ttl: int = None, namespace: str = "default") -> Any:
        """Get cache entry or set it using the provided function if not found."""
        # Try to get existing value
        cached_value = self.get(key, namespace)
        
        if cached_value is not None:
            return cached_value
        
        # Generate new value
        try:
            new_value = value_func()
            self.set(key, new_value, ttl, namespace)
            return new_value
        
        except Exception as e:
            print(f"Error in get_or_set: {e}")
            return None
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for storage."""
        try:
            return json.dumps(value, default=str)
        except Exception as e:
            print(f"Error serializing value: {e}")
            return json.dumps(str(value))
    
    def _deserialize_value(self, serialized_value: str) -> Any:
        """Deserialize value from storage."""
        try:
            return json.loads(serialized_value)
        except Exception as e:
            print(f"Error deserializing value: {e}")
            return serialized_value
    
    def _cleanup_expired_entries(self) -> int:
        """Clean up expired cache entries."""
        try:
            current_time = datetime.utcnow()
            result = self.collection.delete_many({'expires_at': {'$lt': current_time}})
            
            # Also enforce max cache size
            total_entries = self.collection.count_documents({})
            if total_entries > self.max_cache_size:
                # Remove oldest entries
                excess_count = total_entries - self.max_cache_size
                oldest_entries = list(self.collection.find().sort('last_accessed', 1).limit(excess_count))
                
                if oldest_entries:
                    oldest_ids = [entry['_id'] for entry in oldest_entries]
                    self.collection.delete_many({'_id': {'$in': oldest_ids}})
                    result.deleted_count += len(oldest_ids)
            
            return result.deleted_count
        
        except Exception as e:
            print(f"Error cleaning up expired entries: {e}")
            return 0
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics and performance metrics."""
        try:
            # Total entries
            total_entries = self.collection.count_documents({})
            
            # Expired entries
            current_time = datetime.utcnow()
            expired_entries = self.collection.count_documents({'expires_at': {'$lt': current_time}})
            
            # Cache hit statistics
            pipeline = [
                {'$group': {
                    '_id': None,
                    'total_hits': {'$sum': '$hit_count'},
                    'avg_hits': {'$avg': '$hit_count'},
                    'max_hits': {'$max': '$hit_count'}
                }}
            ]
            
            hit_stats = list(self.collection.aggregate(pipeline))
            hit_data = hit_stats[0] if hit_stats else {
                'total_hits': 0, 'avg_hits': 0, 'max_hits': 0
            }
            
            # Namespace distribution
            pipeline = [
                {'$project': {
                    'namespace': {'$arrayElemAt': [{'$split': ['$key', ':']}, 0]}
                }},
                {'$group': {'_id': '$namespace', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]
            
            namespace_stats = list(self.collection.aggregate(pipeline))
            
            # Memory usage estimation (rough)
            pipeline = [
                {'$project': {
                    'key_size': {'$strLenCP': '$key'},
                    'value_size': {'$strLenCP': {'$toString': '$value'}}
                }},
                {'$group': {
                    '_id': None,
                    'total_key_size': {'$sum': '$key_size'},
                    'total_value_size': {'$sum': '$value_size'}
                }}
            ]
            
            size_stats = list(self.collection.aggregate(pipeline))
            size_data = size_stats[0] if size_stats else {
                'total_key_size': 0, 'total_value_size': 0
            }
            
            return {
                'total_entries': total_entries,
                'expired_entries': expired_entries,
                'active_entries': total_entries - expired_entries,
                'cache_utilization': (total_entries / self.max_cache_size) * 100,
                'hit_statistics': hit_data,
                'namespace_distribution': namespace_stats,
                'estimated_memory_kb': (size_data['total_key_size'] + size_data['total_value_size']) / 1024,
                'cleanup_needed': expired_entries > 0
            }
        
        except Exception as e:
            print(f"Error getting cache statistics: {e}")
            return {}
    
    def optimize_cache(self) -> Dict[str, int]:
        """Optimize cache by cleaning up expired entries and low-hit entries."""
        try:
            # Clean up expired entries
            expired_cleaned = self._cleanup_expired_entries()
            
            # Remove entries with zero hits that are older than 1 hour
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            unused_result = self.collection.delete_many({
                'hit_count': 0,
                'created_at': {'$lt': one_hour_ago}
            })
            
            return {
                'expired_entries_removed': expired_cleaned,
                'unused_entries_removed': unused_result.deleted_count,
                'total_removed': expired_cleaned + unused_result.deleted_count
            }
        
        except Exception as e:
            print(f"Error optimizing cache: {e}")
            return {'expired_entries_removed': 0, 'unused_entries_removed': 0, 'total_removed': 0}
    
    def get_top_cached_keys(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most frequently accessed cache keys."""
        try:
            pipeline = [
                {'$match': {'expires_at': {'$gt': datetime.utcnow()}}},
                {'$sort': {'hit_count': -1}},
                {'$limit': limit},
                {'$project': {
                    'key': 1,
                    'hit_count': 1,
                    'last_accessed': 1,
                    'expires_at': 1,
                    'ttl': 1
                }}
            ]
            
            return list(self.collection.aggregate(pipeline))
        
        except Exception as e:
            print(f"Error getting top cached keys: {e}")
            return []