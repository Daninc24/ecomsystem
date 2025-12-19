#!/usr/bin/env python3
"""
Route verification script for the E-commerce Flask application.
This script checks if all required routes are properly registered.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_routes():
    """Verify that all required routes are registered."""
    try:
        from app import app
        
        # Expected routes
        expected_routes = [
            '/',
            '/register',
            '/login',
            '/logout',
            '/products',
            '/product/<int:id>',
            '/contact',
            '/add_to_cart',
            '/cart',
            '/update_cart',
            '/remove_from_cart',
            '/checkout',
            '/place_order',
            '/orders',
            '/profile',
            '/admin',
            '/admin/products',
            '/admin/add_product',
            '/admin/edit_product/<int:id>',
            '/admin/delete_product/<int:id>',
            '/admin/orders',
            '/admin/update_order_status'
        ]
        
        # Get all registered routes
        registered_routes = []
        for rule in app.url_map.iter_rules():
            registered_routes.append(rule.rule)
        
        print("=" * 50)
        print("ROUTE VERIFICATION REPORT")
        print("=" * 50)
        
        print(f"\nTotal registered routes: {len(registered_routes)}")
        print(f"Expected routes: {len(expected_routes)}")
        
        # Check for missing routes
        missing_routes = []
        for route in expected_routes:
            if route not in registered_routes:
                missing_routes.append(route)
        
        if missing_routes:
            print(f"\n❌ MISSING ROUTES ({len(missing_routes)}):")
            for route in missing_routes:
                print(f"  - {route}")
        else:
            print("\n✅ ALL EXPECTED ROUTES ARE REGISTERED!")
        
        # Show all registered routes
        print(f"\n📋 ALL REGISTERED ROUTES:")
        for route in sorted(registered_routes):
            if route != '/static/<path:filename>':  # Skip static file route
                status = "✅" if route in expected_routes else "ℹ️"
                print(f"  {status} {route}")
        
        print("\n" + "=" * 50)
        
        if missing_routes:
            print("❌ VERIFICATION FAILED - Some routes are missing!")
            return False
        else:
            print("✅ VERIFICATION PASSED - All routes are properly registered!")
            return True
            
    except Exception as e:
        print(f"❌ ERROR during verification: {e}")
        return False

if __name__ == '__main__':
    success = verify_routes()
    sys.exit(0 if success else 1)