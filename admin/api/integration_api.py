"""
Integration API
Provides endpoints for managing e-commerce system integration
"""

from flask import Blueprint, request, jsonify, session
from bson import ObjectId
from datetime import datetime
from .base_api import admin_api_required, handle_api_errors, success_response, error_response
from .middleware import rate_limit, cors_headers, security_headers, log_api_request
from ..database.collections import get_admin_db
from ..services.ecommerce_integration import EcommerceIntegrationService
from ..services.data_migration import DataMigrationService
from ..services.realtime_sync import RealtimeSyncService

# Create integration API blueprint
integration_bp = Blueprint('integration_api', __name__, url_prefix='/api/admin/integration')


@integration_bp.route('/status', methods=['GET'])
@admin_api_required
@rate_limit('default')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def get_integration_status():
    """Get current integration status between admin and e-commerce systems."""
    db = get_admin_db()
    integration_service = EcommerceIntegrationService(db)
    
    status = integration_service.get_integration_status()
    return success_response(status)


@integration_bp.route('/collections', methods=['GET'])
@admin_api_required
@rate_limit('default')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def get_collections_info():
    """Get information about existing and admin collections."""
    db = get_admin_db()
    integration_service = EcommerceIntegrationService(db)
    
    collections_info = {
        'existing_collections': integration_service.get_existing_collections(),
        'integration_points': integration_service.get_integration_points(),
        'last_updated': datetime.utcnow()
    }
    
    return success_response(collections_info)


@integration_bp.route('/sync/user/<user_id>', methods=['POST'])
@admin_api_required
@rate_limit('default')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def sync_user_data(user_id):
    """Sync specific user data with admin enhancements."""
    try:
        db = get_admin_db()
        integration_service = EcommerceIntegrationService(db)
        
        user_data = integration_service.sync_user_data(ObjectId(user_id))
        return success_response({
            'user_id': user_id,
            'sync_status': 'completed',
            'user_data': user_data
        })
        
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(f"Sync failed: {str(e)}", 500)


@integration_bp.route('/sync/product/<product_id>', methods=['POST'])
@admin_api_required
@rate_limit('default')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def sync_product_data(product_id):
    """Sync specific product data with admin enhancements."""
    try:
        db = get_admin_db()
        integration_service = EcommerceIntegrationService(db)
        
        product_data = integration_service.sync_product_data(ObjectId(product_id))
        return success_response({
            'product_id': product_id,
            'sync_status': 'completed',
            'product_data': product_data
        })
        
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(f"Sync failed: {str(e)}", 500)


@integration_bp.route('/sync/order/<order_id>', methods=['POST'])
@admin_api_required
@rate_limit('default')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def sync_order_data(order_id):
    """Sync specific order data with admin enhancements."""
    try:
        db = get_admin_db()
        integration_service = EcommerceIntegrationService(db)
        
        order_data = integration_service.sync_order_data(ObjectId(order_id))
        return success_response({
            'order_id': order_id,
            'sync_status': 'completed',
            'order_data': order_data
        })
        
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(f"Sync failed: {str(e)}", 500)


@integration_bp.route('/compatibility', methods=['POST'])
@admin_api_required
@rate_limit('auth')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def create_compatibility_layer():
    """Create compatibility layer for existing authentication."""
    db = get_admin_db()
    integration_service = EcommerceIntegrationService(db)
    
    compatibility_result = integration_service.create_compatibility_layer()
    return success_response(compatibility_result)


@integration_bp.route('/realtime-sync', methods=['POST'])
@admin_api_required
@rate_limit('auth')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def setup_realtime_sync():
    """Set up real-time synchronization between admin and frontend."""
    db = get_admin_db()
    integration_service = EcommerceIntegrationService(db)
    
    sync_config = integration_service.setup_real_time_sync()
    return success_response(sync_config)


@integration_bp.route('/cache/update', methods=['POST'])
@admin_api_required
@rate_limit('default')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def update_frontend_cache():
    """Update frontend cache with admin changes."""
    data = request.get_json()
    
    if not data or 'cache_type' not in data or 'data' not in data:
        return error_response("Missing required fields: cache_type, data", 400)
    
    db = get_admin_db()
    integration_service = EcommerceIntegrationService(db)
    
    success = integration_service.update_frontend_cache(
        data['cache_type'],
        data['data']
    )
    
    if success:
        return success_response({'cache_updated': True})
    else:
        return error_response("Failed to update cache", 500)


@integration_bp.route('/cache/invalidate', methods=['POST'])
@admin_api_required
@rate_limit('default')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def invalidate_frontend_cache():
    """Invalidate frontend cache entries."""
    data = request.get_json() or {}
    cache_types = data.get('cache_types')
    
    db = get_admin_db()
    integration_service = EcommerceIntegrationService(db)
    
    success = integration_service.invalidate_frontend_cache(cache_types)
    
    if success:
        return success_response({'cache_invalidated': True})
    else:
        return error_response("Failed to invalidate cache", 500)


# Migration endpoints
@integration_bp.route('/migration/status', methods=['GET'])
@admin_api_required
@rate_limit('default')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def get_migration_status():
    """Get status of data migrations."""
    db = get_admin_db()
    migration_service = DataMigrationService(db)
    
    status = migration_service.get_migration_status()
    return success_response(status)


