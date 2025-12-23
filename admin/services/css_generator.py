"""
CSS Generator Service
Generates dynamic CSS from theme configuration settings
"""

from typing import Dict, Any, List
import re


class CSSGenerator:
    """Generates CSS from theme configuration settings."""
    
    def __init__(self):
        self.css_template = self._load_css_template()
    
    def generate_css(self, theme_settings: Dict[str, Any]) -> str:
        """Generate complete CSS from theme settings."""
        css_parts = []
        
        # Generate CSS variables (custom properties)
        css_parts.append(self._generate_css_variables(theme_settings))
        
        # Generate base styles
        css_parts.append(self._generate_base_styles(theme_settings))
        
        # Generate layout styles
        css_parts.append(self._generate_layout_styles(theme_settings))
        
        # Generate component styles
        css_parts.append(self._generate_component_styles(theme_settings))
        
        # Generate responsive styles
        css_parts.append(self._generate_responsive_styles(theme_settings))
        
        # Combine all parts
        return '\n\n'.join(filter(None, css_parts))
    
    def _generate_css_variables(self, settings: Dict[str, Any]) -> str:
        """Generate CSS custom properties (variables) from theme settings."""
        variables = []
        variables.append(':root {')
        
        # Color variables
        if 'colors' in settings:
            for key, value in settings['colors'].items():
                css_key = key.replace('_', '-')
                variables.append(f'  --color-{css_key}: {value};')
        
        # Typography variables
        if 'typography' in settings:
            for key, value in settings['typography'].items():
                css_key = key.replace('_', '-')
                variables.append(f'  --{css_key}: {value};')
        
        # Layout variables
        if 'layout' in settings:
            for key, value in settings['layout'].items():
                css_key = key.replace('_', '-')
                variables.append(f'  --{css_key}: {value};')
        
        # Spacing variables
        if 'spacing' in settings:
            for key, value in settings['spacing'].items():
                css_key = key.replace('_', '-')
                variables.append(f'  --{css_key}: {value};')
        
        # Border variables
        if 'borders' in settings:
            for key, value in settings['borders'].items():
                css_key = key.replace('_', '-')
                variables.append(f'  --border-{css_key}: {value};')
        
        # Shadow variables
        if 'shadows' in settings:
            for key, value in settings['shadows'].items():
                css_key = key.replace('_', '-')
                variables.append(f'  --shadow-{css_key}: {value};')
        
        variables.append('}')
        return '\n'.join(variables)
    
    def _generate_base_styles(self, settings: Dict[str, Any]) -> str:
        """Generate base HTML element styles."""
        styles = []
        
        # Body styles
        body_styles = []
        if 'colors' in settings:
            if 'background' in settings['colors']:
                body_styles.append(f"background-color: var(--color-background);")
            if 'text' in settings['colors']:
                body_styles.append(f"color: var(--color-text);")
        
        if 'typography' in settings:
            if 'font_family_primary' in settings['typography']:
                body_styles.append(f"font-family: var(--font-family-primary);")
            if 'font_size_base' in settings['typography']:
                body_styles.append(f"font-size: var(--font-size-base);")
            if 'line_height_base' in settings['typography']:
                body_styles.append(f"line-height: var(--line-height-base);")
        
        if body_styles:
            styles.append('body {')
            styles.extend([f'  {style}' for style in body_styles])
            styles.append('}')
        
        # Heading styles
        heading_styles = []
        if 'typography' in settings:
            if 'font_family_secondary' in settings['typography']:
                heading_styles.append(f"font-family: var(--font-family-secondary);")
            if 'font_weight_bold' in settings['typography']:
                heading_styles.append(f"font-weight: var(--font-weight-bold);")
        
        if heading_styles:
            styles.append('h1, h2, h3, h4, h5, h6 {')
            styles.extend([f'  {style}' for style in heading_styles])
            styles.append('}')
        
        # Link styles
        if 'colors' in settings and 'link' in settings['colors']:
            styles.extend([
                'a {',
                '  color: var(--color-link);',
                '  text-decoration: none;',
                '}',
                'a:hover {',
                '  text-decoration: underline;',
                '}'
            ])
        
        return '\n'.join(styles)
    
    def _generate_layout_styles(self, settings: Dict[str, Any]) -> str:
        """Generate layout and grid styles."""
        styles = []
        
        # Container styles
        container_styles = []
        if 'layout' in settings:
            if 'container_max_width' in settings['layout']:
                container_styles.extend([
                    'max-width: var(--container-max-width);',
                    'margin: 0 auto;',
                    'padding: 0 var(--padding-medium);'
                ])
        
        if container_styles:
            styles.append('.container {')
            styles.extend([f'  {style}' for style in container_styles])
            styles.append('}')
        
        # Grid system
        if 'layout' in settings and 'grid_columns' in settings['layout']:
            grid_columns = int(settings['layout']['grid_columns'])
            
            styles.extend([
                '.row {',
                '  display: flex;',
                '  flex-wrap: wrap;',
                '  margin: 0 calc(var(--grid-gutter) / -2);',
                '}',
                '.col {',
                '  flex: 1;',
                '  padding: 0 calc(var(--grid-gutter) / 2);',
                '}'
            ])
            
            # Generate column classes
            for i in range(1, grid_columns + 1):
                width_percentage = (i / grid_columns) * 100
                styles.extend([
                    f'.col-{i} {{',
                    f'  flex: 0 0 {width_percentage:.4f}%;',
                    f'  max-width: {width_percentage:.4f}%;',
                    '  padding: 0 calc(var(--grid-gutter) / 2);',
                    '}'
                ])
        
        # Header styles
        if 'layout' in settings and 'header_height' in settings['layout']:
            styles.extend([
                'header, .header {',
                '  height: var(--header-height);',
                '  display: flex;',
                '  align-items: center;',
                '}'
            ])
        
        return '\n'.join(styles)
    
    def _generate_component_styles(self, settings: Dict[str, Any]) -> str:
        """Generate component-specific styles."""
        styles = []
        
        # Button styles
        button_styles = [
            'display: inline-block;',
            'padding: var(--padding-medium) var(--padding-large);',
            'border: var(--border-width-thin) solid transparent;',
            'border-radius: var(--border-radius-medium);',
            'font-family: inherit;',
            'font-size: var(--font-size-base);',
            'font-weight: var(--font-weight-normal);',
            'line-height: 1;',
            'text-align: center;',
            'text-decoration: none;',
            'cursor: pointer;',
            'transition: all 0.2s ease-in-out;'
        ]
        
        styles.append('.btn {')
        styles.extend([f'  {style}' for style in button_styles])
        styles.append('}')
        
        # Button variants
        if 'colors' in settings:
            button_variants = [
                ('primary', 'primary'),
                ('secondary', 'secondary'),
                ('success', 'success'),
                ('danger', 'danger'),
                ('warning', 'warning'),
                ('info', 'info')
            ]
            
            for variant, color_key in button_variants:
                if color_key in settings['colors']:
                    styles.extend([
                        f'.btn-{variant} {{',
                        f'  background-color: var(--color-{color_key});',
                        '  color: white;',
                        f'  border-color: var(--color-{color_key});',
                        '}',
                        f'.btn-{variant}:hover {{',
                        f'  background-color: var(--color-{color_key});',
                        '  opacity: 0.9;',
                        '}'
                    ])
        
        # Card styles
        card_styles = [
            'background-color: var(--color-background);',
            'border: var(--border-width-thin) solid var(--color-border);',
            'border-radius: var(--border-radius-medium);',
            'box-shadow: var(--shadow-small);',
            'overflow: hidden;'
        ]
        
        styles.append('.card {')
        styles.extend([f'  {style}' for style in card_styles])
        styles.append('}')
        
        styles.extend([
            '.card-header, .card-body, .card-footer {',
            '  padding: var(--padding-large);',
            '}',
            '.card-header {',
            '  background-color: var(--color-light);',
            '  border-bottom: var(--border-width-thin) solid var(--color-border);',
            '}',
            '.card-footer {',
            '  background-color: var(--color-light);',
            '  border-top: var(--border-width-thin) solid var(--color-border);',
            '}'
        ])
        
        # Form styles
        form_styles = [
            'display: block;',
            'width: 100%;',
            'padding: var(--padding-medium);',
            'font-size: var(--font-size-base);',
            'line-height: var(--line-height-base);',
            'color: var(--color-text);',
            'background-color: var(--color-background);',
            'border: var(--border-width-thin) solid var(--color-border);',
            'border-radius: var(--border-radius-small);',
            'transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;'
        ]
        
        styles.append('.form-control {')
        styles.extend([f'  {style}' for style in form_styles])
        styles.append('}')
        
        styles.extend([
            '.form-control:focus {',
            '  outline: 0;',
            '  border-color: var(--color-primary);',
            '  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);',
            '}'
        ])
        
        return '\n'.join(styles)
    
    def _generate_responsive_styles(self, settings: Dict[str, Any]) -> str:
        """Generate responsive media queries."""
        styles = []
        
        # Mobile styles (max-width: 768px)
        mobile_styles = []
        
        # Adjust container padding on mobile
        mobile_styles.extend([
            '.container {',
            '  padding: 0 var(--padding-small);',
            '}'
        ])
        
        # Stack grid columns on mobile
        if 'layout' in settings and 'grid_columns' in settings['layout']:
            grid_columns = int(settings['layout']['grid_columns'])
            for i in range(1, grid_columns + 1):
                mobile_styles.extend([
                    f'.col-{i} {{',
                    '  flex: 0 0 100%;',
                    '  max-width: 100%;',
                    '}'
                ])
        
        # Adjust typography on mobile
        if 'typography' in settings and 'font_size_base' in settings['typography']:
            mobile_styles.extend([
                'body {',
                '  font-size: calc(var(--font-size-base) * 0.9);',
                '}'
            ])
        
        if mobile_styles:
            styles.append('@media (max-width: 768px) {')
            styles.extend([f'  {style}' if not style.endswith('{') and not style.endswith('}') else style for style in mobile_styles])
            styles.append('}')
        
        # Tablet styles (min-width: 769px and max-width: 1024px)
        tablet_styles = []
        
        # Adjust grid for tablet
        if 'layout' in settings and 'grid_columns' in settings['layout']:
            grid_columns = int(settings['layout']['grid_columns'])
            # On tablet, make columns take up more space
            for i in range(1, grid_columns + 1):
                if i <= 6:  # First half of columns take full width on tablet
                    tablet_styles.extend([
                        f'.col-{i} {{',
                        '  flex: 0 0 50%;',
                        '  max-width: 50%;',
                        '}'
                    ])
        
        if tablet_styles:
            styles.append('@media (min-width: 769px) and (max-width: 1024px) {')
            styles.extend([f'  {style}' if not style.endswith('{') and not style.endswith('}') else style for style in tablet_styles])
            styles.append('}')
        
        return '\n'.join(styles)
    
    def _load_css_template(self) -> str:
        """Load base CSS template (placeholder for future template system)."""
        return """
/* Dynamic Theme CSS - Generated automatically */
/* Do not edit this file directly - changes will be overwritten */
"""
    
    def validate_css_output(self, css: str) -> bool:
        """Validate that generated CSS is syntactically correct."""
        # Basic CSS validation - check for balanced braces
        open_braces = css.count('{')
        close_braces = css.count('}')
        
        if open_braces != close_braces:
            return False
        
        # Check for basic CSS syntax patterns
        # This is a simplified validation - in production, you might use a proper CSS parser
        lines = css.split('\n')
        in_rule = False
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('/*'):
                continue
            
            if line.endswith('{'):
                in_rule = True
            elif line == '}':
                in_rule = False
            elif in_rule and ':' not in line and not line.endswith(';'):
                # Invalid property line
                return False
        
        return True
    
    def minify_css(self, css: str) -> str:
        """Minify CSS by removing unnecessary whitespace and comments."""
        # Remove comments
        css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
        
        # Remove extra whitespace
        css = re.sub(r'\s+', ' ', css)
        
        # Remove whitespace around braces and semicolons
        css = re.sub(r'\s*{\s*', '{', css)
        css = re.sub(r'\s*}\s*', '}', css)
        css = re.sub(r'\s*;\s*', ';', css)
        css = re.sub(r'\s*:\s*', ':', css)
        
        return css.strip()