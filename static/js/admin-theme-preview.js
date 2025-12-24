/**
 * Live Theme Preview System
 * Provides real-time theme customization preview functionality
 */

// ==================== LIVE THEME PREVIEW ====================

class LiveThemePreview {
    constructor() {
        this.previewFrame = null;
        this.previewDocument = null;
        this.currentTheme = {};
        this.cssVariables = new Map();
        this.previewStylesheet = null;
        
        this.init();
    }

    init() {
        this.setupPreviewFrame();
        this.loadCurrentTheme();
        this.setupEventListeners();
    }

    setupPreviewFrame() {
        this.previewFrame = document.getElementById('preview-iframe');
        if (!this.previewFrame) {
            console.warn('Preview iframe not found');
            return;
        }

        // Wait for iframe to load
        this.previewFrame.addEventListener('load', () => {
            this.previewDocument = this.previewFrame.contentDocument;
            this.initializePreviewStyles();
        });

        // If already loaded
        if (this.previewFrame.contentDocument && this.previewFrame.contentDocument.readyState === 'complete') {
            this.previewDocument = this.previewFrame.contentDocument;
            this.initializePreviewStyles();
        }
    }

    async loadCurrentTheme() {
        try {
            const response = await fetch('/api/admin/theme/current');
            const data = await response.json();
            
            if (data.success) {
                this.currentTheme = data.data.theme;
                this.generateCSSVariables();
            }
        } catch (error) {
            console.error('Failed to load current theme:', error);
        }
    }

    initializePreviewStyles() {
        if (!this.previewDocument) return;

        // Create or get the preview stylesheet
        let styleElement = this.previewDocument.getElementById('theme-preview-styles');
        
        if (!styleElement) {
            styleElement = this.previewDocument.createElement('style');
            styleElement.id = 'theme-preview-styles';
            styleElement.type = 'text/css';
            this.previewDocument.head.appendChild(styleElement);
        }

        this.previewStylesheet = styleElement;
        this.updatePreviewStyles();
    }

    generateCSSVariables() {
        this.cssVariables.clear();

        // Colors
        if (this.currentTheme.colors) {
            Object.entries(this.currentTheme.colors).forEach(([key, value]) => {
                this.cssVariables.set(`--color-${this.kebabCase(key)}`, value);
            });
        }

        // Typography
        if (this.currentTheme.typography) {
            const typography = this.currentTheme.typography;
            
            if (typography.fontFamily) {
                this.cssVariables.set('--font-family-base', typography.fontFamily);
            }
            
            if (typography.baseFontSize) {
                this.cssVariables.set('--font-size-base', `${typography.baseFontSize}px`);
            }
            
            if (typography.lineHeight) {
                this.cssVariables.set('--line-height-base', typography.lineHeight);
            }
        }

        // Layout
        if (this.currentTheme.layout) {
            const layout = this.currentTheme.layout;
            
            if (layout.containerWidth) {
                this.cssVariables.set('--container-width', `${layout.containerWidth}px`);
            }
            
            if (layout.borderRadius) {
                this.cssVariables.set('--border-radius-base', `${layout.borderRadius}px`);
            }
            
            if (layout.spacingUnit) {
                this.cssVariables.set('--spacing-unit', `${layout.spacingUnit}px`);
            }
        }

        // Components
        if (this.currentTheme.components) {
            this.generateComponentStyles();
        }
    }

    generateComponentStyles() {
        const components = this.currentTheme.components;

        // Button styles
        if (components.buttonStyle) {
            switch (components.buttonStyle) {
                case 'rounded':
                    this.cssVariables.set('--button-border-radius', 'var(--border-radius-base)');
                    break;
                case 'square':
                    this.cssVariables.set('--button-border-radius', '0');
                    break;
                case 'pill':
                    this.cssVariables.set('--button-border-radius', '50px');
                    break;
            }
        }

        // Card shadows
        if (components.cardShadow) {
            const shadows = {
                none: 'none',
                subtle: '0 1px 3px rgba(0, 0, 0, 0.1)',
                medium: '0 4px 6px rgba(0, 0, 0, 0.1)',
                strong: '0 10px 25px rgba(0, 0, 0, 0.15)'
            };
            
            this.cssVariables.set('--card-shadow', shadows[components.cardShadow] || shadows.subtle);
        }
    }

    updatePreviewStyles() {
        if (!this.previewStylesheet) return;

        const cssText = this.generateCSS();
        this.previewStylesheet.textContent = cssText;
    }

    generateCSS() {
        let css = ':root {\n';
        
        // Add CSS variables
        this.cssVariables.forEach((value, key) => {
            css += `  ${key}: ${value};\n`;
        });
        
        css += '}\n\n';

        // Add component-specific styles
        css += this.generateComponentCSS();

        return css;
    }

