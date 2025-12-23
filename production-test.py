#!/usr/bin/env python3
"""
Production Readiness Test Script
Tests all critical components before deployment
"""

import os
import sys
import requests
import json
from datetime import datetime

def print_status(message, status="INFO"):
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m", 
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "RESET": "\033[0m"
    }
    
    icons = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️", 
        "ERROR": "❌"
    }
    
    print(f"{colors[status]}{icons[status]} {message}{colors['RESET']}")

def test_environment_variables():
    """Test that all required environment variables are set"""
    print_status("Testing Environment Variables", "INFO")
    
    required_vars = [
        'SECRET_KEY',
        'MONGO_URI', 
        'STRIPE_SECRET_KEY',
        'PAYPAL_CLIENT_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print_status(f"Missing environment variables: {', '.join(missing_vars)}", "ERROR")
        return False
    else:
        print_status("All required environment variables are set", "SUCCESS")
        return True

def test_application_startup():
    """Test that the application starts successfully"""
    print_status("Testing Application Startup", "INFO")
    
    try:
        # Import the app to test startup
        from app_mongo import app
        with app.app_context():
            print_status("Application imports successfully", "SUCCESS")
            return True
    except Exception as e:
        print_status(f"Application startup failed: {str(e)}", "ERROR")
        return False

def test_database_connection():
    """Test database connectivity"""
    print_status("Testing Database Connection", "INFO")
    
    try:
        from app_mongo import app, mongo
        with app.app_context():
            # Test database connection
            mongo.db.users.find_one()
            print_status("Database connection successful", "SUCCESS")
            return True
    except Exception as e:
        print_status(f"Database connection failed: {str(e)}", "ERROR")
        return False

def test_security_configuration():
    """Test security configuration"""
    print_status("Testing Security Configuration", "INFO")
    
    issues = []
    
    # Check SECRET_KEY strength
    secret_key = os.environ.get('SECRET_KEY', '')
    if len(secret_key) < 32:
        issues.append("SECRET_KEY should be at least 32 characters")
    
    # Check for default passwords
    if 'admin123' in secret_key or 'change-this' in secret_key.lower():
        issues.append("SECRET_KEY appears to be a default value")
    
    # Check Flask config
    flask_config = os.environ.get('FLASK_CONFIG', 'development')
    if flask_config != 'production':
        issues.append("FLASK_CONFIG should be set to 'production'")
    
    if issues:
        for issue in issues:
            print_status(issue, "WARNING")
        return False
    else:
        print_status("Security configuration looks good", "SUCCESS")
        return True

def test_payment_configuration():
    """Test payment gateway configuration"""
    print_status("Testing Payment Configuration", "INFO")
    
    gateways = {
        'Stripe': ['STRIPE_PUBLISHABLE_KEY', 'STRIPE_SECRET_KEY'],
        'PayPal': ['PAYPAL_CLIENT_ID', 'PAYPAL_CLIENT_SECRET'],
        'M-Pesa': ['MPESA_CONSUMER_KEY', 'MPESA_CONSUMER_SECRET']
    }
    
    configured_gateways = []
    
    for gateway, vars_needed in gateways.items():
        if all(os.environ.get(var) for var in vars_needed):
            configured_gateways.append(gateway)
    
    if configured_gateways:
        print_status(f"Payment gateways configured: {', '.join(configured_gateways)}", "SUCCESS")
        return True
    else:
        print_status("No payment gateways configured", "WARNING")
        return False

def test_file_permissions():
    """Test file permissions and structure"""
    print_status("Testing File Structure", "INFO")
    
    required_files = [
        'app_mongo.py',
        'config_mongo.py', 
        'requirements.txt',
        'Dockerfile',
        'docker-compose.yml'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print_status(f"Missing files: {', '.join(missing_files)}", "ERROR")
        return False
    else:
        print_status("All required files present", "SUCCESS")
        return True

def test_docker_configuration():
    """Test Docker configuration"""
    print_status("Testing Docker Configuration", "INFO")
    
    try:
        # Check if docker-compose.yml is valid
        import yaml
        with open('docker-compose.yml', 'r') as f:
            docker_config = yaml.safe_load(f)
        
        # Check for required services
        required_services = ['web', 'mongo', 'nginx', 'redis']
        services = docker_config.get('services', {})
        
        missing_services = [svc for svc in required_services if svc not in services]
        
        if missing_services:
            print_status(f"Missing Docker services: {', '.join(missing_services)}", "ERROR")
            return False
        else:
            print_status("Docker configuration is valid", "SUCCESS")
            return True
            
    except Exception as e:
        print_status(f"Docker configuration error: {str(e)}", "ERROR")
        return False

def generate_production_report():
    """Generate a production readiness report"""
    print_status("Generating Production Readiness Report", "INFO")
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Application Startup", test_application_startup),
        ("Database Connection", test_database_connection),
        ("Security Configuration", test_security_configuration),
        ("Payment Configuration", test_payment_configuration),
        ("File Structure", test_file_permissions),
        ("Docker Configuration", test_docker_configuration)
    ]
    
    results = {}
    passed = 0
    total = len(tests)
    
    print("\n" + "="*60)
    print("🚀 PRODUCTION READINESS TEST RESULTS")
    print("="*60)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
            if result:
                passed += 1
        except Exception as e:
            print_status(f"{test_name} test failed with exception: {str(e)}", "ERROR")
            results[test_name] = False
    
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        color = "SUCCESS" if result else "ERROR"
        print_status(f"{test_name}: {status}", color)
    
    print(f"\n📈 Overall Score: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print_status("🎉 ALL TESTS PASSED - READY FOR PRODUCTION!", "SUCCESS")
        return True
    elif passed >= total * 0.8:
        print_status("⚠️ MOSTLY READY - Address warnings before deployment", "WARNING")
        return False
    else:
        print_status("❌ NOT READY - Critical issues must be fixed", "ERROR")
        return False

def main():
    """Main test runner"""
    print("🔍 MarketHub Pro - Production Readiness Test")
    print("=" * 50)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Set up environment for testing
    if not os.environ.get('FLASK_CONFIG'):
        os.environ['FLASK_CONFIG'] = 'production'
    
    # Run the tests
    ready = generate_production_report()
    
    print("\n" + "="*60)
    print("📋 NEXT STEPS")
    print("="*60)
    
    if ready:
        print_status("Your application is ready for production deployment!", "SUCCESS")
        print_status("Run: ./docker-deploy.sh", "INFO")
    else:
        print_status("Please address the issues above before deployment", "WARNING")
        print_status("Check PRODUCTION_SECURITY_CHECKLIST.md for details", "INFO")
    
    return 0 if ready else 1

if __name__ == "__main__":
    sys.exit(main())