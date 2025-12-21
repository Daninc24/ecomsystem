#!/usr/bin/env python3
"""
MarketHub Pro - Startup Script
Ensures the correct app is running on the correct port
"""

import os
import sys
import subprocess

def main():
    """Start the MarketHub Pro application"""
    print("🚀 Starting MarketHub Pro...")
    print("📍 Using MongoDB version with enhanced features")
    print("🌐 Server will be available at: http://127.0.0.1:5002")
    print("=" * 50)
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Virtual environment not detected")
        print("💡 Recommendation: Activate virtual environment with 'source venv/bin/activate'")
        print()
    
    # Check if required files exist
    required_files = [
        'app_mongo.py',
        'config_mongo.py',
        'simple_mongo_mock.py',
        'static/css/aliexpress-style.css',
        'static/css/responsive-fixes.css',
        'templates/base_enhanced.html'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        print("\n🔧 Please ensure all files are present before starting the application.")
        return 1
    
    print("✅ All required files found")
    print("🔄 Starting application...")
    print()
    
    try:
        # Start the MongoDB version of the app
        subprocess.run([sys.executable, 'app_mongo.py'], check=True)
    except KeyboardInterrupt:
        print("\n\n🛑 Application stopped by user")
        print("👋 Thank you for using MarketHub Pro!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error starting application: {e}")
        return 1
    except FileNotFoundError:
        print("\n❌ Python interpreter not found")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())