    generateComponentCSS() {
        let css = '';

        // Button styles
        css += `
        .btn, button {
            border-radius: var(--button-border-radius, var(--border-radius-base));
            font-family: var(--font-family-base);
            font-size: var(--font-size-base);
        }
        `;

        // Card styles
        css += `
        .card, .product-card, .admin-card {
            box-shadow: var(--card-shadow);
            border-radius: var(--border-radius-base);
        }
        `;

        // Container styles
        css += `
        .container {
            max-width: var(--container-width);
        }
        `;

        // Typography styles
        css += `
        body {
            font-family: var(--font-family-base);
            font-size: var(--font-size-base);
            line-height: var(--line-height-base);
        }
        `;

        // Color applications
        if (this.currentTheme.colors) {
            css += this.generateColorCSS();
        }

        return css;
    }

    generateColorCSS() {
        let css = '';
        const colors = this.currentTheme.colors;

        // Primary color applications
        if (colors.primary) {
            css += `
            .btn-primary {
                background-color: var(--color-primary);
                border-color: var(--color-primary);
            }
            
            .text-primary {
                color: var(--color-primary);
            }
            
            .bg-primary {
                background-color: var(--color-primary);
            }
            `;
        }

        // Secondary color applications
        if (colors.secondary) {
            css += `
            .btn-secondary {
                background-color: var(--color-secondary);
                border-color: var(--color-secondary);
            }
            
            .text-secondary {
                color: var(--color-secondary);
            }
            
            .bg-secondary {
                background-color: var(--color-secondary);
            }
            `;
        }

        // Background colors
        if (colors.background) {
            css += `
            body {
                background-color: var(--color-background);
            }
            `;
        }

        // Text colors
        if (colors.text) {
            css += `
            body, .text-default {
                color: var(--color-text);
            }
            `;
        }

        return css;
    }

    updatePreview(newTheme) {
        this.currentTheme = { ...this.currentTheme, ...newTheme };
        this.generateCSSVariables();
        this.updatePreviewStyles();
        
        // Trigger preview refresh animation
        this.animatePreviewUpdate();
    }

    animatePreviewUpdate() {
        if (!this.previewFrame) return;

        this.previewFrame.style.opacity = '0.8';
        this.previewFrame.style.transform = 'scale(0.98)';
        
        setTimeout(() => {
            this.previewFrame.style.opacity = '1';
            this.previewFrame.style.transform = 'scale(1)';
        }, 150);
    }

    setupEventListeners() {
        // Listen for device preview changes
        document.addEventListener('click', (e) => {
            if (e.target.matches('.preview-device')) {
                const device = e.target.getAttribute('data-device');
                this.switchDevice(device);
            }
        });

        // Listen for theme reset
        document.addEventListener('themeReset', () => {
            this.loadCurrentTheme();
        });
    }

    switchDevice(device) {
        if (!this.previewFrame) return;

        const previewContainer = this.previewFrame.parentElement;
        
        // Remove existing device classes
        previewContainer.classList.remove('device-desktop', 'device-tablet', 'device-mobile');
        
        // Add new device class
        previewContainer.classList.add(`device-${device}`);
        
        // Update iframe dimensions
        this.updatePreviewDimensions(device);
    }

    updatePreviewDimensions(device) {
        const dimensions = {
            desktop: { width: '100%', height: '600px' },
            tablet: { width: '768px', height: '1024px' },
            mobile: { width: '375px', height: '667px' }
        };

        const dim = dimensions[device] || dimensions.desktop;
        
        this.previewFrame.style.width = dim.width;
        this.previewFrame.style.height = dim.height;
        
        // Center the preview if it's smaller than container
        const container = this.previewFrame.parentElement;
        if (device !== 'desktop') {
            container.style.display = 'flex';
            container.style.justifyContent = 'center';
            container.style.alignItems = 'flex-start';
        } else {
            container.style.display = 'block';
        }
    }

    // Utility methods
    kebabCase(str) {
        return str.replace(/([a-z0-9]|(?=[A-Z]))([A-Z])/g, '$1-$2').toLowerCase();
    }

    // Export current theme
    exportTheme() {
        return JSON.stringify(this.currentTheme, null, 2);
    }

    // Import theme
    importTheme(themeData) {
        try {
            const theme = typeof themeData === 'string' ? JSON.parse(themeData) : themeData;
            this.updatePreview(theme);
            return true;
        } catch (error) {
            console.error('Failed to import theme:', error);
            return false;
        }
    }

    // Reset to default theme
    async resetToDefault() {
        try {
            const response = await fetch('/api/admin/theme/default');
            const data = await response.json();
            
            if (data.success) {
                this.currentTheme = data.data.theme;
                this.generateCSSVariables();
                this.updatePreviewStyles();
                return true;
            }
        } catch (error) {
            console.error('Failed to reset theme:', error);
        }
        return false;
    }

    // Get preview screenshot (if supported)
    async getPreviewScreenshot() {
        if (!this.previewFrame || !this.previewFrame.contentWindow) {
            return null;
        }

        try {
            // This would require additional setup for cross-origin iframe screenshots
            // For now, we'll return a placeholder
            return '/api/admin/theme/preview-screenshot';
        } catch (error) {
            console.error('Failed to capture screenshot:', error);
            return null;
        }
    }

