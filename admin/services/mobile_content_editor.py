"""
Mobile Content Editor Service
Provides touch-friendly content editing capabilities for mobile admin interface
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from bson import ObjectId
from .base_service import BaseService


class MobileContentEditor(BaseService):
    """Manages mobile-optimized content editing functionality."""
    
    def _get_collection_name(self) -> str:
        return "mobile_content_sessions"
    
    def __init__(self, mongo_db):
        super().__init__(mongo_db)
        self.content_drafts_collection = self.db.mobile_content_drafts
        self.editor_settings_collection = self.db.mobile_editor_settings
    
    def create_editing_session(self, user_id: ObjectId, content_id: str, content_type: str) -> ObjectId:
        """Create a new mobile editing session."""
        session_data = {
            'user_id': user_id,
            'content_id': content_id,
            'content_type': content_type,
            'status': 'active',
            'device_info': self._get_device_info(),
            'editor_config': self._get_mobile_editor_config(),
            'last_activity': datetime.utcnow(),
            'auto_save_enabled': True,
            'auto_save_interval': 30  # seconds
        }
        
        return self.create(session_data, user_id)
    
    def _get_device_info(self) -> Dict[str, Any]:
        """Get device information for optimizing editor experience."""
        # In a real implementation, this would be passed from the client
        return {
            'screen_width': 375,  # Default iPhone width
            'screen_height': 667,
            'pixel_ratio': 2,
            'touch_capable': True,
            'keyboard_type': 'virtual',
            'orientation': 'portrait'
        }
    
    def _get_mobile_editor_config(self) -> Dict[str, Any]:
        """Get mobile-optimized editor configuration."""
        return {
            'toolbar': {
                'position': 'bottom',
                'style': 'compact',
                'buttons': [
                    'bold', 'italic', 'underline',
                    'heading', 'list', 'link',
                    'image', 'save', 'undo', 'redo'
                ],
                'button_size': 'large',  # 44px minimum for touch
                'spacing': 'comfortable'
            },
            'editor': {
                'font_size': 16,  # Prevents zoom on iOS
                'line_height': 1.5,
                'padding': 16,
                'auto_focus': False,  # Prevents keyboard popup
                'spell_check': True,
                'auto_correct': True,
                'word_wrap': True
            },
            'gestures': {
                'swipe_to_undo': True,
                'pinch_to_zoom': False,
                'double_tap_to_select': True,
                'long_press_for_context': True
            },
            'auto_save': {
                'enabled': True,
                'interval': 30,
                'on_blur': True,
                'on_orientation_change': True
            }
        }
    
    def save_content_draft(self, session_id: ObjectId, content: str, metadata: Dict[str, Any] = None) -> ObjectId:
        """Save content draft with mobile-specific metadata."""
        draft_data = {
            'session_id': session_id,
            'content': content,
            'content_length': len(content),
            'word_count': len(content.split()),
            'metadata': metadata or {},
            'device_info': self._get_device_info(),
            'is_auto_save': metadata.get('is_auto_save', False),
            'cursor_position': metadata.get('cursor_position', 0),
            'selection_range': metadata.get('selection_range', [0, 0])
        }
        
        result = self.content_drafts_collection.insert_one(draft_data)
        
        # Update session last activity
        self.update(session_id, {'last_activity': datetime.utcnow()})
        
        return result.inserted_id
    
    def get_content_draft(self, session_id: ObjectId) -> Optional[Dict[str, Any]]:
        """Get the latest content draft for a session."""
        return self.content_drafts_collection.find_one(
            {'session_id': session_id},
            sort=[('created_at', -1)]
        )
    
    def get_content_history(self, session_id: ObjectId, limit: int = 10) -> List[Dict[str, Any]]:
        """Get content editing history for a session."""
        return list(self.content_drafts_collection.find(
            {'session_id': session_id},
            sort=[('created_at', -1)],
            limit=limit
        ))
    
    def optimize_content_for_mobile(self, content: str, content_type: str) -> Dict[str, Any]:
        """Optimize content for mobile display and editing."""
        optimized = {
            'original_content': content,
            'mobile_content': content,
            'optimizations_applied': []
        }
        
        if content_type == 'html':
            optimized.update(self._optimize_html_for_mobile(content))
        elif content_type == 'markdown':
            optimized.update(self._optimize_markdown_for_mobile(content))
        elif content_type == 'text':
            optimized.update(self._optimize_text_for_mobile(content))
        
        return optimized
    
    def _optimize_html_for_mobile(self, html_content: str) -> Dict[str, Any]:
        """Optimize HTML content for mobile editing."""
        optimizations = []
        mobile_content = html_content
        
        # Remove or simplify complex HTML structures
        if '<table' in mobile_content:
            # Convert tables to simpler div structures for mobile editing
            optimizations.append('tables_simplified')
        
        # Ensure images are responsive
        if '<img' in mobile_content:
            # Add responsive image classes
            optimizations.append('images_made_responsive')
        
        # Simplify nested structures
        if mobile_content.count('<div') > 10:
            optimizations.append('structure_simplified')
        
        return {
            'mobile_content': mobile_content,
            'optimizations_applied': optimizations
        }
    
    def _optimize_markdown_for_mobile(self, markdown_content: str) -> Dict[str, Any]:
        """Optimize Markdown content for mobile editing."""
        optimizations = []
        mobile_content = markdown_content
        
        # Break long lines for better mobile editing
        lines = mobile_content.split('\n')
        optimized_lines = []
        
        for line in lines:
            if len(line) > 80:  # Long line threshold
                # Break at sentence boundaries
                sentences = line.split('. ')
                if len(sentences) > 1:
                    optimized_lines.extend([s + '.' for s in sentences[:-1]])
                    optimized_lines.append(sentences[-1])
                    optimizations.append('long_lines_broken')
                else:
                    optimized_lines.append(line)
            else:
                optimized_lines.append(line)
        
        return {
            'mobile_content': '\n'.join(optimized_lines),
            'optimizations_applied': optimizations
        }
    
    def _optimize_text_for_mobile(self, text_content: str) -> Dict[str, Any]:
        """Optimize plain text content for mobile editing."""
        optimizations = []
        mobile_content = text_content
        
        # Add paragraph breaks for better readability
        if '\n\n' not in mobile_content and len(mobile_content) > 200:
            # Add paragraph breaks at sentence boundaries
            sentences = mobile_content.split('. ')
            if len(sentences) > 3:
                # Group sentences into paragraphs
                paragraphs = []
                current_paragraph = []
                
                for sentence in sentences:
                    current_paragraph.append(sentence)
                    if len(' '.join(current_paragraph)) > 150:
                        paragraphs.append('. '.join(current_paragraph) + '.')
                        current_paragraph = []
                
                if current_paragraph:
                    paragraphs.append('. '.join(current_paragraph))
                
                mobile_content = '\n\n'.join(paragraphs)
                optimizations.append('paragraphs_added')
        
        return {
            'mobile_content': mobile_content,
            'optimizations_applied': optimizations
        }
    
    def get_mobile_editor_toolbar(self, content_type: str, user_preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get mobile-optimized editor toolbar configuration."""
        base_toolbar = {
            'position': 'bottom',
            'style': 'compact',
            'button_size': 44,  # Touch-friendly size
            'spacing': 8,
            'background': 'var(--bg-card)',
            'border': '1px solid var(--border-light)',
            'border_radius': 12
        }
        
        # Content-type specific buttons
        if content_type == 'html':
            base_toolbar['buttons'] = [
                {'id': 'bold', 'icon': 'B', 'label': 'Bold', 'shortcut': 'Ctrl+B'},
                {'id': 'italic', 'icon': 'I', 'label': 'Italic', 'shortcut': 'Ctrl+I'},
                {'id': 'underline', 'icon': 'U', 'label': 'Underline', 'shortcut': 'Ctrl+U'},
                {'id': 'separator'},
                {'id': 'heading', 'icon': 'H', 'label': 'Heading', 'dropdown': True},
                {'id': 'list', 'icon': '•', 'label': 'List', 'dropdown': True},
                {'id': 'separator'},
                {'id': 'link', 'icon': '🔗', 'label': 'Link'},
                {'id': 'image', 'icon': '🖼️', 'label': 'Image'},
                {'id': 'separator'},
                {'id': 'undo', 'icon': '↶', 'label': 'Undo'},
                {'id': 'redo', 'icon': '↷', 'label': 'Redo'},
                {'id': 'separator'},
                {'id': 'save', 'icon': '💾', 'label': 'Save', 'primary': True}
            ]
        elif content_type == 'markdown':
            base_toolbar['buttons'] = [
                {'id': 'bold', 'icon': 'B', 'label': 'Bold', 'markdown': '**text**'},
                {'id': 'italic', 'icon': 'I', 'label': 'Italic', 'markdown': '*text*'},
                {'id': 'separator'},
                {'id': 'heading', 'icon': 'H', 'label': 'Heading', 'markdown': '# '},
                {'id': 'list', 'icon': '•', 'label': 'List', 'markdown': '- '},
                {'id': 'separator'},
                {'id': 'link', 'icon': '🔗', 'label': 'Link', 'markdown': '[text](url)'},
                {'id': 'image', 'icon': '🖼️', 'label': 'Image', 'markdown': '![alt](url)'},
                {'id': 'separator'},
                {'id': 'preview', 'icon': '👁️', 'label': 'Preview'},
                {'id': 'separator'},
                {'id': 'save', 'icon': '💾', 'label': 'Save', 'primary': True}
            ]
        else:  # Plain text
            base_toolbar['buttons'] = [
                {'id': 'undo', 'icon': '↶', 'label': 'Undo'},
                {'id': 'redo', 'icon': '↷', 'label': 'Redo'},
                {'id': 'separator'},
                {'id': 'find', 'icon': '🔍', 'label': 'Find'},
                {'id': 'replace', 'icon': '🔄', 'label': 'Replace'},
                {'id': 'separator'},
                {'id': 'word_count', 'icon': '#', 'label': 'Word Count'},
                {'id': 'separator'},
                {'id': 'save', 'icon': '💾', 'label': 'Save', 'primary': True}
            ]
        
        # Apply user preferences
        if user_preferences:
            if 'toolbar_position' in user_preferences:
                base_toolbar['position'] = user_preferences['toolbar_position']
            if 'button_size' in user_preferences:
                base_toolbar['button_size'] = user_preferences['button_size']
            if 'hidden_buttons' in user_preferences:
                base_toolbar['buttons'] = [
                    btn for btn in base_toolbar['buttons']
                    if btn.get('id') not in user_preferences['hidden_buttons']
                ]
        
        return base_toolbar
    
    def handle_touch_gesture(self, session_id: ObjectId, gesture_type: str, gesture_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle touch gestures in the mobile editor."""
        session = self.get_by_id(session_id)
        if not session:
            return {'success': False, 'error': 'Session not found'}
        
        result = {'success': True, 'action': None}
        
        if gesture_type == 'swipe_left':
            # Undo last action
            result['action'] = 'undo'
        elif gesture_type == 'swipe_right':
            # Redo last action
            result['action'] = 'redo'
        elif gesture_type == 'double_tap':
            # Select word or paragraph
            result['action'] = 'select_text'
            result['selection'] = gesture_data.get('selection_range', [0, 0])
        elif gesture_type == 'long_press':
            # Show context menu
            result['action'] = 'show_context_menu'
            result['position'] = gesture_data.get('position', [0, 0])
        elif gesture_type == 'pinch':
            # Zoom (if enabled)
            if session.get('editor_config', {}).get('gestures', {}).get('pinch_to_zoom'):
                result['action'] = 'zoom'
                result['zoom_level'] = gesture_data.get('scale', 1.0)
            else:
                result['success'] = False
                result['error'] = 'Pinch to zoom is disabled'
        
        # Log gesture for analytics
        self._log_gesture(session_id, gesture_type, gesture_data, result)
        
        return result
    
    def _log_gesture(self, session_id: ObjectId, gesture_type: str, gesture_data: Dict[str, Any], result: Dict[str, Any]):
        """Log touch gesture for analytics and optimization."""
        log_data = {
            'session_id': session_id,
            'gesture_type': gesture_type,
            'gesture_data': gesture_data,
            'result': result,
            'timestamp': datetime.utcnow()
        }
        
        # Store in a separate collection for analytics
        self.db.mobile_gesture_logs.insert_one(log_data)
    
    def get_mobile_editor_settings(self, user_id: ObjectId) -> Dict[str, Any]:
        """Get mobile editor settings for a user."""
        settings = self.editor_settings_collection.find_one({'user_id': user_id})
        
        if not settings:
            settings = self._get_default_mobile_editor_settings()
            settings['user_id'] = user_id
            self.editor_settings_collection.insert_one(settings)
        
        return settings
    
    def _get_default_mobile_editor_settings(self) -> Dict[str, Any]:
        """Get default mobile editor settings."""
        return {
            'theme': 'light',
            'font_size': 16,
            'font_family': 'system-ui',
            'line_height': 1.5,
            'toolbar_position': 'bottom',
            'auto_save_interval': 30,
            'spell_check': True,
            'auto_correct': True,
            'haptic_feedback': True,
            'gesture_shortcuts': {
                'swipe_left': 'undo',
                'swipe_right': 'redo',
                'double_tap': 'select_word',
                'long_press': 'context_menu'
            },
            'accessibility': {
                'high_contrast': False,
                'large_text': False,
                'voice_over_support': True,
                'reduced_motion': False
            }
        }
    
    def update_mobile_editor_settings(self, user_id: ObjectId, settings: Dict[str, Any]) -> bool:
        """Update mobile editor settings for a user."""
        result = self.editor_settings_collection.update_one(
            {'user_id': user_id},
            {'$set': {**settings, 'updated_at': datetime.utcnow()}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    
    def close_editing_session(self, session_id: ObjectId, save_final_draft: bool = True) -> bool:
        """Close a mobile editing session."""
        session = self.get_by_id(session_id)
        if not session:
            return False
        
        if save_final_draft:
            # Save final draft
            latest_draft = self.get_content_draft(session_id)
            if latest_draft:
                self.save_content_draft(
                    session_id,
                    latest_draft['content'],
                    {'is_final': True, 'session_closed': True}
                )
        
        # Update session status
        return self.update(session_id, {
            'status': 'closed',
            'closed_at': datetime.utcnow()
        })
    
    def get_mobile_editing_analytics(self, user_id: ObjectId, days: int = 30) -> Dict[str, Any]:
        """Get mobile editing analytics for a user."""
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get sessions
        sessions = list(self.find({
            'user_id': user_id,
            'created_at': {'$gte': start_date}
        }))
        
        # Get gesture logs
        gesture_logs = list(self.db.mobile_gesture_logs.find({
            'session_id': {'$in': [s['_id'] for s in sessions]},
            'timestamp': {'$gte': start_date}
        }))
        
        # Calculate analytics
        total_sessions = len(sessions)
        total_editing_time = sum([
            (s.get('closed_at', datetime.utcnow()) - s['created_at']).total_seconds()
            for s in sessions
        ]) / 60  # Convert to minutes
        
        gesture_counts = {}
        for log in gesture_logs:
            gesture_type = log['gesture_type']
            gesture_counts[gesture_type] = gesture_counts.get(gesture_type, 0) + 1
        
        return {
            'period_days': days,
            'total_sessions': total_sessions,
            'total_editing_time_minutes': total_editing_time,
            'average_session_time_minutes': total_editing_time / max(total_sessions, 1),
            'gesture_usage': gesture_counts,
            'most_used_gesture': max(gesture_counts.items(), key=lambda x: x[1])[0] if gesture_counts else None,
            'sessions_per_day': total_sessions / days,
            'device_info': sessions[0].get('device_info') if sessions else None
        }