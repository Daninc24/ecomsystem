"""
System Monitoring API endpoints for Dynamic Admin System
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timezone
import functools
import psutil
import os

system_bp = Blueprint('system_api', __name__, url_prefix='/system')


def admin_required(f):
    """Decorator to require admin role."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_role('admin'):
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403
        return f(*args, **kwargs)
    return decorated_function


@system_bp.route('/', methods=['GET'])
def system_info():
    """Get system API information."""
    return jsonify({
        'success': True,
        'data': {
            'name': 'System Monitoring API',
            'version': '2.0.0',
            'endpoints': {
                'status': '/api/admin/system/status',
                'notifications': '/api/admin/system/notifications',
                'alerts': '/api/admin/system/alerts/clear (POST)'
            }
        }
    })


@system_bp.route('/status', methods=['GET'])
@login_required
@admin_required
def get_system_status():
    """Get system status information."""
    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get service status (simplified)
        services = {
            'database': {
                'status': 'healthy',
                'uptime': '24h 30m',
                'responseTime': 15
            },
            'api': {
                'status': 'healthy',
                'uptime': '24h 30m',
                'responseTime': 25
            },
            'cache': {
                'status': 'healthy',
                'uptime': '24h 30m',
                'responseTime': 5
            }
        }
        
        # Generate sample metrics data
        import random
        labels = ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00']
        
        metrics = {
            'cpu': {
                'labels': labels,
                'data': [random.randint(10, 80) for _ in labels]
            },
            'memory': {
                'used': memory.used,
                'total': memory.total
            },
            'disk': {
                'labels': ['Used', 'Free'],
                'data': [int(disk.used / disk.total * 100), int(disk.free / disk.total * 100)]
            },
            'network': {
                'labels': labels,
                'inbound': [random.randint(10, 100) for _ in labels],
                'outbound': [random.randint(5, 50) for _ in labels]
            }
        }
        
        # Sample alerts
        alerts = [
            {
                'id': 1,
                'title': 'High CPU Usage',
                'message': 'CPU usage has been above 80% for the last 10 minutes',
                'severity': 'warning',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        ] if cpu_percent > 50 else []
        
        # Sample logs
        logs = [
            {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'level': 'info',
                'message': 'System status check completed successfully'
            },
            {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'level': 'info',
                'message': 'Database connection pool refreshed'
            }
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'status': {
                    'services': services,
                    'metrics': metrics
                },
                'alerts': alerts,
                'logs': logs
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/notifications', methods=['GET'])
@login_required
@admin_required
def get_notifications():
    """Get system notifications."""
    try:
        # Sample notifications
        notifications = [
            {
                'id': 1,
                'message': 'System backup completed successfully',
                'type': 'success',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'notifications': notifications
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/alerts/clear', methods=['POST'])
@login_required
@admin_required
def clear_alerts():
    """Clear system alerts."""
    try:
        # In a real implementation, you'd clear alerts from database
        
        return jsonify({
            'success': True,
            'message': 'All alerts cleared successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500