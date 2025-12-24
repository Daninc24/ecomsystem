"""
Integration Setup Script
Initializes the integration between admin system and existing e-commerce system
"""

from datetime import datetime
from typing import Dict, Any
from .database.collections import get_admin_db, setup_admin_database
from .services.ecommerce_integration import EcommerceIntegrationService
from .services.data_migration import DataMigrationService
from .services.realtime_sync import RealtimeSyncService


def initialize_integration() -> Dict[str, Any]:
    """Initialize complete integration between admin and e-commerce systems."""
    
    print("🚀 Starting admin system integration...")
    
    results = {
        'started_at': datetime.utcnow(),
        'database_setup': None,
        'compatibility_layer': None,
        'data_migration': None,
        'realtime_sync': None,
        'integration_status': None,
        'completed_at': None,
        'success': False,
        'errors': []
    }
    
    try:
        # Step 1: Set up admin database collections
        print("📊 Setting up admin database collections...")
        db = get_admin_db()
        setup_admin_database(db)
        results['database_setup'] = {'status': 'completed', 'collections_created': True}
        print("✅ Admin database setup completed")
        
        # Step 2: Create compatibility layer
        print("🔗 Creating compatibility layer...")
        integration_service = EcommerceIntegrationService(db)
        compatibility_result = integration_service.create_compatibility_layer()
        results['compatibility_layer'] = compatibility_result
        print(f"✅ Compatibility layer created: {len(compatibility_result['created_collections'])} new collections")
        
        # Step 3: Run data migration
        print("📦 Running data migration...")
        migration_service = DataMigrationService(db)
        migration_result = migration_service.run_full_migration()
        results['data_migration'] = migration_result
        print("✅ Data migration completed")
        
        # Step 4: Set up real-time synchronization
        print("⚡ Setting up real-time synchronization...")
        sync_config = integration_service.setup_real_time_sync()
        results['realtime_sync'] = sync_config
        print("✅ Real-time sync configured")
        
        # Step 5: Start sync monitoring
        print("🔄 Starting sync monitoring...")
        sync_service = RealtimeSyncService(db)
        sync_service.start_sync_monitoring()
        print("✅ Sync monitoring started")
        
        # Step 6: Get final integration status
        print("📋 Getting integration status...")
        integration_status = integration_service.get_integration_status()
        results['integration_status'] = integration_status
        print("✅ Integration status retrieved")
        
        results['completed_at'] = datetime.utcnow()
        results['success'] = True
        
        print("🎉 Admin system integration completed successfully!")
        
        # Print summary
        print("\n📊 Integration Summary:")
        print(f"   • Database collections: {len(integration_status['admin_collections'])} admin collections")
        print(f"   • E-commerce collections: {len(integration_status['ecommerce_collections'])} existing collections")
        
        if results['data_migration']:
            migration = results['data_migration']
            if migration.get('user_migration'):
                print(f"   • Users migrated: {migration['user_migration'].get('users_updated', 0)}")
            if migration.get('product_migration'):
                print(f"   • Products migrated: {migration['product_migration'].get('products_updated', 0)}")
            if migration.get('content_migration'):
                print(f"   • Content elements: {migration['content_migration'].get('content_elements_created', 0)}")
        
        print(f"   • Real-time sync: {'Active' if results['realtime_sync']['sync_enabled'] else 'Inactive'}")
        print(f"   • Integration completed in: {(results['completed_at'] - results['started_at']).total_seconds():.2f} seconds")
        
        return results
        
    except Exception as e:
        error_msg = f"Integration failed: {str(e)}"
        print(f"❌ {error_msg}")
        results['errors'].append(error_msg)
        results['completed_at'] = datetime.utcnow()
        results['success'] = False
        return results


