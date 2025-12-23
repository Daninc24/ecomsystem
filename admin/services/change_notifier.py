"""
Change Notifier system for broadcasting configuration changes
Handles real-time notification of configuration updates to all registered listeners
"""

from typing import Any, Dict, List, Callable, Optional
from datetime import datetime
from threading import Lock
import logging


class ChangeEvent:
    """Represents a configuration change event."""
    
    def __init__(self, key: str, old_value: Any, new_value: Any, user_id: Optional[str] = None):
        self.key = key
        self.old_value = old_value
        self.new_value = new_value
        self.user_id = user_id
        self.timestamp = datetime.utcnow()
        self.event_id = f"{key}_{self.timestamp.timestamp()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the change event to a dictionary."""
        return {
            'event_id': self.event_id,
            'key': self.key,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'user_id': self.user_id,
            'timestamp': self.timestamp
        }
    
    def __str__(self):
        return f"ChangeEvent(key={self.key}, old={self.old_value}, new={self.new_value})"


class ChangeListener:
    """Represents a registered change listener."""
    
    def __init__(self, listener_id: str, callback: Callable[[ChangeEvent], None], 
                 filter_keys: Optional[List[str]] = None, priority: int = 0):
        self.listener_id = listener_id
        self.callback = callback
        self.filter_keys = filter_keys or []
        self.priority = priority
        self.is_active = True
        self.error_count = 0
        self.last_error = None
    
    def should_notify(self, change_event: ChangeEvent) -> bool:
        """Check if this listener should be notified of the change."""
        if not self.is_active:
            return False
        
        if not self.filter_keys:
            return True
        
        return change_event.key in self.filter_keys
    
    def notify(self, change_event: ChangeEvent) -> bool:
        """Notify this listener of a change event."""
        try:
            self.callback(change_event)
            return True
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logging.error(f"Error in change listener {self.listener_id}: {e}")
            
            # Disable listener after too many errors
            if self.error_count >= 5:
                self.is_active = False
                logging.warning(f"Disabled change listener {self.listener_id} due to repeated errors")
            
            return False


class ChangeNotifier:
    """System for broadcasting configuration changes to registered listeners."""
    
    def __init__(self):
        self.listeners: Dict[str, ChangeListener] = {}
        self.change_history: List[ChangeEvent] = []
        self.max_history_size = 1000
        self._lock = Lock()
        self.logger = logging.getLogger(__name__)
    
    def register_listener(self, listener_id: str, callback: Callable[[ChangeEvent], None],
                         filter_keys: Optional[List[str]] = None, priority: int = 0) -> None:
        """Register a new change listener."""
        with self._lock:
            listener = ChangeListener(listener_id, callback, filter_keys, priority)
            self.listeners[listener_id] = listener
            self.logger.info(f"Registered change listener: {listener_id}")
    
    def unregister_listener(self, listener_id: str) -> bool:
        """Unregister a change listener."""
        with self._lock:
            if listener_id in self.listeners:
                del self.listeners[listener_id]
                self.logger.info(f"Unregistered change listener: {listener_id}")
                return True
            return False
    
    def broadcast_change(self, key: str, old_value: Any, new_value: Any, user_id: Optional[str] = None) -> Dict[str, bool]:
        """Broadcast a configuration change to all relevant listeners."""
        change_event = ChangeEvent(key, old_value, new_value, user_id)
        
        # Add to history
        with self._lock:
            self.change_history.append(change_event)
            if len(self.change_history) > self.max_history_size:
                self.change_history.pop(0)
        
        # Notify listeners
        notification_results = {}
        
        # Sort listeners by priority (higher priority first)
        sorted_listeners = sorted(
            self.listeners.items(),
            key=lambda x: x[1].priority,
            reverse=True
        )
        
        for listener_id, listener in sorted_listeners:
            if listener.should_notify(change_event):
                success = listener.notify(change_event)
                notification_results[listener_id] = success
        
        self.logger.info(f"Broadcasted change for key '{key}' to {len(notification_results)} listeners")
        return notification_results
    
    def get_active_listeners(self) -> List[str]:
        """Get list of active listener IDs."""
        with self._lock:
            return [lid for lid, listener in self.listeners.items() if listener.is_active]
    
    def get_listener_status(self, listener_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a specific listener."""
        with self._lock:
            if listener_id not in self.listeners:
                return None
            
            listener = self.listeners[listener_id]
            return {
                'listener_id': listener_id,
                'is_active': listener.is_active,
                'priority': listener.priority,
                'filter_keys': listener.filter_keys,
                'error_count': listener.error_count,
                'last_error': listener.last_error
            }
    
    def get_all_listener_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all listeners."""
        return {lid: self.get_listener_status(lid) for lid in self.listeners.keys()}
    
    def get_change_history(self, limit: Optional[int] = None, key_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get change history, optionally filtered and limited."""
        with self._lock:
            history = self.change_history.copy()
        
        # Filter by key if specified
        if key_filter:
            history = [event for event in history if event.key == key_filter]
        
        # Apply limit
        if limit:
            history = history[-limit:]
        
        return [event.to_dict() for event in history]
    
    def clear_change_history(self) -> int:
        """Clear the change history and return the number of events cleared."""
        with self._lock:
            count = len(self.change_history)
            self.change_history.clear()
            return count
    
    def disable_listener(self, listener_id: str) -> bool:
        """Manually disable a listener."""
        with self._lock:
            if listener_id in self.listeners:
                self.listeners[listener_id].is_active = False
                self.logger.info(f"Disabled change listener: {listener_id}")
                return True
            return False
    
    def enable_listener(self, listener_id: str) -> bool:
        """Re-enable a disabled listener."""
        with self._lock:
            if listener_id in self.listeners:
                self.listeners[listener_id].is_active = True
                self.listeners[listener_id].error_count = 0
                self.listeners[listener_id].last_error = None
                self.logger.info(f"Enabled change listener: {listener_id}")
                return True
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the change notifier."""
        with self._lock:
            total_listeners = len(self.listeners)
            active_listeners = sum(1 for listener in self.listeners.values() if listener.is_active)
            total_changes = len(self.change_history)
            
            return {
                'total_listeners': total_listeners,
                'active_listeners': active_listeners,
                'inactive_listeners': total_listeners - active_listeners,
                'total_changes_recorded': total_changes,
                'max_history_size': self.max_history_size
            }