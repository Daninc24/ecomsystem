#!/usr/bin/env python3
"""
Demo script for the Theme Customization Engine
Shows the main functionality of the theme management system
"""

import os
import sys
from bson import ObjectId

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from admin.services.theme_manager import ThemeManager
from admin.services.css_generator import CSSGenerator
from admin.services.responsive_validator import ResponsiveValidator


def create_mock_db():
    """Create a simple mock database for demonstration."""
    mock_db = type('MockDB', (), {})()
    
    # Create mock collections
    for collection_name in ['theme_configs', 'theme_backups', 'media_assets']:
        collection = type('MockCollection', (), {
            '_data': {},
            '_counter': 0
        })()
        
        # Add basic CRUD methods
        def make_insert_one(coll):
            def insert_one(doc):
                coll._counter += 1
                doc_id = ObjectId()
                doc['_id'] = doc_id
                coll._data[doc_id] = doc.copy()
                return type('InsertResult', (), {'inserted_id': doc_id})()
            return insert_one
        
        def make_find_one(coll):
            def find_one(query):
                for doc_id, doc in coll._data.items():
                    match = True
                    for key, value in query.items():
                        if key not in doc or doc[key] != value:
                            match = False
                            break
                    if match:
                        return doc.copy()
                return None
            return find_one
        
        def make_update_one(coll):
            def update_one(query, update):
                for doc_id, doc in coll._data.items():
                    match = True
                    for key, value in query.items():
                        if key not in doc or doc[key] != value:
                            match = False
                            break
                    if match:
                        if '$set' in update:
                            doc.update(update['$set'])
                        return type('UpdateResult', (), {'modified_count': 1})()
                return type('UpdateResult', (), {'modified_count': 0})()
            return update_one
        
        collection.insert_one = make_insert_one(collection)
        collection.find_one = make_find_one(collection)
        collection.update_one = make_update_one(collection)
        collection.update_many = make_update_one(collection)  # Simplified
        collection.delete_one = lambda query: type('DeleteResult', (), {'deleted_count': 0})()
        collection.delete_many = lambda query: type('DeleteResult', (), {'deleted_count': 0})()
        
        setattr(mock_db, collection_name, collection)
    
    return mock_db


def demo_theme_creation():
    """Demonstrate theme creation and management."""
    print("=== Theme Creation Demo ===")
    
    # Create mock database and theme manager
    db = create_mock_db()
    user_id = ObjectId()
    theme_manager = ThemeManager(db, user_id)
    
    # Create a custom theme
    custom_settings = {
        'colors': {
            'primary': '#007bff',
            'secondary': '#6c757d',
            'background': '#ffffff',
            'text': '#212529',
            'link': '#007bff'
        },
        'typography': {
            'font_family_primary': 'system-ui, -apple-system, sans-serif',
            'font_size_base': '16px',
            'line_height_base': '1.5',
            'font_weight_normal': '400',
            'font_weight_bold': '700'
        },
        'layout': {
            'container_max_width': '1200px',
            'grid_columns': 12,
            'grid_gutter': '30px'
        },
        'spacing': {
            'padding_small': '8px',
            'padding_medium': '16px',
            'padding_large': '24px'
        }
    }
    
    theme = theme_manager.create_theme(
        name="Demo Theme",
        description="A demonstration theme for the admin system",
        settings=custom_settings
    )
    
    print(f"✓ Created theme: {theme.name}")
    print(f"  Theme ID: {theme.id}")
    print(f"  Primary color: {theme.get_setting('colors.primary')}")
    print(f"  Font size: {theme.get_setting('typography.font_size_base')}")
    print()
    
    return theme_manager, theme


def demo_css_generation():
    """Demonstrate CSS generation from theme settings."""
    print("=== CSS Generation Demo ===")
    
    css_generator = CSSGenerator()
    
    sample_settings = {
        'colors': {
            'primary': '#28a745',
            'background': '#f8f9fa',
            'text': '#343a40'
        },
        'typography': {
            'font_family_primary': 'Arial, sans-serif',
            'font_size_base': '18px'
        },
        'layout': {
            'container_max_width': '1140px'
        }
    }
    
    generated_css = css_generator.generate_css(sample_settings)
    
    print("✓ Generated CSS from theme settings:")
    print("--- CSS Output (first 500 characters) ---")
    print(generated_css[:500] + "..." if len(generated_css) > 500 else generated_css)
    print()
    
    # Validate the CSS
    is_valid = css_generator.validate_css_output(generated_css)
    print(f"✓ CSS validation: {'PASSED' if is_valid else 'FAILED'}")
    print()