@integration_bp.route('/migration/run', methods=['POST'])
@admin_api_required
@rate_limit('auth')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def run_data_migration():
    """Run data migration process."""
    data = request.get_json() or {}
    migration_type = data.get('migration_type', 'full')
    
    db = get_admin_db()
    migration_service = DataMigrationService(db)
    
    try:
        if migration_type == 'full':
            results = migration_service.run_full_migration()
        elif migration_type == 'users':
            results = migration_service.migrate_user_authentication()
        elif migration_type == 'content':
            results = migration_service.migrate_content_data()
        elif migration_type == 'products':
            results = migration_service.migrate_product_data()
        elif migration_type == 'orders':
            results = migration_service.migrate_order_data()
        else:
            return error_response(f"Unknown migration type: {migration_type}", 400)
        
        return success_response(results)
        
    except Exception as e:
        return error_response(f"Migration failed: {str(e)}", 500)


@integration_bp.route('/migration/rollback', methods=['POST'])
@admin_api_required
@rate_limit('auth')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def rollback_migration():
    """Rollback a specific migration."""
    data = request.get_json()
    
    if not data or 'migration_type' not in data:
        return error_response("Missing required field: migration_type", 400)
    
    db = get_admin_db()
    migration_service = DataMigrationService(db)
    
    try:
        results = migration_service.rollback_migration(data['migration_type'])
        return success_response(results)
        
    except Exception as e:
        return error_response(f"Rollback failed: {str(e)}", 500)


# Real-time sync endpoints
@integration_bp.route('/sync/status', methods=['GET'])
@admin_api_required
@rate_limit('default')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def get_sync_status():
    """Get real-time synchronization status."""
    db = get_admin_db()
    sync_service = RealtimeSyncService(db)
    
    status = sync_service.get_sync_status()
    return success_response(status)


@integration_bp.route('/sync/trigger', methods=['POST'])
@admin_api_required
@rate_limit('default')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def trigger_sync_event():
    """Trigger a synchronization event."""
    data = request.get_json()
    
    if not data or 'event_type' not in data or 'data' not in data:
        return error_response("Missing required fields: event_type, data", 400)
    
    db = get_admin_db()
    sync_service = RealtimeSyncService(db)
    
    user_id = ObjectId(session.get('user_id')) if session.get('user_id') else None
    
    success = sync_service.trigger_sync_event(
        data['event_type'],
        data['data'],
        user_id
    )
    
    if success:
        return success_response({'sync_triggered': True})
    else:
        return error_response("Failed to trigger sync event", 500)


@integration_bp.route('/sync/start', methods=['POST'])
@admin_api_required
@rate_limit('auth')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def start_sync_monitoring():
    """Start real-time sync monitoring."""
    db = get_admin_db()
    sync_service = RealtimeSyncService(db)
    
    success = sync_service.start_sync_monitoring()
    
    if success:
        return success_response({'sync_monitoring_started': True})
    else:
        return error_response("Sync monitoring already active", 400)


@integration_bp.route('/sync/stop', methods=['POST'])
@admin_api_required
@rate_limit('auth')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def stop_sync_monitoring():
    """Stop real-time sync monitoring."""
    db = get_admin_db()
    sync_service = RealtimeSyncService(db)
    
    success = sync_service.stop_sync_monitoring()
    
    if success:
        return success_response({'sync_monitoring_stopped': True})
    else:
        return error_response("Sync monitoring not active", 400)


@integration_bp.route('/sync/cache/cleanup', methods=['POST'])
@admin_api_required
@rate_limit('default')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def cleanup_expired_cache():
    """Clean up expired cache entries."""
    db = get_admin_db()
    sync_service = RealtimeSyncService(db)
    
    cleaned_count = sync_service.cleanup_expired_cache()
    
    return success_response({
        'expired_entries_cleaned': cleaned_count
    })


@integration_bp.route('/sync/cache/refresh', methods=['POST'])
@admin_api_required
@rate_limit('auth')
@cors_headers()
@security_headers()
@log_api_request()
@handle_api_errors
def force_cache_refresh():
    """Force refresh of cache entries."""
    data = request.get_json() or {}
    cache_types = data.get('cache_types')
    
    db = get_admin_db()
    sync_service = RealtimeSyncService(db)
    
    success = sync_service.force_cache_refresh(cache_types)
    
    if success:
        return success_response({'cache_refreshed': True})
    else:
        return error_response("Failed to refresh cache", 500)


# Integration health check
@integration_bp.route('/health', methods=['GET'])
@admin_api_required
@cors_headers()
@security_headers()
@handle_api_errors
def integration_health_check():
    """Check health of integration systems."""
    db = get_admin_db()
    
    health_status = {
        'integration_service': 'healthy',
        'migration_service': 'healthy',
        'sync_service': 'healthy',
        'database_connection': 'healthy',
        'timestamp': datetime.utcnow()
    }
    
    try:
        # Test integration service
        integration_service = EcommerceIntegrationService(db)
        integration_service.get_existing_collections()
        
        # Test migration service
        migration_service = DataMigrationService(db)
        migration_service.get_migration_status()
        
        # Test sync service
        sync_service = RealtimeSyncService(db)
        sync_service.get_sync_status()
        
        # Test database connection
        db.admin_settings.find_one()
        
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['error'] = str(e)
        return jsonify(health_status), 503
    
    return success_response(health_status)