    // Cleanup
    destroy() {
        if (this.previewStylesheet && this.previewStylesheet.parentNode) {
            this.previewStylesheet.parentNode.removeChild(this.previewStylesheet);
        }
        
        this.cssVariables.clear();
        this.currentTheme = {};
    }
}

// ==================== THEME COMPARISON TOOL ====================

class ThemeComparisonTool {
    constructor() {
        this.themes = new Map();
        this.comparisonContainer = null;
        
        this.init();
    }

    init() {
        this.createComparisonInterface();
    }

    createComparisonInterface() {
        const container = document.getElementById('theme-comparison-container');
        if (!container) return;

        this.comparisonContainer = container;
        
        container.innerHTML = `
            <div class="theme-comparison">
                <div class="comparison-header">
                    <h3>Theme Comparison</h3>
                    <div class="comparison-controls">
                        <button class="btn btn-secondary" id="add-theme-comparison">
                            <i class="icon-plus"></i> Add Theme
                        </button>
                        <button class="btn btn-secondary" id="clear-comparison">
                            <i class="icon-trash"></i> Clear All
                        </button>
                    </div>
                </div>
                
                <div class="comparison-grid" id="comparison-grid">
                    <!-- Theme comparisons will be added here -->
                </div>
            </div>
        `;

        this.setupComparisonEvents();
    }

    setupComparisonEvents() {
        document.getElementById('add-theme-comparison')?.addEventListener('click', () => {
            this.addThemeToComparison();
        });

        document.getElementById('clear-comparison')?.addEventListener('click', () => {
            this.clearComparison();
        });
    }

    addThemeToComparison(theme = null) {
        const themeId = theme ? theme.id : `theme-${Date.now()}`;
        const themeData = theme || this.getCurrentTheme();
        
        this.themes.set(themeId, themeData);
        this.renderComparison();
    }

    removeThemeFromComparison(themeId) {
        this.themes.delete(themeId);
        this.renderComparison();
    }

    renderComparison() {
        const grid = document.getElementById('comparison-grid');
        if (!grid) return;

        const themesHTML = Array.from(this.themes.entries()).map(([id, theme]) => `
            <div class="theme-comparison-item" data-theme-id="${id}">
                <div class="theme-preview-mini">
                    <iframe src="/preview?theme=${encodeURIComponent(JSON.stringify(theme))}" 
                            class="mini-preview-frame"></iframe>
                </div>
                
                <div class="theme-details">
                    <h4>${theme.name || 'Unnamed Theme'}</h4>
                    <div class="theme-colors">
                        ${Object.entries(theme.colors || {}).map(([key, value]) => `
                            <div class="color-swatch" style="background-color: ${value}" title="${key}: ${value}"></div>
                        `).join('')}
                    </div>
                    <div class="theme-actions">
                        <button class="btn btn-sm btn-primary" data-action="apply-theme" data-theme-id="${id}">
                            Apply
                        </button>
                        <button class="btn btn-sm btn-secondary" data-action="export-theme" data-theme-id="${id}">
                            Export
                        </button>
                        <button class="btn btn-sm btn-danger" data-action="remove-theme" data-theme-id="${id}">
                            Remove
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        grid.innerHTML = themesHTML;

        // Setup action handlers
        grid.addEventListener('click', (e) => {
            const action = e.target.getAttribute('data-action');
            const themeId = e.target.getAttribute('data-theme-id');
            
            switch (action) {
                case 'apply-theme':
                    this.applyTheme(themeId);
                    break;
                case 'export-theme':
                    this.exportTheme(themeId);
                    break;
                case 'remove-theme':
                    this.removeThemeFromComparison(themeId);
                    break;
            }
        });
    }

    applyTheme(themeId) {
        const theme = this.themes.get(themeId);
        if (!theme) return;

        // Apply theme to main preview
        if (window.adminInterface) {
            const themeCustomizer = window.adminInterface.getComponent('themeCustomizer');
            if (themeCustomizer && themeCustomizer.previewHandler) {
                themeCustomizer.previewHandler.updatePreview(theme);
            }
        }
    }

    exportTheme(themeId) {
        const theme = this.themes.get(themeId);
        if (!theme) return;

        const dataStr = JSON.stringify(theme, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `theme-${themeId}.json`;
        link.click();
        
        URL.revokeObjectURL(link.href);
    }

    clearComparison() {
        this.themes.clear();
        this.renderComparison();
    }

    getCurrentTheme() {
        // This would get the current theme from the theme customizer
        return {
            name: 'Current Theme',
            colors: {
                primary: '#007bff',
                secondary: '#6c757d',
                background: '#ffffff',
                text: '#333333'
            },
            typography: {
                fontFamily: 'Arial, sans-serif',
                baseFontSize: 16,
                lineHeight: 1.5
            },
            layout: {
                containerWidth: 1200,
                borderRadius: 4,
                spacingUnit: 8
            }
        };
    }
}

// Export theme preview components
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        LiveThemePreview,
        ThemeComparisonTool
    };
}