def verify_integration() -> Dict[str, Any]:
    """Verify that integration is working correctly."""
    
    print("🔍 Verifying admin system integration...")
    
    verification_results = {
        'started_at': datetime.utcnow(),
        'database_connectivity': None,
        'admin_collections': None,
        'ecommerce_collections': None,
        'data_integrity': None,
        'sync_functionality': None,
        'api_endpoints': None,
        'overall_status': 'unknown',
        'completed_at': None,
        'errors': []
    }
    
    try:
        db = get_admin_db()
        
        # Test 1: Database connectivity
        print("🔌 Testing database connectivity...")
        try:
            db.admin_settings.find_one()
            verification_results['database_connectivity'] = {'status': 'pass', 'message': 'Database accessible'}
            print("✅ Database connectivity: PASS")
        except Exception as e:
            verification_results['database_connectivity'] = {'status': 'fail', 'message': str(e)}
            print(f"❌ Database connectivity: FAIL - {str(e)}")
        
        # Test 2: Admin collections
        print("📊 Testing admin collections...")
        try:
            admin_collections = [
                'admin_settings', 'content_versions', 'theme_configs',
                'activity_logs', 'system_alerts', 'analytics_metrics'
            ]
            
            collection_status = {}
            for collection_name in admin_collections:
                try:
                    count = db[collection_name].count_documents({})
                    collection_status[collection_name] = {'exists': True, 'count': count}
                except Exception as e:
                    collection_status[collection_name] = {'exists': False, 'error': str(e)}
            
            verification_results['admin_collections'] = collection_status
            print(f"✅ Admin collections: {len([c for c in collection_status.values() if c.get('exists')])} of {len(admin_collections)} exist")
        
        except Exception as e:
            verification_results['admin_collections'] = {'status': 'fail', 'message': str(e)}
            print(f"❌ Admin collections test: FAIL - {str(e)}")
        
        # Test 3: E-commerce collections
        print("🛒 Testing e-commerce collections...")
        try:
            ecommerce_collections = ['users', 'products', 'orders', 'vendors']
            
            ecommerce_status = {}
            for collection_name in ecommerce_collections:
                try:
                    count = db[collection_name].count_documents({})
                    ecommerce_status[collection_name] = {'exists': True, 'count': count}
                except Exception as e:
                    ecommerce_status[collection_name] = {'exists': False, 'error': str(e)}
            
            verification_results['ecommerce_collections'] = ecommerce_status
            print(f"✅ E-commerce collections: {len([c for c in ecommerce_status.values() if c.get('exists')])} of {len(ecommerce_collections)} exist")
        
        except Exception as e:
            verification_results['ecommerce_collections'] = {'status': 'fail', 'message': str(e)}
            print(f"❌ E-commerce collections test: FAIL - {str(e)}")
        
        # Test 4: Data integrity
        print("🔍 Testing data integrity...")
        try:
            integrity_checks = {}
            
            # Check if users have admin fields
            users_with_admin_fields = db.users.count_documents({'admin_metadata': {'$exists': True}})
            total_users = db.users.count_documents({})
            integrity_checks['users_migrated'] = {
                'migrated': users_with_admin_fields,
                'total': total_users,
                'percentage': (users_with_admin_fields / total_users * 100) if total_users > 0 else 0
            }
            
            # Check if products have admin fields
            products_with_admin_fields = db.products.count_documents({'admin_metadata': {'$exists': True}})
            total_products = db.products.count_documents({})
            integrity_checks['products_migrated'] = {
                'migrated': products_with_admin_fields,
                'total': total_products,
                'percentage': (products_with_admin_fields / total_products * 100) if total_products > 0 else 0
            }
            
            verification_results['data_integrity'] = integrity_checks
            print(f"✅ Data integrity: Users {integrity_checks['users_migrated']['percentage']:.1f}%, Products {integrity_checks['products_migrated']['percentage']:.1f}% migrated")
        
        except Exception as e:
            verification_results['data_integrity'] = {'status': 'fail', 'message': str(e)}
            print(f"❌ Data integrity test: FAIL - {str(e)}")
        
        # Test 5: Sync functionality
        print("⚡ Testing sync functionality...")
        try:
            sync_service = RealtimeSyncService(db)
            sync_status = sync_service.get_sync_status()
            verification_results['sync_functionality'] = sync_status
            print(f"✅ Sync functionality: {sync_status['pending_events']} pending, {sync_status['cache_entries']} cache entries")
        
        except Exception as e:
            verification_results['sync_functionality'] = {'status': 'fail', 'message': str(e)}
            print(f"❌ Sync functionality test: FAIL - {str(e)}")
        
        # Test 6: API endpoints (basic test)
        print("🌐 Testing API endpoints...")
        try:
            integration_service = EcommerceIntegrationService(db)
            integration_status = integration_service.get_integration_status()
            verification_results['api_endpoints'] = {'status': 'pass', 'integration_active': integration_status['integration_active']}
            print("✅ API endpoints: Basic functionality working")
        
        except Exception as e:
            verification_results['api_endpoints'] = {'status': 'fail', 'message': str(e)}
            print(f"❌ API endpoints test: FAIL - {str(e)}")
        
        # Determine overall status
        failed_tests = []
        for test_name, test_result in verification_results.items():
            if isinstance(test_result, dict) and test_result.get('status') == 'fail':
                failed_tests.append(test_name)
        
        if not failed_tests:
            verification_results['overall_status'] = 'pass'
            print("🎉 All integration tests passed!")
        else:
            verification_results['overall_status'] = 'partial'
            print(f"⚠️  Integration partially working. Failed tests: {', '.join(failed_tests)}")
        
        verification_results['completed_at'] = datetime.utcnow()
        
        return verification_results
        
    except Exception as e:
        error_msg = f"Verification failed: {str(e)}"
        print(f"❌ {error_msg}")
        verification_results['errors'].append(error_msg)
        verification_results['overall_status'] = 'fail'
        verification_results['completed_at'] = datetime.utcnow()
        return verification_results


