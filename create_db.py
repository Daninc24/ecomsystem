#!/usr/bin/env python3
"""
Simple script to create database tables.
"""

from app import app, db

def create_tables():
    """Create all database tables."""
    with app.app_context():
        # Drop all tables first (if they exist)
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        print("Database tables created successfully!")

if __name__ == '__main__':
    create_tables()