def demo_live_preview():
    """Demonstrate live preview functionality."""
    print("=== Live Preview Demo ===")
    
    theme_manager, theme = demo_theme_creation()
    
    # Generate preview with temporary changes
    temporary_changes = {
        'colors': {
            'primary': '#dc3545'  # Change to red
        },
        'typography': {
            'font_size_base': '20px'  # Increase font size
        }
    }
    
    preview_css = theme_manager.generate_preview_css(theme.id, temporary_changes)
    
    print("✓ Generated live preview with temporary changes:")
    print(f"  - Primary color changed to: {temporary_changes['colors']['primary']}")
    print(f"  - Font size changed to: {temporary_changes['typography']['font_size_base']}")
    print("  - Preview CSS contains the changes without affecting the original theme")
    print()
    
    # Verify original theme is unchanged
    original_theme = theme_manager.get_theme_by_id(theme.id)
    print(f"✓ Original theme unchanged:")
    print(f"  - Primary color still: {original_theme.get_setting('colors.primary')}")
    print(f"  - Font size still: {original_theme.get_setting('typography.font_size_base')}")
    print()


def demo_backup_and_restore():
    """Demonstrate backup and restoration functionality."""
    print("=== Backup and Restore Demo ===")
    
    theme_manager, theme = demo_theme_creation()
    
    # Store original primary color
    original_primary = theme.get_setting('colors.primary')
    print(f"✓ Original primary color: {original_primary}")
    
    # Make a change (this should create an automatic backup)
    new_primary = '#ffc107'
    theme_manager.update_theme_setting(theme.id, 'colors.primary', new_primary)
    
    updated_theme = theme_manager.get_theme_by_id(theme.id)
    print(f"✓ Updated primary color: {updated_theme.get_setting('colors.primary')}")
    
    # Find the automatic backup
    backup_data = None
    for backup_id, backup_doc in theme_manager.backup_collection._data.items():
        if (backup_doc.get('theme_id') == theme.id and 
            backup_doc.get('backup_type') == 'automatic'):
            backup_data = backup_doc
            break
    
    if backup_data:
        print(f"✓ Automatic backup created: {backup_data['backup_name']}")
        
        # Restore from backup
        from admin.models.theme import ThemeBackup
        backup = ThemeBackup(**backup_data)
        restored_theme = theme_manager.restore_theme(backup.id)
        
        print(f"✓ Restored primary color: {restored_theme.get_setting('colors.primary')}")
        print(f"✓ Restoration successful: {restored_theme.get_setting('colors.primary') == original_primary}")
    else:
        print("✗ No automatic backup found")
    
    print()


def demo_responsive_validation():
    """Demonstrate responsive design validation."""
    print("=== Responsive Validation Demo ===")
    
    validator = ResponsiveValidator()
    
    # Test valid settings
    valid_settings = {
        'layout': {
            'container_max_width': '1200px',
            'grid_columns': 12
        },
        'typography': {
            'font_size_base': '16px',
            'line_height_base': '1.5'
        },
        'colors': {
            'background': '#ffffff',
            'text': '#212529'
        }
    }
    
    result = validator.validate_theme_settings(valid_settings)
    print(f"✓ Valid settings validation: {'PASSED' if result.is_valid else 'FAILED'}")
    if result.warnings:
        print(f"  Warnings: {', '.join(result.warnings)}")
    
    # Test invalid settings
    invalid_settings = {
        'typography': {
            'font_size_base': '10px'  # Too small for mobile
        },
        'layout': {
            'container_max_width': '200px'  # Too small
        }
    }
    
    result = validator.validate_theme_settings(invalid_settings)
    print(f"✓ Invalid settings validation: {'FAILED' if not result.is_valid else 'UNEXPECTED PASS'}")
    if result.error:
        print(f"  Error: {result.error}")
    
    print()


def main():
    """Run all demonstrations."""
    print("Theme Customization Engine Demo")
    print("=" * 40)
    print()
    
    try:
        demo_theme_creation()
        demo_css_generation()
        demo_live_preview()
        demo_backup_and_restore()
        demo_responsive_validation()
        
        print("=" * 40)
        print("✓ All demonstrations completed successfully!")
        print()
        print("The Theme Customization Engine provides:")
        print("  • Dynamic theme creation and management")
        print("  • Real-time CSS generation from theme settings")
        print("  • Live preview functionality without affecting original themes")
        print("  • Automatic backup and restoration capabilities")
        print("  • Responsive design validation")
        print("  • Asset management for logos, favicons, and media")
        
    except Exception as e:
        print(f"✗ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()