def reset_integration() -> Dict[str, Any]:
    """Reset integration to clean state (for development/testing)."""
    
    print("🔄 Resetting admin system integration...")
    
    reset_results = {
        'started_at': datetime.utcnow(),
        'admin_collections_cleared': 0,
        'migration_logs_cleared': 0,
        'cache_cleared': 0,
        'sync_events_cleared': 0,
        'user_fields_removed': 0,
        'product_fields_removed': 0,
        'completed_at': None,
        'success': False,
        'errors': []
    }
    
    try:
        db = get_admin_db()
        
        # Clear admin collections
        admin_collections = [
            'admin_settings', 'content_versions', 'theme_configs',
            'activity_logs', 'system_alerts', 'analytics_metrics',
            'migration_logs', 'sync_events', 'frontend_cache'
        ]
        
        for collection_name in admin_collections:
            try:
                result = db[collection_name].delete_many({})
                reset_results['admin_collections_cleared'] += result.deleted_count
                print(f"🗑️  Cleared {result.deleted_count} documents from {collection_name}")
            except Exception as e:
                reset_results['errors'].append(f"Failed to clear {collection_name}: {str(e)}")
        
        # Remove admin fields from users
        try:
            result = db.users.update_many(
                {},
                {'$unset': {
                    'admin_settings': '',
                    'permissions': '',
                    'admin_metadata': '',
                    'session_settings': ''
                }}
            )
            reset_results['user_fields_removed'] = result.modified_count
            print(f"🗑️  Removed admin fields from {result.modified_count} users")
        except Exception as e:
            reset_results['errors'].append(f"Failed to remove user admin fields: {str(e)}")
        
        # Remove admin fields from products
        try:
            result = db.products.update_many(
                {},
                {'$unset': {
                    'admin_metadata': '',
                    'admin_notes': '',
                    'admin_flags': '',
                    'moderation_status': ''
                }}
            )
            reset_results['product_fields_removed'] = result.modified_count
            print(f"🗑️  Removed admin fields from {result.modified_count} products")
        except Exception as e:
            reset_results['errors'].append(f"Failed to remove product admin fields: {str(e)}")
        
        reset_results['completed_at'] = datetime.utcnow()
        reset_results['success'] = len(reset_results['errors']) == 0
        
        if reset_results['success']:
            print("✅ Integration reset completed successfully")
        else:
            print(f"⚠️  Integration reset completed with {len(reset_results['errors'])} errors")
        
        return reset_results
        
    except Exception as e:
        error_msg = f"Reset failed: {str(e)}"
        print(f"❌ {error_msg}")
        reset_results['errors'].append(error_msg)
        reset_results['completed_at'] = datetime.utcnow()
        reset_results['success'] = False
        return reset_results


if __name__ == '__main__':
    """Run integration setup when script is executed directly."""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'init':
            initialize_integration()
        elif command == 'verify':
            verify_integration()
        elif command == 'reset':
            reset_integration()
        else:
            print("Usage: python setup_integration.py [init|verify|reset]")
    else:
        # Default: run initialization
        initialize_integration()