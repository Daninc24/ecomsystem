#!/usr/bin/env python3
"""
Run the E-commerce Application with SQLite
"""

import os
import sys
from app_sqlite import create_app

def main():
    """Main application entry point"""
    
    # Get configuration from environment
    config_name = os.environ.get('FLASK_CONFIG', 'development')
    
    # Create Flask application
    app = create_app(config_name)
    
    # Get host and port from environment or use defaults
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = config_name == 'development'
    
    print(f"🚀 Starting MarketHub Pro E-commerce System")
    print(f"📊 Configuration: {config_name}")
    print(f"🌐 Server: http://{host}:{port}")
    print(f"🔧 Debug mode: {debug}")
    print(f"💾 Database: SQLite")
    
    if debug:
        print("\n📝 Development Notes:")
        print("   • Admin dashboard: http://localhost:5000/admin")
        print("   • Default admin: admin@markethubpro.com / admin123")
        print("   • API endpoints: http://localhost:5000/api/admin/")
        print("   • Database will be created automatically on first run")
    
    # Run the application
    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Error starting application: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()