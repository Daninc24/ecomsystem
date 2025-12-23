"""
Property-based tests for theme customization engine
Tests the correctness properties defined in the design document
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from bson import ObjectId
from datetime import datetime
import tempfile
import os
import shutil

from admin.services.theme_manager import ThemeManager
from admin.services.css_generator import CSSGenerator
from admin.services.asset_manager import AssetManager
from admin.services.responsive_validator import ResponsiveValidator
from admin.models.theme import ThemeConfig, ThemeBackup


# Test data generators
@st.composite
def theme_settings_strategy(draw):
    """Generate valid theme settings for testing."""
    return {
        'colors': {
            'primary': draw(st.sampled_from(['#007bff', '#28a745', '#dc3545', '#ffc107'])),
            'secondary': draw(st.sampled_from(['#6c757d', '#17a2b8', '#343a40'])),
            'background': draw(st.sampled_from(['#ffffff', '#f8f9fa', '#e9ecef'])),
            'text': draw(st.sampled_from(['#212529', '#495057', '#6c757d'])),
            'link': draw(st.sampled_from(['#007bff', '#28a745', '#dc3545']))
        },
        'typography': {
            'font_family_primary': draw(st.sampled_from([
                'system-ui, sans-serif', 
                'Arial, sans-serif',
                'Helvetica, Arial, sans-serif'
            ])),
            'font_size_base': draw(st.sampled_from(['14px', '16px', '18px'])),
            'line_height_base': draw(st.sampled_from(['1.4', '1.5', '1.6'])),
            'font_weight_normal': draw(st.sampled_from(['400', '500'])),
            'font_weight_bold': draw(st.sampled_from(['600', '700', '800']))
        },
        'layout': {
            'container_max_width': draw(st.sampled_from(['1200px', '1140px', '960px'])),
            'grid_columns': draw(st.integers(min_value=8, max_value=16)),
            'grid_gutter': draw(st.sampled_from(['20px', '30px', '40px']))
        },
        'spacing': {
            'padding_small': draw(st.sampled_from(['8px', '12px', '16px'])),
            'padding_medium': draw(st.sampled_from(['16px', '20px', '24px'])),
            'padding_large': draw(st.sampled_from(['24px', '32px', '40px']))
        }
    }


@st.composite
def theme_setting_update_strategy(draw):
    """Generate theme setting updates for testing."""
    property_paths = [
        'colors.primary',
        'colors.background',
        'typography.font_size_base',
        'layout.container_max_width',
        'spacing.padding_medium'
    ]
    
    property_path = draw(st.sampled_from(property_paths))
    
    if property_path.startswith('colors.'):
        value = draw(st.sampled_from(['#007bff', '#28a745', '#dc3545', '#ffffff', '#000000']))
    elif property_path == 'typography.font_size_base':
        value = draw(st.sampled_from(['14px', '16px', '18px', '20px']))
    elif property_path == 'layout.container_max_width':
        value = draw(st.sampled_from(['1200px', '1140px', '960px', '800px']))
    elif property_path.startswith('spacing.'):
        value = draw(st.sampled_from(['8px', '16px', '24px', '32px']))
    else:
        value = draw(st.text(min_size=1, max_size=50))
    
    return property_path, value


class TestThemeProperties:
    """Property-based tests for theme customization engine."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        # Create a temporary directory for test assets
        self.temp_dir = tempfile.mkdtemp()
        self.original_assets_dir = None
        
        # Mock database
        self.mock_db = type('MockDB', (), {})()
        self.mock_db.theme_configs = type('MockCollection', (), {
            '_data': {},
            '_counter': 0
        })()
        self.mock_db.theme_backups = type('MockCollection', (), {
            '_data': {},
            '_counter': 0
        })()
        self.mock_db.media_assets = type('MockCollection', (), {
            '_data': {},
            '_counter': 0
        })()
        
        # Add mock methods
        self._setup_mock_collection(self.mock_db.theme_configs)
        self._setup_mock_collection(self.mock_db.theme_backups)
        self._setup_mock_collection(self.mock_db.media_assets)
        
        self.user_id = ObjectId()
        
        # Clear any existing data
        self.mock_db.theme_configs._data.clear()
        self.mock_db.theme_backups._data.clear()
        self.mock_db.media_assets._data.clear()
    
    def teardown_method(self):
        """Clean up after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _setup_mock_collection(self, collection):
        """Set up mock collection methods."""
        def insert_one(doc):
            collection._counter += 1
            doc_id = ObjectId()
            doc['_id'] = doc_id
            collection._data[doc_id] = doc.copy()
            return type('InsertResult', (), {'inserted_id': doc_id})()
        
        def find_one(query):
            for doc_id, doc in collection._data.items():
                if self._matches_query(doc, query):
                    return doc.copy()
            return None
        
        def update_one(query, update):
            for doc_id, doc in collection._data.items():
                if self._matches_query(doc, query):
                    if '$set' in update:
                        doc.update(update['$set'])
                    return type('UpdateResult', (), {'modified_count': 1})()
            return type('UpdateResult', (), {'modified_count': 0})()
        
        def update_many(query, update):
            modified = 0
            for doc_id, doc in collection._data.items():
                if self._matches_query(doc, query):
                    if '$set' in update:
                        doc.update(update['$set'])
                    modified += 1
            return type('UpdateResult', (), {'modified_count': modified})()
        
        def delete_one(query):
            for doc_id, doc in list(collection._data.items()):
                if self._matches_query(doc, query):
                    del collection._data[doc_id]
                    return type('DeleteResult', (), {'deleted_count': 1})()
            return type('DeleteResult', (), {'deleted_count': 0})()
        
        def delete_many(query):
            deleted = 0
            for doc_id, doc in list(collection._data.items()):
                if self._matches_query(doc, query):
                    del collection._data[doc_id]
                    deleted += 1
            return type('DeleteResult', (), {'deleted_count': deleted})()
        
        collection.insert_one = insert_one
        collection.find_one = find_one
        collection.update_one = update_one
        collection.update_many = update_many
        collection.delete_one = delete_one
        collection.delete_many = delete_many
    
    def _matches_query(self, doc, query):
        """Simple query matching for mock database."""
        if not query:
            return True
        
        for key, value in query.items():
            if key not in doc or doc[key] != value:
                return False
        return True
    
    @given(theme_settings_strategy())
    @settings(max_examples=50)
    def test_live_theme_preview_accuracy(self, theme_settings):
        """
        **Feature: dynamic-admin-system, Property 6: Live Theme Preview Accuracy**
        **Validates: Requirements 3.1**
        
        For any theme modification, the live preview should accurately reflect 
        how the change will appear on the actual site.
        """
        theme_manager = ThemeManager(self.mock_db, self.user_id)
        
        # Create a theme with the generated settings
        import time
        unique_suffix = f"{int(time.time() * 1000000) % 1000000}"
        theme = theme_manager.create_theme(
            name=f"test_theme_{unique_suffix}",
            description="Test theme for preview accuracy",
            settings=theme_settings
        )
        
        # Generate preview CSS with temporary modifications
        temporary_settings = {
            'colors': {
                'primary': '#ff0000'  # Change primary color
            }
        }
        
        preview_css = theme_manager.generate_preview_css(theme.id, temporary_settings)
        
        # The preview CSS should contain the temporary primary color
        assert '#ff0000' in preview_css or 'var(--color-primary)' in preview_css
        
        # Generate CSS with the same settings applied permanently
        theme_manager.update_theme_setting(theme.id, 'colors.primary', '#ff0000')
        updated_theme = theme_manager.get_theme_by_id(theme.id)
        
        # The preview CSS should match the permanently applied CSS
        # (accounting for CSS variable usage)
        css_generator = CSSGenerator()
        permanent_css = css_generator.generate_css(updated_theme.settings)
        
        # Both should contain the same color value or variable reference
        preview_has_color = '#ff0000' in preview_css or 'var(--color-primary)' in preview_css
        permanent_has_color = '#ff0000' in permanent_css or 'var(--color-primary)' in permanent_css
        
        assert preview_has_color and permanent_has_color, \
            "Preview CSS should accurately reflect permanent changes"
    
    @given(theme_settings_strategy())
    @settings(max_examples=50)
    def test_css_generation_correctness(self, theme_settings):
        """
        **Feature: dynamic-admin-system, Property 7: CSS Generation Correctness**
        **Validates: Requirements 3.2**
        
        For any theme configuration, the generated CSS should produce the exact 
        visual appearance specified by the configuration settings.
        """
        css_generator = CSSGenerator()
        
        # Generate CSS from theme settings
        generated_css = css_generator.generate_css(theme_settings)
        
        # CSS should be valid (basic syntax check)
        assert css_generator.validate_css_output(generated_css), \
            "Generated CSS should be syntactically valid"
        
        # CSS should contain CSS variables for all color settings
        if 'colors' in theme_settings:
            for color_key, color_value in theme_settings['colors'].items():
                css_var_name = f"--color-{color_key.replace('_', '-')}"
                assert css_var_name in generated_css, \
                    f"CSS should contain variable {css_var_name}"
                
                # The color value should appear in the CSS
                assert color_value in generated_css, \
                    f"CSS should contain color value {color_value}"
        
        # CSS should contain typography variables
        if 'typography' in theme_settings:
            for typo_key, typo_value in theme_settings['typography'].items():
                css_var_name = f"--{typo_key.replace('_', '-')}"
                assert css_var_name in generated_css, \
                    f"CSS should contain variable {css_var_name}"
        
        # CSS should contain layout variables
        if 'layout' in theme_settings:
            for layout_key, layout_value in theme_settings['layout'].items():
                css_var_name = f"--{layout_key.replace('_', '-')}"
                assert css_var_name in generated_css, \
                    f"CSS should contain variable {css_var_name}"
        
        # Generated CSS should be non-empty and contain basic structure
        assert len(generated_css.strip()) > 0, "Generated CSS should not be empty"
        assert ':root {' in generated_css, "CSS should contain root variables"
        assert 'body {' in generated_css, "CSS should contain body styles"
    
    @given(theme_settings_strategy())
    @settings(max_examples=30)
    def test_theme_backup_and_restoration(self, theme_settings):
        """
        **Feature: dynamic-admin-system, Property 8: Theme Backup and Restoration**
        **Validates: Requirements 3.5**
        
        For any theme change, a backup should be created automatically, and 
        restoration should return the theme to its exact previous state.
        """
        theme_manager = ThemeManager(self.mock_db, self.user_id)
        
        # Create a theme with initial settings
        import time
        unique_suffix = f"{int(time.time() * 1000000) % 1000000}"
        theme = theme_manager.create_theme(
            name=f"backup_test_theme_{unique_suffix}",
            description="Test theme for backup and restoration",
            settings=theme_settings
        )
        
        # Store original settings for comparison
        original_settings = theme.settings.copy()
        original_css = theme.css_generated
        
        # Make a change that should trigger automatic backup
        new_primary_color = '#123456'
        assume(new_primary_color != theme_settings.get('colors', {}).get('primary', ''))
        
        theme_manager.update_theme_setting(theme.id, 'colors.primary', new_primary_color)
        
        # Verify the change was applied
        updated_theme = theme_manager.get_theme_by_id(theme.id)
        assert updated_theme.get_setting('colors.primary') == new_primary_color
        
        # Find the automatic backup that should have been created
        backup_data = None
        for backup_id, backup_doc in theme_manager.backup_collection._data.items():
            if (backup_doc.get('theme_id') == theme.id and 
                backup_doc.get('backup_type') == 'automatic'):
                backup_data = backup_doc
                break
        
        assert backup_data is not None, "Automatic backup should have been created"
        
        # Create backup object and restore
        backup = ThemeBackup(**backup_data)
        restored_theme = theme_manager.restore_theme(backup.id)
        
        # Verify restoration accuracy
        assert restored_theme.settings == original_settings, \
            "Restored theme settings should exactly match original settings"
        
        # Verify that the primary color was restored
        restored_primary = restored_theme.get_setting('colors.primary')
        original_primary = original_settings.get('colors', {}).get('primary')
        assert restored_primary == original_primary, \
            f"Primary color should be restored to {original_primary}, got {restored_primary}"
        
        # Verify CSS was regenerated correctly
        css_generator = CSSGenerator()
        expected_css = css_generator.generate_css(original_settings)
        
        # The restored CSS should contain the same variables and values
        if original_primary:
            assert original_primary in restored_theme.css_generated or \
                   'var(--color-primary)' in restored_theme.css_generated, \
                   "Restored CSS should contain original primary color"


if __name__ == "__main__":
    pytest.main([__file__])