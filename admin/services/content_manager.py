"""
Content Management Service for SQLite
Handles content editing and management with version control
"""

from typing import Any, Dict, Optional, List
from datetime import datetime, timezone
from models_sqlite import AdminSetting, ActivityLog, db
import json
import hashlib


class ContentManager:
    """Advanced service for managing content with version control and real-time editing."""
    
    def __init__(self, database):
        self.db = database
        self.content_cache = {}
        self.version_history = {}
    
    def edit_content(self, element_id: str, content: str, user_id: Optional[int] = None, 
                    content_type: str = 'html') -> Dict[str, Any]:
        """Edit content and create version with validation."""
        try:
            # Validate content
            validation = self._validate_content(content, content_type)
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors']
                }
            
            # Get current content for comparison
            current_content = self.get_content(element_id)
            
            # Create content hash for deduplication
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Check if content actually changed
            if current_content and current_content.get('content') == content:
                return {
                    'success': True,
                    'message': 'No changes detected',
                    'version_id': current_content.get('version_id')
                }
            
            # Create new version
            version_id = f"v_{datetime.now().timestamp()}_{content_hash[:8]}"
            
            # Store content version
            content_data = {
                'element_id': element_id,
                'content': content,
                'content_type': content_type,
                'version_id': version_id,
                'content_hash': content_hash,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'created_by': user_id,
                'is_published': False,
                'metadata': {
                    'word_count': len(content.split()) if content_type == 'text' else None,
                    'character_count': len(content),
                    'content_type': content_type
                }
            }
            
            # Save to database as admin setting
            setting_key = f'content_{element_id}'
            setting = AdminSetting.query.filter_by(key=setting_key).first()
            
            if setting:
                # Store old version in history
                old_content = json.loads(setting.value) if setting.value else {}
                self._store_version_history(element_id, old_content)
                
                setting.set_value(json.dumps(content_data))
                setting.updated_at = datetime.now(timezone.utc)
                if user_id:
                    setting.updated_by = user_id
            else:
                setting = AdminSetting(
                    key=setting_key,
                    category='content',
                    description=f'Content for element: {element_id}',
                    data_type='json',
                    updated_by=user_id
                )
                setting.set_value(json.dumps(content_data))
                db.session.add(setting)
            
            db.session.commit()
            
            # Clear cache
            self.content_cache.pop(element_id, None)
            
            # Log content change
            self._log_content_change('edit', element_id, user_id, {
                'version_id': version_id,
                'content_type': content_type,
                'content_length': len(content)
            })
            
            return {
                'success': True,
                'version_id': version_id,
                'element_id': element_id,
                'content_hash': content_hash,
                'created_at': content_data['created_at'],
                'metadata': content_data['metadata']
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def get_content(self, element_id: str, version_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get current content for element or specific version."""
        try:
            # Check cache first
            cache_key = f"{element_id}_{version_id or 'current'}"
            if cache_key in self.content_cache:
                return self.content_cache[cache_key]
            
            if version_id:
                # Get specific version from history
                content_data = self._get_version_from_history(element_id, version_id)
            else:
                # Get current content
                setting = AdminSetting.query.filter_by(key=f'content_{element_id}').first()
                if setting and setting.value:
                    content_data = json.loads(setting.value)
                else:
                    content_data = None
            
            if content_data:
                # Cache the result
                self.content_cache[cache_key] = content_data
                return content_data
            
            return None
            
        except Exception as e:
            return None
    
    def publish_content(self, element_id: str, version_id: Optional[str] = None, 
                       user_id: Optional[int] = None) -> Dict[str, Any]:
        """Publish content version."""
        try:
            content_data = self.get_content(element_id, version_id)
            if not content_data:
                return {
                    'success': False,
                    'error': 'Content not found'
                }
            
            # Mark as published
            content_data['is_published'] = True
            content_data['published_at'] = datetime.now(timezone.utc).isoformat()
            content_data['published_by'] = user_id
            
            # Update in database
            setting = AdminSetting.query.filter_by(key=f'content_{element_id}').first()
            if setting:
                setting.set_value(json.dumps(content_data))
                setting.updated_at = datetime.now(timezone.utc)
                if user_id:
                    setting.updated_by = user_id
                db.session.commit()
                
                # Clear cache
                self.content_cache.clear()
                
                # Log publication
                self._log_content_change('publish', element_id, user_id, {
                    'version_id': content_data['version_id'],
                    'published_at': content_data['published_at']
                })
                
                return {
                    'success': True,
                    'element_id': element_id,
                    'version_id': content_data['version_id'],
                    'published_at': content_data['published_at']
                }
            
            return {
                'success': False,
                'error': 'Failed to update content'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_version_history(self, element_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get version history for an element."""
        try:
            # Get current version
            current = self.get_content(element_id)
            versions = []
            
            if current:
                versions.append({
                    'version_id': current['version_id'],
                    'created_at': current['created_at'],
                    'created_by': current.get('created_by'),
                    'is_published': current.get('is_published', False),
                    'is_current': True,
                    'metadata': current.get('metadata', {})
                })
            
            # Get historical versions
            history_key = f'content_history_{element_id}'
            history_setting = AdminSetting.query.filter_by(key=history_key).first()
            
            if history_setting and history_setting.value:
                history_data = json.loads(history_setting.value)
                for version in history_data.get('versions', [])[:limit-1]:
                    versions.append({
                        'version_id': version['version_id'],
                        'created_at': version['created_at'],
                        'created_by': version.get('created_by'),
                        'is_published': version.get('is_published', False),
                        'is_current': False,
                        'metadata': version.get('metadata', {})
                    })
            
            return sorted(versions, key=lambda x: x['created_at'], reverse=True)
            
        except Exception as e:
            return []
    
    def rollback_content(self, element_id: str, version_id: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Rollback content to a previous version."""
        try:
            # Get the target version
            target_content = self._get_version_from_history(element_id, version_id)
            if not target_content:
                return {
                    'success': False,
                    'error': 'Version not found'
                }
            
            # Create new version based on the target
            new_version_id = f"rollback_{datetime.now().timestamp()}_{version_id}"
            rollback_content = target_content.copy()
            rollback_content.update({
                'version_id': new_version_id,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'created_by': user_id,
                'is_published': False,
                'rollback_from': version_id
            })
            
            # Save as new current version
            setting = AdminSetting.query.filter_by(key=f'content_{element_id}').first()
            if setting:
                # Store current version in history
                current_content = json.loads(setting.value) if setting.value else {}
                self._store_version_history(element_id, current_content)
                
                setting.set_value(json.dumps(rollback_content))
                setting.updated_at = datetime.now(timezone.utc)
                if user_id:
                    setting.updated_by = user_id
                db.session.commit()
                
                # Clear cache
                self.content_cache.clear()
                
                # Log rollback
                self._log_content_change('rollback', element_id, user_id, {
                    'new_version_id': new_version_id,
                    'rollback_from': version_id
                })
                
                return {
                    'success': True,
                    'element_id': element_id,
                    'new_version_id': new_version_id,
                    'rollback_from': version_id
                }
            
            return {
                'success': False,
                'error': 'Content not found'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_content_elements(self) -> List[Dict[str, Any]]:
        """List all content elements."""
        try:
            content_settings = AdminSetting.query.filter(
                AdminSetting.key.like('content_%'),
                ~AdminSetting.key.like('content_history_%')
            ).all()
            
            elements = []
            for setting in content_settings:
                element_id = setting.key.replace('content_', '')
                try:
                    content_data = json.loads(setting.value) if setting.value else {}
                    elements.append({
                        'element_id': element_id,
                        'version_id': content_data.get('version_id'),
                        'content_type': content_data.get('content_type', 'html'),
                        'is_published': content_data.get('is_published', False),
                        'created_at': content_data.get('created_at'),
                        'updated_at': setting.updated_at.isoformat() if setting.updated_at else None,
                        'metadata': content_data.get('metadata', {})
                    })
                except json.JSONDecodeError:
                    continue
            
            return sorted(elements, key=lambda x: x['updated_at'] or '', reverse=True)
            
        except Exception as e:
            return []
    
    def search_content(self, query: str, content_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search content by text."""
        try:
            elements = self.list_content_elements()
            results = []
            
            query_lower = query.lower()
            
            for element in elements:
                content_data = self.get_content(element['element_id'])
                if not content_data:
                    continue
                
                # Filter by content type if specified
                if content_type and content_data.get('content_type') != content_type:
                    continue
                
                # Search in content
                content = content_data.get('content', '').lower()
                if query_lower in content:
                    # Calculate relevance score
                    score = content.count(query_lower)
                    results.append({
                        'element_id': element['element_id'],
                        'content_preview': content_data.get('content', '')[:200] + '...',
                        'relevance_score': score,
                        'metadata': element['metadata']
                    })
            
            # Sort by relevance
            return sorted(results, key=lambda x: x['relevance_score'], reverse=True)
            
        except Exception as e:
            return []
    
    def _validate_content(self, content: str, content_type: str) -> Dict[str, Any]:
        """Validate content based on type."""
        errors = []
        
        if not content:
            errors.append('Content cannot be empty')
            return {'valid': False, 'errors': errors}
        
        # Length validation
        if len(content) > 1000000:  # 1MB limit
            errors.append('Content too large (max 1MB)')
        
        # HTML validation (basic)
        if content_type == 'html':
            # Check for potentially dangerous tags
            dangerous_tags = ['<script', '<iframe', '<object', '<embed']
            for tag in dangerous_tags:
                if tag in content.lower():
                    errors.append(f'Potentially dangerous tag detected: {tag}')
        
        # JSON validation
        if content_type == 'json':
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                errors.append(f'Invalid JSON format: {str(e)}')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _store_version_history(self, element_id: str, content_data: Dict[str, Any]):
        """Store version in history."""
        try:
            if not content_data or not content_data.get('version_id'):
                return
            
            history_key = f'content_history_{element_id}'
            history_setting = AdminSetting.query.filter_by(key=history_key).first()
            
            if history_setting and history_setting.value:
                history_data = json.loads(history_setting.value)
            else:
                history_data = {'versions': []}
                if not history_setting:
                    history_setting = AdminSetting(
                        key=history_key,
                        category='content',
                        description=f'Version history for {element_id}',
                        data_type='json'
                    )
                    db.session.add(history_setting)
            
            # Add to history (keep last 50 versions)
            history_data['versions'].insert(0, content_data)
            history_data['versions'] = history_data['versions'][:50]
            
            history_setting.set_value(json.dumps(history_data))
            history_setting.updated_at = datetime.now(timezone.utc)
            
        except Exception:
            pass  # Don't fail main operation if history fails
    
    def _get_version_from_history(self, element_id: str, version_id: str) -> Optional[Dict[str, Any]]:
        """Get specific version from history."""
        try:
            # Check current version first
            current = self.get_content(element_id)
            if current and current.get('version_id') == version_id:
                return current
            
            # Check history
            history_key = f'content_history_{element_id}'
            history_setting = AdminSetting.query.filter_by(key=history_key).first()
            
            if history_setting and history_setting.value:
                history_data = json.loads(history_setting.value)
                for version in history_data.get('versions', []):
                    if version.get('version_id') == version_id:
                        return version
            
            return None
            
        except Exception:
            return None
    
    def _log_content_change(self, action: str, element_id: str, user_id: Optional[int], details: Dict[str, Any]):
        """Log content changes."""
        try:
            log = ActivityLog(
                user_id=user_id,
                action=f'content_{action}',
                resource_type='content',
                resource_id=element_id,
                success=True
            )
            log.set_details(details)
            db.session.add(log)
            db.session.commit()
        except Exception:
            pass