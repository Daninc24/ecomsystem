#!/usr/bin/env python3
"""
Setup script for the E-commerce Flask application.
This script will install dependencies and set up the database.
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error during {description.lower()}: {e}")
        print(f"Command output: {e.stdout}")
        print(f"Error output: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("Error: Python 3.7 or higher is required")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def create_directories():
    """Create necessary directories."""
    directories = [
        'static/css',
        'static/js',
        'static/images',
        'templates/admin'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def main():
    """Main setup function."""
    print("=" * 50)
    print("E-COMMERCE FLASK APPLICATION SETUP")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create directories
    print("\nCreating directories...")
    create_directories()
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        print("\nTrying with pip3...")
        if not run_command("pip3 install -r requirements.txt", "Installing dependencies with pip3"):
            print("Failed to install dependencies. Please install manually:")
            print("pip install Flask Flask-SQLAlchemy Werkzeug")
            sys.exit(1)
    
    # Initialize database with sample data
    if not run_command("python init_data.py", "Initializing database with sample data"):
        print("\nTrying with python3...")
        if not run_command("python3 init_data.py", "Initializing database with python3"):
            print("Failed to initialize database. Please run manually:")
            print("python init_data.py")
            sys.exit(1)
    
    print("\n" + "=" * 50)
    print("SETUP COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print("\nTo start the application:")
    print("1. Run: python app.py")
    print("2. Open your browser to: http://localhost:5000")
    print("\nDefault login credentials:")
    print("Admin - Username: admin, Password: admin123")
    print("User - Username: user, Password: user123")
    print("\nEnjoy your E-commerce application!")

if __name__ == '__main__':
    main()