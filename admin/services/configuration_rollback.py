"""
Configuration rollback system for critical changes
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from bson import ObjectId

from .base_service import BaseService
from ..models.system import ConfigurationBackup


class ConfigurationRollback(BaseService):
    """Service for managing configuration backups and rollbacks."""
    
    def _get_collection_name(self) -> str:
        return "configuration_backups"
    
    def __init__(self, mongo_db):
        super().__init__(mongo_db)
        self.settings_collection = self.db.admin_settings
        self.max_backups_per_type = 50
        self.auto_backup_threshold = 10  # Auto backup after 10 changes
        self.change_counter = 0
    
    def create_backup(self, backup_name: str, backup_reason: str = "manual", 
                     user_id: Optional[ObjectId] = None, is_automatic: bool = False) -> ObjectId:
        """Create a backup of current configuration."""
        try:
            # Get all current configuration settings
            current_config = {}
            settings = list(self.settings_collection.find())
            
            for setting in settings:
                # Remove MongoDB-specific fields for clean backup
                clean_setting = {k: v for k, v in setting.items() if k not in ['_id']}
                current_config[setting['key']] = clean_setting
            
            # Create backup record
            backup = ConfigurationBackup(
                backup_name=backup_name,
                configuration_data=current_config,
                backup_reason=backup_reason,
                is_automatic=is_automatic,
                created_by=user_id
            )
            
            backup_id = self.create(backup.to_dict(), user_id)
            
            # Clean up old backups if we exceed the limit
            self._cleanup_old_backups()
            
            return backup_id
        
        except Exception as e:
            print(f"Error creating configuration backup: {e}")
            raise
    
    def restore_backup(self, backup_id: ObjectId, user_id: Optional[ObjectId] = None) -> bool:
        """Restore configuration from a backup."""
        try:
            # Get backup record
            backup_record = self.get_by_id(backup_id)
            if not backup_record:
                return False
            
            configuration_data = backup_record.get('configuration_data', {})
            if not configuration_data:
                return False
            
            # Create a backup of current state before restoring
            pre_restore_backup_name = f"pre_restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            self.create_backup(
                backup_name=pre_restore_backup_name,
                backup_reason="automatic_pre_restore",
                user_id=user_id,
                is_automatic=True
            )
            
            # Clear current settings
            self.settings_collection.delete_many({})
            
            # Restore settings from backup
            restored_count = 0
            for setting_key, setting_data in configuration_data.items():
                # Add metadata for restoration
                setting_data.update({
                    'restored_at': datetime.utcnow(),
                    'restored_by': user_id,
                    'restored_from_backup': str(backup_id)
                })
                
                self.settings_collection.insert_one(setting_data)
                restored_count += 1
            
            # Mark backup as restored
            self.update(backup_id, {
                'restored': True,
                'restored_at': datetime.utcnow(),
                'restored_by': user_id
            })
            
            print(f"Restored {restored_count} configuration settings from backup {backup_id}")
            return True
        
        except Exception as e:
            print(f"Error restoring configuration backup: {e}")
            return False
    
    def create_automatic_backup_if_needed(self, user_id: Optional[ObjectId] = None) -> Optional[ObjectId]:
        """Create automatic backup if change threshold is reached."""
        self.change_counter += 1
        
        if self.change_counter >= self.auto_backup_threshold:
            backup_name = f"auto_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            backup_id = self.create_backup(
                backup_name=backup_name,
                backup_reason="automatic_threshold",
                user_id=user_id,
                is_automatic=True
            )
            
            # Reset counter
            self.change_counter = 0
            return backup_id
        
        return None
    
    def create_scheduled_backup(self, user_id: Optional[ObjectId] = None) -> ObjectId:
        """Create a scheduled backup (called by scheduler)."""
        backup_name = f"scheduled_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        return self.create_backup(
            backup_name=backup_name,
            backup_reason="scheduled",
            user_id=user_id,
            is_automatic=True
        )
    
    def compare_configurations(self, backup_id1: ObjectId, backup_id2: ObjectId) -> Dict[str, Any]:
        """Compare two configuration backups and return differences."""
        try:
            backup1 = self.get_by_id(backup_id1)
            backup2 = self.get_by_id(backup_id2)
            
            if not backup1 or not backup2:
                return {'error': 'One or both backups not found'}
            
            config1 = backup1.get('configuration_data', {})
            config2 = backup2.get('configuration_data', {})
            
            # Find differences
            differences = {
                'added': {},      # Settings in config2 but not in config1
                'removed': {},    # Settings in config1 but not in config2
                'modified': {},   # Settings that exist in both but with different values
                'unchanged': {}   # Settings that are identical
            }
            
            all_keys = set(config1.keys()) | set(config2.keys())
            
            for key in all_keys:
                if key in config1 and key in config2:
                    if config1[key] != config2[key]:
                        differences['modified'][key] = {
                            'old_value': config1[key],
                            'new_value': config2[key]
                        }
                    else:
                        differences['unchanged'][key] = config1[key]
                elif key in config2:
                    differences['added'][key] = config2[key]
                else:
                    differences['removed'][key] = config1[key]
            
            return {
                'backup1_id': str(backup_id1),
                'backup2_id': str(backup_id2),
                'backup1_name': backup1.get('backup_name'),
                'backup2_name': backup2.get('backup_name'),
                'backup1_date': backup1.get('created_at'),
                'backup2_date': backup2.get('created_at'),
                'differences': differences,
                'summary': {
                    'total_settings_backup1': len(config1),
                    'total_settings_backup2': len(config2),
                    'added_count': len(differences['added']),
                    'removed_count': len(differences['removed']),
                    'modified_count': len(differences['modified']),
                    'unchanged_count': len(differences['unchanged'])
                }
            }
        
        except Exception as e:
            return {'error': f'Error comparing configurations: {e}'}
    
    def get_backup_history(self, limit: int = 20, backup_type: str = None) -> List[Dict[str, Any]]:
        """Get backup history with optional filtering."""
        query = {}
        if backup_type:
            query['backup_reason'] = backup_type
        
        backups = self.find(
            query=query,
            limit=limit,
            sort=[('created_at', -1)]
        )
        
        # Add summary information
        for backup in backups:
            config_data = backup.get('configuration_data', {})
            backup['settings_count'] = len(config_data)
            backup['backup_size_estimate'] = len(str(config_data))
        
        return backups
    
    def delete_backup(self, backup_id: ObjectId, user_id: Optional[ObjectId] = None) -> bool:
        """Delete a configuration backup."""
        try:
            # Check if backup was ever restored
            backup_record = self.get_by_id(backup_id)
            if backup_record and backup_record.get('restored'):
                # Don't allow deletion of restored backups for audit trail
                return False
            
            return self.delete(backup_id)
        
        except Exception as e:
            print(f"Error deleting backup: {e}")
            return False
    
    def _cleanup_old_backups(self) -> int:
        """Clean up old backups based on retention policy."""
        try:
            # Keep only the most recent backups for each type
            backup_types = ['manual', 'automatic_threshold', 'scheduled', 'automatic_pre_restore']
            cleaned_count = 0
            
            for backup_type in backup_types:
                # Get all backups of this type, sorted by creation date (newest first)
                backups = self.find(
                    query={'backup_reason': backup_type},
                    sort=[('created_at', -1)]
                )
                
                # Delete excess backups (keep only max_backups_per_type)
                if len(backups) > self.max_backups_per_type:
                    excess_backups = backups[self.max_backups_per_type:]
                    
                    for backup in excess_backups:
                        # Don't delete restored backups
                        if not backup.get('restored', False):
                            if self.delete(backup['_id']):
                                cleaned_count += 1
            
            # Also clean up very old backups (older than 90 days) regardless of type
            ninety_days_ago = datetime.utcnow() - timedelta(days=90)
            old_backups = self.find({
                'created_at': {'$lt': ninety_days_ago},
                'restored': {'$ne': True}  # Don't delete restored backups
            })
            
            for backup in old_backups:
                if self.delete(backup['_id']):
                    cleaned_count += 1
            
            return cleaned_count
        
        except Exception as e:
            print(f"Error cleaning up old backups: {e}")
            return 0
    
    def get_rollback_statistics(self) -> Dict[str, Any]:
        """Get statistics about configuration backups and rollbacks."""
        try:
            total_backups = self.count()
            manual_backups = self.count({'backup_reason': 'manual'})
            automatic_backups = self.count({'is_automatic': True})
            restored_backups = self.count({'restored': True})
            
            # Get recent backup activity
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_backups = self.count({'created_at': {'$gte': seven_days_ago}})
            
            # Get backup size statistics
            pipeline = [
                {'$project': {
                    'settings_count': {'$size': {'$objectToArray': '$configuration_data'}},
                    'backup_reason': 1,
                    'created_at': 1
                }},
                {'$group': {
                    '_id': None,
                    'avg_settings_per_backup': {'$avg': '$settings_count'},
                    'max_settings_per_backup': {'$max': '$settings_count'},
                    'min_settings_per_backup': {'$min': '$settings_count'}
                }}
            ]
            
            size_stats = list(self.collection.aggregate(pipeline))
            size_data = size_stats[0] if size_stats else {
                'avg_settings_per_backup': 0,
                'max_settings_per_backup': 0,
                'min_settings_per_backup': 0
            }
            
            # Get latest backup info
            latest_backup = self.find(limit=1, sort=[('created_at', -1)])
            latest_backup_info = latest_backup[0] if latest_backup else None
            
            return {
                'total_backups': total_backups,
                'manual_backups': manual_backups,
                'automatic_backups': automatic_backups,
                'restored_backups': restored_backups,
                'recent_backups_7_days': recent_backups,
                'restore_rate': (restored_backups / total_backups * 100) if total_backups > 0 else 0,
                'size_statistics': size_data,
                'latest_backup': latest_backup_info,
                'change_counter': self.change_counter,
                'auto_backup_threshold': self.auto_backup_threshold
            }
        
        except Exception as e:
            print(f"Error getting rollback statistics: {e}")
            return {}
    
    def validate_backup_integrity(self, backup_id: ObjectId) -> Dict[str, Any]:
        """Validate the integrity of a backup."""
        try:
            backup_record = self.get_by_id(backup_id)
            if not backup_record:
                return {'valid': False, 'error': 'Backup not found'}
            
            configuration_data = backup_record.get('configuration_data', {})
            
            validation_results = {
                'valid': True,
                'backup_id': str(backup_id),
                'backup_name': backup_record.get('backup_name'),
                'settings_count': len(configuration_data),
                'issues': []
            }
            
            # Check for empty configuration
            if not configuration_data:
                validation_results['issues'].append('Configuration data is empty')
                validation_results['valid'] = False
            
            # Validate each setting
            for setting_key, setting_data in configuration_data.items():
                if not isinstance(setting_data, dict):
                    validation_results['issues'].append(f'Setting {setting_key} is not a valid object')
                    validation_results['valid'] = False
                    continue
                
                # Check required fields
                required_fields = ['key', 'value']
                for field in required_fields:
                    if field not in setting_data:
                        validation_results['issues'].append(f'Setting {setting_key} missing required field: {field}')
                        validation_results['valid'] = False
            
            return validation_results
        
        except Exception as e:
            return {'valid': False, 'error': f'Error validating backup: {e}'}