#!/usr/bin/env python3
"""
Initialize SQLite Database
Creates all tables and populates with default data
"""

import os
import sys
from app_sqlite import create_app
from models_sqlite import db, create_default_settings
from admin.database.collections import setup_admin_database

def init_database():
    """Initialize the SQLite database"""
    print("🚀 Initializing SQLite Database...")
    
    # Create Flask app
    app = create_app('development')
    
    with app.app_context():
        print("📊 Creating database tables...")
        
        # Drop all tables (for clean start)
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        print("✅ Database tables created successfully")
        
        # Setup admin database
        print("🔧 Setting up admin system...")
        setup_admin_database()
        
        # Create default settings
        print("⚙️  Creating default settings...")
        create_default_settings()
        
        print("🎉 Database initialization complete!")
        print("\n📋 Database Summary:")
        print(f"   • Database file: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"   • Admin database: {app.config.get('ADMIN_DATABASE_URI', 'Same as main')}")
        print("   • Default admin user: admin@markethubpro.com / admin123")
        print("   • Sample products and categories created")
        
        return True

if __name__ == "__main__":
    try:
        success = init_database()
        if success:
            print("\n✅ Database initialization successful!")
            sys.exit(0)
        else:
            print("\n❌ Database initialization failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error during database initialization: {str(e)}")
        sys.exit(1)