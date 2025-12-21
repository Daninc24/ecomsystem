"""
Simple MongoDB Mock for testing without actual MongoDB installation
This provides basic MongoDB-like functionality using JSON files
"""

import json
import os
from datetime import datetime
from bson import ObjectId
import uuid

class MockCollection:
    def __init__(self, name, db_path):
        self.name = name
        self.db_path = db_path
        self.file_path = os.path.join(db_path, f"{name}.json")
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        os.makedirs(self.db_path, exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump([], f)
    
    def _load_data(self):
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
                # Convert string IDs back to ObjectId for consistency
                for item in data:
                    if '_id' in item and isinstance(item['_id'], str):
                        try:
                            item['_id'] = ObjectId(item['_id'])
                        except:
                            pass
                return data
        except:
            return []
    
    def _save_data(self, data):
        # Convert ObjectId to string for JSON serialization
        serializable_data = []
        for item in data:
            item_copy = item.copy()
            if '_id' in item_copy and isinstance(item_copy['_id'], ObjectId):
                item_copy['_id'] = str(item_copy['_id'])
            # Convert datetime objects to ISO strings
            for key, value in item_copy.items():
                if isinstance(value, datetime):
                    item_copy[key] = value.isoformat()
                elif isinstance(value, dict):
                    for k, v in value.items():
                        if isinstance(v, datetime):
                            value[k] = v.isoformat()
            serializable_data.append(item_copy)
        
        with open(self.file_path, 'w') as f:
            json.dump(serializable_data, f, indent=2, default=str)
    
    def find_one(self, query=None):
        data = self._load_data()
        if not query:
            return data[0] if data else None
        
        for item in data:
            if self._matches_query(item, query):
                return item
        return None
    
    def find(self, query=None):
        data = self._load_data()
        if not query:
            return MockCursor(data)
        
        results = [item for item in data if self._matches_query(item, query)]
        return MockCursor(results)
    
    def insert_one(self, document):
        data = self._load_data()
        if '_id' not in document:
            document['_id'] = ObjectId()
        data.append(document)
        self._save_data(data)
        return MockInsertResult(document['_id'])
    
    def update_one(self, query, update):
        data = self._load_data()
        for item in data:
            if self._matches_query(item, query):
                if '$set' in update:
                    item.update(update['$set'])
                if '$inc' in update:
                    for key, value in update['$inc'].items():
                        item[key] = item.get(key, 0) + value
                break
        self._save_data(data)
        return MockUpdateResult()
    
    def delete_many(self, query):
        data = self._load_data()
        original_count = len(data)
        data = [item for item in data if not self._matches_query(item, query)]
        self._save_data(data)
        return MockDeleteResult(original_count - len(data))
    
    def delete_one(self, query):
        data = self._load_data()
        for i, item in enumerate(data):
            if self._matches_query(item, query):
                del data[i]
                self._save_data(data)
                return MockDeleteResult(1)
        return MockDeleteResult(0)
    
    def count_documents(self, query=None):
        data = self._load_data()
        if not query:
            return len(data)
        return len([item for item in data if self._matches_query(item, query)])
    
    def create_index(self, keys, unique=False):
        # Mock index creation - just return success
        return True
    
    def _matches_query(self, item, query):
        """Simple query matching - supports basic equality and $or"""
        if not query:
            return True
        
        for key, value in query.items():
            if key == '$or':
                # Handle $or queries
                if not any(self._matches_query(item, or_query) for or_query in value):
                    return False
            elif '.' in key:
                # Handle nested keys like 'basic_info.name'
                keys = key.split('.')
                current = item
                for k in keys:
                    if isinstance(current, dict) and k in current:
                        current = current[k]
                    else:
                        return False
                if isinstance(value, dict):
                    if '$regex' in value:
                        import re
                        pattern = value['$regex']
                        flags = re.IGNORECASE if value.get('$options') == 'i' else 0
                        if not re.search(pattern, str(current), flags):
                            return False
                    elif '$in' in value:
                        if current not in value['$in']:
                            return False
                    elif '$gte' in value:
                        if current < value['$gte']:
                            return False
                    elif '$lte' in value:
                        if current > value['$lte']:
                            return False
                elif current != value:
                    # Handle ObjectId comparison - convert both to strings for comparison
                    current_value = str(current) if hasattr(current, '__str__') else current
                    query_value = str(value) if hasattr(value, '__str__') else value
                    if current_value != query_value:
                        return False
            elif key in item:
                if isinstance(value, dict):
                    if '$regex' in value:
                        import re
                        pattern = value['$regex']
                        flags = re.IGNORECASE if value.get('$options') == 'i' else 0
                        if not re.search(pattern, str(item[key]), flags):
                            return False
                    elif '$in' in value:
                        if item[key] not in value['$in']:
                            return False
                elif item[key] != value:
                    # Handle ObjectId comparison - convert both to strings for comparison
                    item_value = str(item[key]) if hasattr(item[key], '__str__') else item[key]
                    query_value = str(value) if hasattr(value, '__str__') else value
                    if item_value != query_value:
                        return False
            else:
                return False
        return True

class MockCursor:
    def __init__(self, data):
        self.data = data
        self._limit = None
        self._skip = 0
        self._sort_key = None
        self._sort_direction = 1
    
    def limit(self, count):
        self._limit = count
        return self
    
    def skip(self, count):
        self._skip = count
        return self
    
    def sort(self, key, direction=1):
        self._sort_key = key
        self._sort_direction = direction
        return self
    
    def __iter__(self):
        data = self.data.copy()
        
        # Apply sorting
        if self._sort_key:
            reverse = self._sort_direction == -1
            try:
                if '.' in self._sort_key:
                    # Handle nested keys
                    def get_nested_value(item, key):
                        keys = key.split('.')
                        current = item
                        for k in keys:
                            if isinstance(current, dict) and k in current:
                                current = current[k]
                            else:
                                return None
                        return current
                    data.sort(key=lambda x: get_nested_value(x, self._sort_key) or '', reverse=reverse)
                else:
                    data.sort(key=lambda x: x.get(self._sort_key, ''), reverse=reverse)
            except:
                pass
        
        # Apply skip and limit
        if self._skip:
            data = data[self._skip:]
        if self._limit:
            data = data[:self._limit]
        
        return iter(data)

class MockInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id

class MockUpdateResult:
    def __init__(self):
        self.modified_count = 1

class MockDeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count

class MockDatabase:
    def __init__(self, name, db_path="mock_db"):
        self.name = name
        self.db_path = os.path.join(db_path, name)
        self._collections = {}
    
    def __getattr__(self, name):
        if name not in self._collections:
            self._collections[name] = MockCollection(name, self.db_path)
        return self._collections[name]

class MockMongo:
    def __init__(self, app=None):
        self.app = app
        self.db = MockDatabase("ecommerce")
    
    def init_app(self, app):
        self.app = app

# Create a global mock mongo instance
mock_mongo = MockMongo()