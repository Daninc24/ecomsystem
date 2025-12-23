"""
Responsive Validator Service
Ensures theme settings maintain mobile compatibility and responsive design
"""

from typing import Dict, Any, List, NamedTuple, Optional
import re


class ValidationResult(NamedTuple):
    """Result of a responsive design validation."""
    is_valid: bool
    error: str = ""
    warnings: List[str] = []


class ResponsiveValidator:
    """Validates theme settings for responsive design compliance."""
    
    def __init__(self):
        self.breakpoints = {
            'mobile': 768,
            'tablet': 1024,
            'desktop': 1200
        }
        
        self.min_touch_target_size = 44  # pixels
        self.max_line_length = 75  # characters
        self.min_font_size_mobile = 14  # pixels
    
    def validate_theme_settings(self, settings: Dict[str, Any]) -> ValidationResult:
        """Validate entire theme settings for responsive design."""
        errors = []
        warnings = []
        
        # Validate layout settings
        if 'layout' in settings:
            layout_result = self._validate_layout_settings(settings['layout'])
            if not layout_result.is_valid:
                errors.append(f"Layout: {layout_result.error}")
            warnings.extend(layout_result.warnings)
        
        # Validate typography settings
        if 'typography' in settings:
            typography_result = self._validate_typography_settings(settings['typography'])
            if not typography_result.is_valid:
                errors.append(f"Typography: {typography_result.error}")
            warnings.extend(typography_result.warnings)
        
        # Validate spacing settings
        if 'spacing' in settings:
            spacing_result = self._validate_spacing_settings(settings['spacing'])
            if not spacing_result.is_valid:
                errors.append(f"Spacing: {spacing_result.error}")
            warnings.extend(spacing_result.warnings)
        
        # Validate color contrast
        if 'colors' in settings:
            contrast_result = self._validate_color_contrast(settings['colors'])
            if not contrast_result.is_valid:
                errors.append(f"Colors: {contrast_result.error}")
            warnings.extend(contrast_result.warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            error="; ".join(errors) if errors else "",
            warnings=warnings
        )
    
    def validate_setting(self, property_path: str, value: Any, 
                        full_settings: Dict[str, Any]) -> ValidationResult:
        """Validate a specific setting for responsive design impact."""
        path_parts = property_path.split('.')
        
        if len(path_parts) < 2:
            return ValidationResult(is_valid=True)
        
        section, property_name = path_parts[0], path_parts[1]
        
        if section == 'layout':
            return self._validate_layout_property(property_name, value)
        elif section == 'typography':
            return self._validate_typography_property(property_name, value)
        elif section == 'spacing':
            return self._validate_spacing_property(property_name, value)
        elif section == 'colors':
            return self._validate_color_property(property_name, value, full_settings.get('colors', {}))
        
        return ValidationResult(is_valid=True)
    
    def _validate_layout_settings(self, layout: Dict[str, Any]) -> ValidationResult:
        """Validate layout settings for responsive design."""
        warnings = []
        
        # Check container max width
        if 'container_max_width' in layout:
            max_width = self._parse_pixel_value(layout['container_max_width'])
            if max_width and max_width > 1400:
                warnings.append("Container max width is very large, may cause readability issues on wide screens")
            elif max_width and max_width < 320:
                return ValidationResult(
                    is_valid=False,
                    error="Container max width is too small for mobile devices"
                )
        
        # Check grid system
        if 'grid_columns' in layout:
            try:
                columns = int(layout['grid_columns'])
                if columns < 1 or columns > 24:
                    return ValidationResult(
                        is_valid=False,
                        error="Grid columns must be between 1 and 24"
                    )
                if columns > 12:
                    warnings.append("More than 12 grid columns may be difficult to manage on mobile")
            except (ValueError, TypeError):
                return ValidationResult(
                    is_valid=False,
                    error="Grid columns must be a valid number"
                )
        
        # Check header height
        if 'header_height' in layout:
            header_height = self._parse_pixel_value(layout['header_height'])
            if header_height and header_height > 120:
                warnings.append("Header height is large, may reduce content area on mobile")
            elif header_height and header_height < 40:
                warnings.append("Header height may be too small for touch targets")
        
        return ValidationResult(is_valid=True, warnings=warnings)
    
    def _validate_typography_settings(self, typography: Dict[str, Any]) -> ValidationResult:
        """Validate typography settings for responsive design."""
        warnings = []
        
        # Check base font size
        if 'font_size_base' in typography:
            font_size = self._parse_pixel_value(typography['font_size_base'])
            if font_size:
                if font_size < self.min_font_size_mobile:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Base font size {font_size}px is too small for mobile (minimum {self.min_font_size_mobile}px)"
                    )
                elif font_size > 24:
                    warnings.append("Base font size is very large, may cause layout issues")
        
        # Check line height
        if 'line_height_base' in typography:
            try:
                line_height = float(typography['line_height_base'])
                if line_height < 1.2:
                    warnings.append("Line height is low, may affect readability")
                elif line_height > 2.0:
                    warnings.append("Line height is very high, may waste space")
            except (ValueError, TypeError):
                # Could be a string value like "1.5em"
                pass
        
        # Check font families
        if 'font_family_primary' in typography:
            font_family = typography['font_family_primary']
            if not self._has_fallback_fonts(font_family):
                warnings.append("Primary font family should include fallback fonts")
        
        return ValidationResult(is_valid=True, warnings=warnings)
    
    def _validate_spacing_settings(self, spacing: Dict[str, Any]) -> ValidationResult:
        """Validate spacing settings for responsive design."""
        warnings = []
        
        # Check padding values
        padding_keys = ['padding_small', 'padding_medium', 'padding_large']
        for key in padding_keys:
            if key in spacing:
                padding = self._parse_pixel_value(spacing[key])
                if padding:
                    if padding < 4:
                        warnings.append(f"{key} is very small, may affect touch targets")
                    elif padding > 48:
                        warnings.append(f"{key} is very large, may waste space on mobile")
        
        # Check margin values
        margin_keys = ['margin_small', 'margin_medium', 'margin_large']
        for key in margin_keys:
            if key in spacing:
                margin = self._parse_pixel_value(spacing[key])
                if margin:
                    if margin > 64:
                        warnings.append(f"{key} is very large, may cause layout issues on mobile")
        
        return ValidationResult(is_valid=True, warnings=warnings)
    
    def _validate_color_contrast(self, colors: Dict[str, Any]) -> ValidationResult:
        """Validate color contrast for accessibility."""
        warnings = []
        
        # Check if we have both background and text colors
        if 'background' in colors and 'text' in colors:
            bg_color = colors['background']
            text_color = colors['text']
            
            # Basic contrast check (simplified)
            if self._colors_too_similar(bg_color, text_color):
                return ValidationResult(
                    is_valid=False,
                    error="Background and text colors have insufficient contrast"
                )
        
        # Check link color contrast
        if 'link' in colors and 'background' in colors:
            link_color = colors['link']
            bg_color = colors['background']
            
            if self._colors_too_similar(link_color, bg_color):
                warnings.append("Link color may have insufficient contrast with background")
        
        return ValidationResult(is_valid=True, warnings=warnings)
    
    def _validate_layout_property(self, property_name: str, value: Any) -> ValidationResult:
        """Validate a specific layout property."""
        if property_name == 'container_max_width':
            max_width = self._parse_pixel_value(value)
            if max_width and max_width < 320:
                return ValidationResult(
                    is_valid=False,
                    error="Container max width is too small for mobile devices"
                )
        
        elif property_name == 'grid_columns':
            try:
                columns = int(value)
                if columns < 1 or columns > 24:
                    return ValidationResult(
                        is_valid=False,
                        error="Grid columns must be between 1 and 24"
                    )
            except (ValueError, TypeError):
                return ValidationResult(
                    is_valid=False,
                    error="Grid columns must be a valid number"
                )
        
        return ValidationResult(is_valid=True)
    
    def _validate_typography_property(self, property_name: str, value: Any) -> ValidationResult:
        """Validate a specific typography property."""
        if property_name == 'font_size_base':
            font_size = self._parse_pixel_value(value)
            if font_size and font_size < self.min_font_size_mobile:
                return ValidationResult(
                    is_valid=False,
                    error=f"Font size {font_size}px is too small for mobile (minimum {self.min_font_size_mobile}px)"
                )
        
        elif property_name == 'line_height_base':
            try:
                line_height = float(value)
                if line_height < 1.0:
                    return ValidationResult(
                        is_valid=False,
                        error="Line height cannot be less than 1.0"
                    )
            except (ValueError, TypeError):
                # Could be a string value, which is valid
                pass
        
        return ValidationResult(is_valid=True)
    
    def _validate_spacing_property(self, property_name: str, value: Any) -> ValidationResult:
        """Validate a specific spacing property."""
        spacing_value = self._parse_pixel_value(value)
        if spacing_value is not None:
            if spacing_value < 0:
                return ValidationResult(
                    is_valid=False,
                    error="Spacing values cannot be negative"
                )
            
            # Check for reasonable limits
            if 'padding' in property_name and spacing_value > 100:
                return ValidationResult(
                    is_valid=False,
                    error="Padding value is too large and may cause layout issues"
                )
            
            if 'margin' in property_name and spacing_value > 200:
                return ValidationResult(
                    is_valid=False,
                    error="Margin value is too large and may cause layout issues"
                )
        
        return ValidationResult(is_valid=True)
    
    def _validate_color_property(self, property_name: str, value: Any, 
                                all_colors: Dict[str, Any]) -> ValidationResult:
        """Validate a specific color property."""
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                error="Color value must be a string"
            )
        
        # Basic color format validation
        if not self._is_valid_color_format(value):
            return ValidationResult(
                is_valid=False,
                error=f"Invalid color format: {value}"
            )
        
        # Check contrast if this is a text or background color
        if property_name == 'text' and 'background' in all_colors:
            if self._colors_too_similar(value, all_colors['background']):
                return ValidationResult(
                    is_valid=False,
                    error="Text color has insufficient contrast with background"
                )
        
        elif property_name == 'background' and 'text' in all_colors:
            if self._colors_too_similar(value, all_colors['text']):
                return ValidationResult(
                    is_valid=False,
                    error="Background color has insufficient contrast with text"
                )
        
        return ValidationResult(is_valid=True)
    
    def _parse_pixel_value(self, value: Any) -> Optional[int]:
        """Parse a pixel value from various formats."""
        if isinstance(value, (int, float)):
            return int(value)
        
        if isinstance(value, str):
            # Remove 'px' suffix and convert to int
            if value.endswith('px'):
                try:
                    return int(value[:-2])
                except ValueError:
                    pass
            
            # Try to convert directly to int
            try:
                return int(value)
            except ValueError:
                pass
        
        return None
    
    def _has_fallback_fonts(self, font_family: str) -> bool:
        """Check if font family includes fallback fonts."""
        if not isinstance(font_family, str):
            return False
        
        # Check for common fallback patterns
        fallbacks = ['sans-serif', 'serif', 'monospace', 'system-ui', 'Arial', 'Helvetica']
        font_lower = font_family.lower()
        
        return any(fallback.lower() in font_lower for fallback in fallbacks)
    
    def _is_valid_color_format(self, color: str) -> bool:
        """Check if color is in a valid format."""
        if not isinstance(color, str):
            return False
        
        color = color.strip()
        
        # Hex colors
        if re.match(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', color):
            return True
        
        # RGB/RGBA colors
        if re.match(r'^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(,\s*[\d.]+)?\s*\)$', color):
            return True
        
        # HSL/HSLA colors
        if re.match(r'^hsla?\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*(,\s*[\d.]+)?\s*\)$', color):
            return True
        
        # Named colors (basic check)
        named_colors = [
            'black', 'white', 'red', 'green', 'blue', 'yellow', 'cyan', 'magenta',
            'gray', 'grey', 'orange', 'purple', 'pink', 'brown', 'transparent'
        ]
        if color.lower() in named_colors:
            return True
        
        return False
    
    def _colors_too_similar(self, color1: str, color2: str) -> bool:
        """Check if two colors are too similar (simplified contrast check)."""
        # This is a simplified check - in production, you'd want to use
        # proper color contrast calculation (WCAG guidelines)
        
        # Convert to comparable format (simplified)
        def normalize_color(color):
            if color.startswith('#'):
                return color.lower()
            return color.lower()
        
        norm_color1 = normalize_color(color1)
        norm_color2 = normalize_color(color2)
        
        # Very basic similarity check
        if norm_color1 == norm_color2:
            return True
        
        # Check for common problematic combinations
        problematic_pairs = [
            ('#ffffff', '#f8f9fa'),  # White and very light gray
            ('#000000', '#212529'),  # Black and very dark gray
            ('#ffffff', '#ffffff'),  # Same colors
        ]
        
        for pair in problematic_pairs:
            if (norm_color1, norm_color2) == pair or (norm_color2, norm_color1) == pair:
                return True
        
        return False