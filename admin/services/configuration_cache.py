"""
Configuration Cache for frequently accessed settings
Provides high-performance caching with TTL, hit counting, and cache management
"""

from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from threading import Lock
import logging
from ..models.configuration import ConfigurationCache as CacheModel


class CacheEntry:
    """Represents a cached configuration entry."""
    
    def __init__(self, key: str, value: Any, ttl: timedelta = None):
        self.key = key
        self.value = value
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + (ttl or timedelta(hours=1))
        self.hit_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return datetime.utcnow() > self.expires_at
    
    def access(self) -> Any:
        """Record an access and return the cached value."""
        self.hit_count += 1
        self.last_accessed = datetime.utcnow()
        return self.value
    
    def refresh_ttl(self, ttl: timedelta = None) -> None:
        """Refresh the TTL of this cache entry."""
        self.expires_at = datetime.utcnow() + (ttl or timedelta(hours=1))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert cache entry to dictionary."""
        return {
            'key': self.key,
            'value': self.value,
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'hit_count': self.hit_count,
            'last_accessed': self.last_accessed
        }


class ConfigurationCache:
    """High-performance cache for configuration settings."""
    
    def __init__(self, mongo_db=None, default_ttl: timedelta = None, max_size: int = 1000):
        self.mongo_db = mongo_db
        self.cache_collection = mongo_db.admin_config_cache if mongo_db else None
        self.default_ttl = default_ttl or timedelta(hours=1)
        self.max_size = max_size
        
        # In-memory cache for ultra-fast access
        self.memory_cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired_removals': 0
        }
    
    def get(self, key: str, use_memory_cache: bool = True) -> Optional[Any]:
        """Get a value from the cache."""
        # Try memory cache first if enabled
        if use_memory_cache:
            with self._lock:
                if key in self.memory_cache:
                    entry = self.memory_cache[key]
                    if not entry.is_expired():
                        self.stats['hits'] += 1
                        return entry.access()
                    else:
                        # Remove expired entry
                        del self.memory_cache[key]
                        self.stats['expired_removals'] += 1
        
        # Try persistent cache if available
        if self.cache_collection:
            cache_doc = self.cache_collection.find_one({'key': key})
            if cache_doc:
                cache_entry = CacheModel.from_dict(cache_doc)
                if not cache_entry.is_expired():
                    # Update access statistics in database
                    self.cache_collection.update_one(
                        {'_id': cache_entry.id},
                        {
                            '$inc': {'hit_count': 1},
                            '$set': {'last_accessed': datetime.utcnow()}
                        }
                    )
                    
                    # Add to memory cache for faster future access
                    if use_memory_cache:
                        with self._lock:
                            self._add_to_memory_cache(key, cache_entry.value, self.default_ttl)
                    
                    self.stats['hits'] += 1
                    return cache_entry.value
                else:
                    # Remove expired entry from database
                    self.cache_collection.delete_one({'_id': cache_entry.id})
                    self.stats['expired_removals'] += 1
        
        self.stats['misses'] += 1
        return None
    
    def set(self, key: str, value: Any, ttl: timedelta = None, persist: bool = True) -> None:
        """Set a value in the cache."""
        cache_ttl = ttl or self.default_ttl
        
        # Add to memory cache
        with self._lock:
            self._add_to_memory_cache(key, value, cache_ttl)
        
        # Add to persistent cache if available and requested
        if persist and self.cache_collection:
            expires_at = datetime.utcnow() + cache_ttl
            cache_data = {
                'key': key,
                'value': value,
                'expires_at': expires_at,
                'hit_count': 0,
                'last_accessed': datetime.utcnow()
            }
            
            # Upsert the cache entry
            self.cache_collection.replace_one(
                {'key': key},
                cache_data,
                upsert=True
            )
    
    def _add_to_memory_cache(self, key: str, value: Any, ttl: timedelta) -> None:
        """Add entry to memory cache with size management."""
        # Remove expired entries first
        self._cleanup_expired_memory_entries()
        
        # If at max size, remove least recently used entry
        if len(self.memory_cache) >= self.max_size:
            lru_key = min(
                self.memory_cache.keys(),
                key=lambda k: self.memory_cache[k].last_accessed
            )
            del self.memory_cache[lru_key]
            self.stats['evictions'] += 1
        
        # Add new entry
        self.memory_cache[key] = CacheEntry(key, value, ttl)
    
    def _cleanup_expired_memory_entries(self) -> int:
        """Remove expired entries from memory cache."""
        expired_keys = [
            key for key, entry in self.memory_cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self.memory_cache[key]
        
        self.stats['expired_removals'] += len(expired_keys)
        return len(expired_keys)
    
    def invalidate(self, key: str) -> bool:
        """Remove a specific key from all caches."""
        removed = False
        
        # Remove from memory cache
        with self._lock:
            if key in self.memory_cache:
                del self.memory_cache[key]
                removed = True
        
        # Remove from persistent cache
        if self.cache_collection:
            result = self.cache_collection.delete_one({'key': key})
            if result.deleted_count > 0:
                removed = True
        
        return removed
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Remove all keys matching a pattern from all caches."""
        import re
        removed_count = 0
        
        # Remove from memory cache
        with self._lock:
            matching_keys = [
                key for key in self.memory_cache.keys()
                if re.match(pattern, key)
            ]
            for key in matching_keys:
                del self.memory_cache[key]
                removed_count += 1
        
        # Remove from persistent cache
        if self.cache_collection:
            # MongoDB doesn't support regex in delete operations directly,
            # so we need to find and delete
            matching_docs = self.cache_collection.find({'key': {'$regex': pattern}})
            for doc in matching_docs:
                self.cache_collection.delete_one({'_id': doc['_id']})
                removed_count += 1
        
        return removed_count
    
    def clear(self) -> int:
        """Clear all cached entries."""
        removed_count = 0
        
        # Clear memory cache
        with self._lock:
            removed_count += len(self.memory_cache)
            self.memory_cache.clear()
        
        # Clear persistent cache
        if self.cache_collection:
            result = self.cache_collection.delete_many({})
            removed_count += result.deleted_count
        
        return removed_count
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries from all caches."""
        removed_count = 0
        
        # Clean memory cache
        with self._lock:
            removed_count += self._cleanup_expired_memory_entries()
        
        # Clean persistent cache
        if self.cache_collection:
            result = self.cache_collection.delete_many({
                'expires_at': {'$lt': datetime.utcnow()}
            })
            removed_count += result.deleted_count
        
        return removed_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            memory_size = len(self.memory_cache)
            memory_expired = sum(1 for entry in self.memory_cache.values() if entry.is_expired())
        
        persistent_size = 0
        if self.cache_collection:
            persistent_size = self.cache_collection.count_documents({})
        
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'memory_cache_size': memory_size,
            'memory_cache_expired': memory_expired,
            'persistent_cache_size': persistent_size,
            'total_hits': self.stats['hits'],
            'total_misses': self.stats['misses'],
            'hit_rate_percent': round(hit_rate, 2),
            'evictions': self.stats['evictions'],
            'expired_removals': self.stats['expired_removals'],
            'max_size': self.max_size
        }
    
    def get_cache_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get information about cached entries."""
        entries = []
        
        # Get from memory cache
        with self._lock:
            for entry in list(self.memory_cache.values())[:limit]:
                entry_info = entry.to_dict()
                entry_info['source'] = 'memory'
                entries.append(entry_info)
        
        # Get from persistent cache if we need more entries
        if len(entries) < limit and self.cache_collection:
            remaining = limit - len(entries)
            docs = self.cache_collection.find().limit(remaining)
            for doc in docs:
                cache_entry = CacheModel.from_dict(doc)
                entry_info = {
                    'key': cache_entry.key,
                    'value': cache_entry.value,
                    'created_at': cache_entry.created_at,
                    'expires_at': cache_entry.expires_at,
                    'hit_count': cache_entry.hit_count,
                    'last_accessed': cache_entry.last_accessed,
                    'source': 'persistent'
                }
                entries.append(entry_info)
        
        return entries
    
    def refresh_ttl(self, key: str, ttl: timedelta = None) -> bool:
        """Refresh the TTL for a specific cache entry."""
        cache_ttl = ttl or self.default_ttl
        refreshed = False
        
        # Refresh in memory cache
        with self._lock:
            if key in self.memory_cache:
                self.memory_cache[key].refresh_ttl(cache_ttl)
                refreshed = True
        
        # Refresh in persistent cache
        if self.cache_collection:
            new_expires_at = datetime.utcnow() + cache_ttl
            result = self.cache_collection.update_one(
                {'key': key},
                {'$set': {'expires_at': new_expires_at}}
            )
            if result.modified_count > 0:
                refreshed = True
        
        return refreshed