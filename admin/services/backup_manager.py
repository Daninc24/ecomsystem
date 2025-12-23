"""
Backup management service with automated scheduling and restoration
"""

import os
import json
import gzip
import shutil
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from bson import ObjectId
import pymongo

from .base_service import BaseService
from ..models.system import BackupRecord, BackupStatus


class BackupManager(BaseService):
    """Service for managing database and system backups."""
    
    def _get_collection_name(self) -> str:
        return "backup_records"
    
    def __init__(self, mongo_db, backup_directory: str = "/tmp/backups"):
        super().__init__(mongo_db)
        self.backup_directory = backup_directory
        self.ensure_backup_directory()
        
        # Backup retention settings
        self.retention_days = 30
        self.max_backups = 50
    
    def ensure_backup_directory(self) -> None:
        """Ensure backup directory exists."""
        os.makedirs(self.backup_directory, exist_ok=True)
    
    def create_database_backup(self, backup_type: str = "full", user_id: Optional[ObjectId] = None) -> ObjectId:
        """Create a database backup."""
        backup_record = BackupRecord(
            backup_type=backup_type,
            status=BackupStatus.PENDING,
            started_at=datetime.utcnow(),
            created_by=user_id
        )
        
        backup_id = self.create(backup_record.to_dict(), user_id)
        
        try:
            # Update status to in progress
            self.update(backup_id, {'status': BackupStatus.IN_PROGRESS.value})
            
            # Generate backup filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"mongodb_backup_{timestamp}.gz"
            backup_path = os.path.join(self.backup_directory, backup_filename)
            
            # Create MongoDB dump
            success, file_size = self._create_mongodb_dump(backup_path)
            
            if success:
                # Update backup record with success
                self.update(backup_id, {
                    'status': BackupStatus.COMPLETED.value,
                    'file_path': backup_path,
                    'file_size': file_size,
                    'completed_at': datetime.utcnow()
                })
            else:
                # Update backup record with failure
                self.update(backup_id, {
                    'status': BackupStatus.FAILED.value,
                    'error_message': 'Failed to create MongoDB dump',
                    'completed_at': datetime.utcnow()
                })
        
        except Exception as e:
            # Update backup record with error
            self.update(backup_id, {
                'status': BackupStatus.FAILED.value,
                'error_message': str(e),
                'completed_at': datetime.utcnow()
            })
        
        return backup_id
    
    def _create_mongodb_dump(self, backup_path: str) -> tuple[bool, int]:
        """Create MongoDB dump using mongodump."""
        try:
            # Get database name from connection
            db_name = self.db.name
            
            # Create temporary directory for dump
            temp_dir = f"/tmp/mongodump_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # Run mongodump command
                cmd = [
                    'mongodump',
                    '--db', db_name,
                    '--out', temp_dir
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    # Compress the dump
                    with open(backup_path, 'wb') as f_out:
                        with gzip.GzipFile(fileobj=f_out) as gz_out:
                            # Archive the dump directory
                            shutil.make_archive(
                                base_name=f"{temp_dir}/dump",
                                format='tar',
                                root_dir=temp_dir
                            )
                            
                            with open(f"{temp_dir}/dump.tar", 'rb') as f_in:
                                shutil.copyfileobj(f_in, gz_out)
                    
                    file_size = os.path.getsize(backup_path)
                    return True, file_size
                else:
                    print(f"mongodump failed: {result.stderr}")
                    return False, 0
            
            finally:
                # Clean up temporary directory
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
        
        except subprocess.TimeoutExpired:
            print("mongodump timed out")
            return False, 0
        except Exception as e:
            print(f"Error creating MongoDB dump: {e}")
            # Fallback to manual backup
            return self._create_manual_backup(backup_path)
    
    def _create_manual_backup(self, backup_path: str) -> tuple[bool, int]:
        """Create manual backup by exporting collections."""
        try:
            backup_data = {}
            
            # Get all collection names
            collection_names = self.db.list_collection_names()
            
            for collection_name in collection_names:
                collection = getattr(self.db, collection_name)
                documents = list(collection.find())
                
                # Convert ObjectIds to strings for JSON serialization
                for doc in documents:
                    self._convert_objectids_to_strings(doc)
                
                backup_data[collection_name] = documents
            
            # Write compressed JSON backup
            with gzip.open(backup_path, 'wt', encoding='utf-8') as f:
                json.dump(backup_data, f, default=str, indent=2)
            
            file_size = os.path.getsize(backup_path)
            return True, file_size
        
        except Exception as e:
            print(f"Error creating manual backup: {e}")
            return False, 0
    
    def _convert_objectids_to_strings(self, obj):
        """Recursively convert ObjectIds to strings in a document."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, ObjectId):
                    obj[key] = str(value)
                elif isinstance(value, (dict, list)):
                    self._convert_objectids_to_strings(value)
        elif isinstance(obj, list):
            for item in obj:
                self._convert_objectids_to_strings(item)
    
    def restore_backup(self, backup_id: ObjectId, user_id: Optional[ObjectId] = None) -> bool:
        """Restore from a backup."""
        backup_record = self.get_by_id(backup_id)
        if not backup_record:
            return False
        
        backup_path = backup_record.get('file_path')
        if not backup_path or not os.path.exists(backup_path):
            return False
        
        try:
            # Attempt MongoDB restore first
            if self._restore_mongodb_dump(backup_path):
                return True
            else:
                # Fallback to manual restore
                return self._restore_manual_backup(backup_path)
        
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False
    
    def _restore_mongodb_dump(self, backup_path: str) -> bool:
        """Restore MongoDB dump using mongorestore."""
        try:
            # Extract compressed backup
            temp_dir = f"/tmp/mongorestore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # Extract gzipped tar file
                with gzip.open(backup_path, 'rb') as gz_in:
                    with open(f"{temp_dir}/dump.tar", 'wb') as tar_out:
                        shutil.copyfileobj(gz_in, tar_out)
                
                # Extract tar file
                shutil.unpack_archive(f"{temp_dir}/dump.tar", temp_dir)
                
                # Run mongorestore command
                db_name = self.db.name
                cmd = [
                    'mongorestore',
                    '--db', db_name,
                    '--drop',  # Drop existing collections
                    f"{temp_dir}/{db_name}"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                return result.returncode == 0
            
            finally:
                # Clean up temporary directory
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
        
        except Exception as e:
            print(f"Error restoring MongoDB dump: {e}")
            return False
    
    def _restore_manual_backup(self, backup_path: str) -> bool:
        """Restore from manual JSON backup."""
        try:
            # Load backup data
            with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Restore each collection
            for collection_name, documents in backup_data.items():
                collection = getattr(self.db, collection_name)
                
                # Drop existing collection
                collection.drop()
                
                if documents:
                    # Convert string IDs back to ObjectIds
                    for doc in documents:
                        self._convert_strings_to_objectids(doc)
                    
                    # Insert documents
                    collection.insert_many(documents)
            
            return True
        
        except Exception as e:
            print(f"Error restoring manual backup: {e}")
            return False
    
    def _convert_strings_to_objectids(self, obj):
        """Recursively convert string IDs back to ObjectIds."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in ['_id', 'created_by', 'updated_by', 'user_id'] and isinstance(value, str):
                    try:
                        obj[key] = ObjectId(value)
                    except:
                        pass  # Keep as string if not valid ObjectId
                elif isinstance(value, (dict, list)):
                    self._convert_strings_to_objectids(value)
        elif isinstance(obj, list):
            for item in obj:
                self._convert_strings_to_objectids(item)
    
    def schedule_automatic_backup(self, backup_type: str = "full", interval_hours: int = 24) -> bool:
        """Schedule automatic backups (this would typically integrate with a job scheduler)."""
        # This is a placeholder for scheduling logic
        # In a real implementation, this would integrate with cron, celery, or similar
        print(f"Scheduled {backup_type} backup every {interval_hours} hours")
        return True
    
    def cleanup_old_backups(self) -> int:
        """Clean up old backup files based on retention policy."""
        cleaned_count = 0
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        # Find old backup records
        old_backups = self.find({
            'created_at': {'$lt': cutoff_date},
            'status': BackupStatus.COMPLETED.value
        })
        
        for backup in old_backups:
            backup_path = backup.get('file_path')
            if backup_path and os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                    cleaned_count += 1
                except Exception as e:
                    print(f"Error removing backup file {backup_path}: {e}")
            
            # Remove backup record
            self.delete(backup['_id'])
        
        return cleaned_count
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup statistics and status."""
        total_backups = self.count()
        successful_backups = self.count({'status': BackupStatus.COMPLETED.value})
        failed_backups = self.count({'status': BackupStatus.FAILED.value})
        
        # Get latest backup
        latest_backup = self.find(
            {'status': BackupStatus.COMPLETED.value},
            limit=1,
            sort=[('created_at', -1)]
        )
        
        # Calculate total backup size
        completed_backups = self.find({'status': BackupStatus.COMPLETED.value})
        total_size = sum(backup.get('file_size', 0) for backup in completed_backups)
        
        return {
            'total_backups': total_backups,
            'successful_backups': successful_backups,
            'failed_backups': failed_backups,
            'success_rate': (successful_backups / total_backups * 100) if total_backups > 0 else 0,
            'latest_backup': latest_backup[0] if latest_backup else None,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024) if total_size > 0 else 0
        }