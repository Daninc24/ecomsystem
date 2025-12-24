"""
System Maintenance and Monitoring API endpoints
"""

from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime
from .base_api import admin_api_required, validate_json_request, handle_api_errors, success_response, error_response, get_current_user_id

system_bp = Blueprint('admin_system', __name__, url_prefix='/api/admin/system')


@system_bp.route('/health', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_system_health():
    """Get comprehensive system health status."""
    from ..services.system_monitor import SystemMonitor
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    system_monitor = SystemMonitor(db)
    
    health_status = system_monitor.get_system_health()
    
    return jsonify(success_response(health_status))


@system_bp.route('/performance', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_performance_metrics():
    """Get system performance metrics."""
    from ..services.system_monitor import SystemMonitor
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    system_monitor = SystemMonitor(db)
    
    period = request.args.get('period', 'hour')  # hour, day, week
    
    performance_data = system_monitor.get_performance_metrics(period)
    
    return jsonify(success_response(performance_data))


@system_bp.route('/logs', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_system_logs():
    """Get system logs with filtering."""
    from ..services.system_monitor import SystemMonitor
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    system_monitor = SystemMonitor(db)
    
    level = request.args.get('level')  # error, warning, info, debug
    component = request.args.get('component')
    limit = request.args.get('limit', 100, type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    logs = system_monitor.get_system_logs(level, component, limit, date_from, date_to)
    
    # Convert ObjectIds to strings
    for log in logs:
        log['_id'] = str(log['_id'])
    
    return jsonify(success_response(logs))


@system_bp.route('/backups', methods=['GET'])
@admin_api_required
@handle_api_errors
def list_backups():
    """List all system backups."""
    from ..services.backup_manager import BackupManager
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    backup_manager = BackupManager(db)
    
    backup_type = request.args.get('type')  # full, incremental, config
    limit = request.args.get('limit', 20, type=int)
    
    backups = backup_manager.list_backups(backup_type, limit)
    
    # Convert ObjectIds to strings
    for backup in backups:
        backup['_id'] = str(backup['_id'])
        if 'created_by' in backup:
            backup['created_by'] = str(backup['created_by'])
    
    return jsonify(success_response(backups))


@system_bp.route('/backups', methods=['POST'])
@admin_api_required
@validate_json_request(['type'])
@handle_api_errors
def create_backup():
    """Create a new system backup."""
    from ..services.backup_manager import BackupManager
    from ..database.collections import get_admin_db
    
    data = request.get_json()
    backup_type = data['type']
    description = data.get('description', '')
    user_id = get_current_user_id()
    
    db = get_admin_db()
    backup_manager = BackupManager(db)
    
    try:
        backup_id = backup_manager.create_backup(backup_type, description, user_id)
        
        return jsonify(success_response(
            {'id': str(backup_id)},
            f'{backup_type.title()} backup created successfully'
        )), 201
    
    except ValueError as e:
        return error_response(str(e), 'BACKUP_ERROR')


@system_bp.route('/backups/<backup_id>/restore', methods=['POST'])
@admin_api_required
@handle_api_errors
def restore_backup(backup_id):
    """Restore from a backup."""
    from ..services.backup_manager import BackupManager
    from ..database.collections import get_admin_db
    
    try:
        backup_obj_id = ObjectId(backup_id)
    except:
        return error_response('Invalid backup ID', 'INVALID_ID')
    
    user_id = get_current_user_id()
    
    db = get_admin_db()
    backup_manager = BackupManager(db)
    
    try:
        success = backup_manager.restore_backup(backup_obj_id, user_id)
        
        if success:
            return jsonify(success_response(message='Backup restored successfully'))
        else:
            return error_response('Failed to restore backup', 'RESTORE_ERROR')
    
    except ValueError as e:
        return error_response(str(e), 'RESTORE_ERROR')


@system_bp.route('/cache/status', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_cache_status():
    """Get cache system status and statistics."""
    from ..services.cache_manager import CacheManager
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    cache_manager = CacheManager(db)
    
    cache_status = cache_manager.get_cache_status()
    
    return jsonify(success_response(cache_status))


@system_bp.route('/cache/clear', methods=['POST'])
@admin_api_required
@handle_api_errors
def clear_cache():
    """Clear system cache."""
    from ..services.cache_manager import CacheManager
    from ..database.collections import get_admin_db
    
    data = request.get_json() or {}
    cache_type = data.get('type', 'all')  # all, content, configuration, user
    
    db = get_admin_db()
    cache_manager = CacheManager(db)
    
    cleared_count = cache_manager.clear_cache(cache_type)
    
    return jsonify(success_response(
        {'cleared_count': cleared_count},
        f'Cleared {cleared_count} cache entries'
    ))


@system_bp.route('/security/status', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_security_status():
    """Get security monitoring status."""
    from ..services.security_monitor import SecurityMonitor
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    security_monitor = SecurityMonitor(db)
    
    security_status = security_monitor.get_security_status()
    
    return jsonify(success_response(security_status))


@system_bp.route('/security/threats', methods=['GET'])
@admin_api_required
@handle_api_errors
def list_security_threats():
    """List detected security threats."""
    from ..services.security_monitor import SecurityMonitor
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    security_monitor = SecurityMonitor(db)
    
    severity = request.args.get('severity')  # low, medium, high, critical
    status = request.args.get('status')  # active, resolved, dismissed
    limit = request.args.get('limit', 50, type=int)
    
    threats = security_monitor.list_threats(severity, status, limit)
    
    # Convert ObjectIds to strings
    for threat in threats:
        threat['_id'] = str(threat['_id'])
    
    return jsonify(success_response(threats))


@system_bp.route('/security/login-attempts', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_login_attempts():
    """Get login attempt statistics."""
    from ..services.security_monitor import SecurityMonitor
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    security_monitor = SecurityMonitor(db)
    
    period = request.args.get('period', 'day')  # hour, day, week
    failed_only = request.args.get('failed_only', 'false').lower() == 'true'
    
    login_attempts = security_monitor.get_login_attempts(period, failed_only)
    
    return jsonify(success_response(login_attempts))


@system_bp.route('/configuration/rollback', methods=['GET'])
@admin_api_required
@handle_api_errors
def list_configuration_rollbacks():
    """List available configuration rollback points."""
    from ..services.configuration_rollback import ConfigurationRollback
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    rollback_manager = ConfigurationRollback(db)
    
    limit = request.args.get('limit', 20, type=int)
    
    rollback_points = rollback_manager.list_rollback_points(limit)
    
    # Convert ObjectIds to strings
    for point in rollback_points:
        point['_id'] = str(point['_id'])
        if 'created_by' in point:
            point['created_by'] = str(point['created_by'])
    
    return jsonify(success_response(rollback_points))


@system_bp.route('/configuration/rollback/<rollback_id>', methods=['POST'])
@admin_api_required
@handle_api_errors
def execute_configuration_rollback(rollback_id):
    """Execute a configuration rollback."""
    from ..services.configuration_rollback import ConfigurationRollback
    from ..database.collections import get_admin_db
    
    try:
        rollback_obj_id = ObjectId(rollback_id)
    except:
        return error_response('Invalid rollback ID', 'INVALID_ID')
    
    user_id = get_current_user_id()
    
    db = get_admin_db()
    rollback_manager = ConfigurationRollback(db)
    
    try:
        success = rollback_manager.execute_rollback(rollback_obj_id, user_id)
        
        if success:
            return jsonify(success_response(message='Configuration rollback completed'))
        else:
            return error_response('Failed to execute rollback', 'ROLLBACK_ERROR')
    
    except ValueError as e:
        return error_response(str(e), 'ROLLBACK_ERROR')


@system_bp.route('/maintenance/mode', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_maintenance_mode():
    """Get maintenance mode status."""
    from ..services.system_monitor import SystemMonitor
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    system_monitor = SystemMonitor(db)
    
    maintenance_status = system_monitor.get_maintenance_mode_status()
    
    return jsonify(success_response(maintenance_status))


@system_bp.route('/maintenance/mode', methods=['POST'])
@admin_api_required
@validate_json_request(['enabled'])
@handle_api_errors
def set_maintenance_mode():
    """Enable or disable maintenance mode."""
    from ..services.system_monitor import SystemMonitor
    from ..database.collections import get_admin_db
    
    data = request.get_json()
    enabled = data['enabled']
    message = data.get('message', 'System is under maintenance')
    user_id = get_current_user_id()
    
    db = get_admin_db()
    system_monitor = SystemMonitor(db)
    
    success = system_monitor.set_maintenance_mode(enabled, message, user_id)
    
    if success:
        status = 'enabled' if enabled else 'disabled'
        return jsonify(success_response(message=f'Maintenance mode {status}'))
    else:
        return error_response('Failed to update maintenance mode', 'UPDATE_ERROR')


@system_bp.route('/database/optimize', methods=['POST'])
@admin_api_required
@handle_api_errors
def optimize_database():
    """Optimize database performance."""
    from ..services.system_monitor import SystemMonitor
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    system_monitor = SystemMonitor(db)
    
    optimization_result = system_monitor.optimize_database()
    
    return jsonify(success_response(
        optimization_result,
        'Database optimization completed'
    ))


@system_bp.route('/cleanup', methods=['POST'])
@admin_api_required
@handle_api_errors
def system_cleanup():
    """Perform system cleanup tasks."""
    from ..services.system_monitor import SystemMonitor
    from ..database.collections import get_admin_db
    
    data = request.get_json() or {}
    cleanup_types = data.get('types', ['logs', 'cache', 'temp_files'])
    
    db = get_admin_db()
    system_monitor = SystemMonitor(db)
    
    cleanup_result = system_monitor.perform_cleanup(cleanup_types)
    
    return jsonify(success_response(
        cleanup_result,
        'System cleanup completed'
    ))


@system_bp.route('/updates/check', methods=['GET'])
@admin_api_required
@handle_api_errors
def check_for_updates():
    """Check for system updates."""
    from ..services.system_monitor import SystemMonitor
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    system_monitor = SystemMonitor(db)
    
    update_info = system_monitor.check_for_updates()
    
    return jsonify(success_response(update_info))


@system_bp.route('/disk-usage', methods=['GET'])
@admin_api_required
@handle_api_errors
def get_disk_usage():
    """Get disk usage statistics."""
    from ..services.system_monitor import SystemMonitor
    from ..database.collections import get_admin_db
    
    db = get_admin_db()
    system_monitor = SystemMonitor(db)
    
    disk_usage = system_monitor.get_disk_usage()
    
    return jsonify(success_response(disk_usage))