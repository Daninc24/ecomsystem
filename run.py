#!/usr/bin/env python3
"""
Simple run script for the E-commerce Flask application.
This script will start the Flask development server.
"""

import os
import sys

def main():
    """Start the Flask application."""
    print("Starting E-commerce Flask Application...")
    print("=" * 40)
    
    # Check if database exists
    if not os.path.exists('ecommerce.db'):
        print("Database not found. Please run setup first:")
        print("python setup.py")
        sys.exit(1)
    
    # Import and run the app
    try:
        from app import app
        print("Server starting at: http://localhost:5000")
        print("Press Ctrl+C to stop the server")
        print("=" * 40)
        app.run(debug=True, host='0.0.0.0', port=5000)
    except ImportError as e:
        print(f"Error importing app: {e}")
        print("Please make sure all dependencies are installed:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()