/**
 * Inline Editing Functionality for Admin Interface
 * Provides rich text editing, image editing, and configuration editing capabilities
 */

// ==================== BASE INLINE EDITOR ====================

class BaseInlineEditor {
    constructor(element) {
        this.element = element;
        this.contentId = element.dataset.contentId || element.dataset.configKey;
        this.originalContent = '';
        this.isActive = false;
        this.hasUnsavedChanges = false;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.originalContent = this.getContent();
    }

    setupEventListeners() {
        this.element.addEventListener('click', this.handleClick.bind(this));
        this.element.addEventListener('dblclick', this.handleDoubleClick.bind(this));
        this.element.addEventListener('keydown', this.handleKeydown.bind(this));
    }

    handleClick(e) {
        if (!this.isActive) {
            e.preventDefault();
            this.activate();
        }
    }

    handleDoubleClick(e) {
        e.preventDefault();
        this.activate();
    }

    handleKeydown(e) {
        if (!this.isActive) return;

        switch (e.key) {
            case 'Enter':
                if (!e.shiftKey) {
                    e.preventDefault();
                    this.save();
                }
                break;
            case 'Escape':
                e.preventDefault();
                this.cancel();
                break;
            case 's':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    this.save();
                }
                break;
        }
    }

    activate() {
        if (this.isActive) return;

        this.isActive = true;
        this.element.classList.add('editing');
        this.originalContent = this.getContent();
        
        try {
            this.createEditingInterface();
            this.focusEditor();
        } catch (error) {
            console.error('Error creating editing interface:', error);
            this.deactivate();
            return;
        }
        
        // Add global click listener to detect clicks outside
        setTimeout(() => {
            document.addEventListener('click', this.handleOutsideClick.bind(this));
        }, 100);
    }

    createEditingInterface() {
        // Override in subclasses
    }

    focusEditor() {
        // Override in subclasses
    }

    handleOutsideClick(e) {
        if (!this.isActive) return;
        
        if (!this.element.contains(e.target) && !this.isEditingToolbar(e.target)) {
            this.save();
        }
    }

    isEditingToolbar(element) {
        return element.closest('.inline-editor-toolbar') !== null;
    }

    async save() {
        if (!this.isActive) return;

        const newContent = this.getContent();
        
        if (newContent === this.originalContent) {
            this.deactivate();
            return;
        }

        try {
            const success = await this.saveContent(newContent);
            
            if (success) {
                this.originalContent = newContent;
                this.hasUnsavedChanges = false;
                this.showNotification('Content saved successfully', 'success');
                this.deactivate();
            } else {
                this.showNotification('Failed to save content', 'error');
            }
        } catch (error) {
            console.error('Save error:', error);
            this.showNotification('Error saving content', 'error');
        }
    }

    cancel() {
        if (!this.isActive) return;

        this.setContent(this.originalContent);
        this.hasUnsavedChanges = false;
        this.deactivate();
    }

    deactivate() {
        if (!this.isActive) return;

        this.isActive = false;
        this.element.classList.remove('editing');
        
        try {
            this.destroyEditingInterface();
        } catch (error) {
            console.error('Error destroying editing interface:', error);
        }
        
        // Remove global click listener
        document.removeEventListener('click', this.handleOutsideClick.bind(this));
    }

    destroyEditingInterface() {
        // Override in subclasses
    }

    getContent() {
        // Override in subclasses
        return this.element.textContent || this.element.innerHTML;
    }

    setContent(content) {
        // Override in subclasses
        this.element.textContent = content;
    }

    async saveContent(content) {
        // Override in subclasses
        return true;
    }

    hasChanges() {
        return this.hasUnsavedChanges || this.getContent() !== this.originalContent;
    }

    showNotification(message, type) {
        // This would integrate with the main notification system
        console.log(`${type.toUpperCase()}: ${message}`);
    }

    destroy() {
        this.deactivate();
        // Remove event listeners
    }
}

// ==================== INLINE TEXT EDITOR ====================

class InlineTextEditor extends BaseInlineEditor {
    constructor(element) {
        super(element);
        this.toolbar = null;
        this.isRichText = element.dataset.editable === 'rich-text';
    }

    createEditingInterface() {
        if (this.isRichText) {
            this.createRichTextEditor();
        } else {
            this.createSimpleTextEditor();
        }
    }

    createSimpleTextEditor() {
        this.element.contentEditable = true;
        this.element.focus();
        
        // Select all text
        const range = document.createRange();
        range.selectNodeContents(this.element);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
    }

    createRichTextEditor() {
        this.element.contentEditable = true;
        this.createToolbar();
        this.element.focus();
    }

    createToolbar() {
        this.toolbar = document.createElement('div');
        this.toolbar.className = 'inline-editor-toolbar';
        this.toolbar.innerHTML = `
            <div class="toolbar-group">
                <button type="button" class="toolbar-btn" data-command="bold" title="Bold">
                    <i class="icon-bold"></i>
                </button>
                <button type="button" class="toolbar-btn" data-command="italic" title="Italic">
                    <i class="icon-italic"></i>
                </button>
                <button type="button" class="toolbar-btn" data-command="underline" title="Underline">
                    <i class="icon-underline"></i>
                </button>
            </div>
            <div class="toolbar-group">
                <button type="button" class="toolbar-btn" data-command="insertUnorderedList" title="Bullet List">
                    <i class="icon-list"></i>
                </button>
                <button type="button" class="toolbar-btn" data-command="insertOrderedList" title="Numbered List">
                    <i class="icon-list-numbered"></i>
                </button>
            </div>
            <div class="toolbar-group">
                <button type="button" class="toolbar-btn" data-command="createLink" title="Insert Link">
                    <i class="icon-link"></i>
                </button>
                <button type="button" class="toolbar-btn" data-command="unlink" title="Remove Link">
                    <i class="icon-unlink"></i>
                </button>
            </div>
            <div class="toolbar-group">
                <button type="button" class="toolbar-btn toolbar-save" title="Save">
                    <i class="icon-check"></i>
                </button>
                <button type="button" class="toolbar-btn toolbar-cancel" title="Cancel">
                    <i class="icon-x"></i>
                </button>
            </div>
        `;

        // Position toolbar
        const rect = this.element.getBoundingClientRect();
        this.toolbar.style.position = 'fixed';
        this.toolbar.style.top = (rect.top - 50) + 'px';
        this.toolbar.style.left = rect.left + 'px';
        this.toolbar.style.zIndex = '10000';

        document.body.appendChild(this.toolbar);

        // Setup toolbar event listeners
        this.toolbar.addEventListener('click', this.handleToolbarClick.bind(this));
    }

    handleToolbarClick(e) {
        e.preventDefault();
        const button = e.target.closest('.toolbar-btn');
        if (!button) return;

        const command = button.dataset.command;

        if (button.classList.contains('toolbar-save')) {
            this.save();
        } else if (button.classList.contains('toolbar-cancel')) {
            this.cancel();
        } else if (command) {
            this.executeCommand(command);
        }
    }

    executeCommand(command) {
        if (command === 'createLink') {
            const url = prompt('Enter URL:');
            if (url) {
                document.execCommand(command, false, url);
            }
        } else {
            document.execCommand(command, false, null);
        }

        this.hasUnsavedChanges = true;
        this.element.focus();
    }

    focusEditor() {
        this.element.focus();
        
        // Place cursor at end
        const range = document.createRange();
        const selection = window.getSelection();
        range.selectNodeContents(this.element);
        range.collapse(false);
        selection.removeAllRanges();
        selection.addRange(range);
    }

    destroyEditingInterface() {
        this.element.contentEditable = false;
        
        if (this.toolbar) {
            document.body.removeChild(this.toolbar);
            this.toolbar = null;
        }
    }

    getContent() {
        return this.isRichText ? this.element.innerHTML : this.element.textContent;
    }

    setContent(content) {
        if (this.isRichText) {
            this.element.innerHTML = content;
        } else {
            this.element.textContent = content;
        }
    }

    async saveContent(content) {
        try {
            const response = await fetch('/api/admin/content/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content_id: this.contentId,
                    content: content,
                    type: this.isRichText ? 'rich-text' : 'text'
                })
            });

            // Check if response is HTML (likely a redirect to login)
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/html')) {
                console.warn('Received HTML response, likely authentication required');
                this.showNotification('Authentication required. Please log in.', 'warning');
                return false;
            }

            const data = await response.json();
            return data.success;
        } catch (error) {
            console.error('Failed to save text content:', error);
            return false;
        }
    }
}

// ==================== INLINE IMAGE EDITOR ====================

class InlineImageEditor extends BaseInlineEditor {
    constructor(element) {
        super(element);
        this.imageModal = null;
        this.uploadArea = null;
        this.boundHandlers = {
            fileChange: null,
            dragOver: null,
            drop: null
        };
    }

    handleClick(e) {
        e.preventDefault();
        this.activate();
    }

    createEditingInterface() {
        console.log('Creating image editing interface for content ID:', this.contentId);
        this.createImageModal();
    }

    createImageModal() {
        console.log('Creating image modal for element:', this.element);
        
        this.imageModal = document.createElement('div');
        this.imageModal.className = 'inline-image-modal';
        this.imageModal.innerHTML = `
            <div class="image-modal-content">
                <div class="image-modal-header">
                    <h3>Edit Image</h3>
                    <button class="modal-close" type="button">×</button>
                </div>
                
                <div class="image-modal-body">
                    <div class="current-image">
                        <img src="${this.element.src}" alt="${this.element.alt || ''}" id="current-image-preview">
                    </div>
                    
                    <div class="image-options">
                        <div class="option-group">
                            <label for="image-alt">Alt Text:</label>
                            <input type="text" id="image-alt" value="${this.element.alt || ''}" class="form-control">
                        </div>
                        
                        <div class="option-group">
                            <label for="image-url">Image URL:</label>
                            <input type="url" id="image-url" value="${this.element.src}" class="form-control">
                        </div>
                        
                        <div class="option-group">
                            <label>Upload New Image:</label>
                            <div class="image-upload-area" id="image-upload-area">
                                <div class="upload-placeholder">
                                    <i class="icon-upload"></i>
                                    <p>Drag & drop an image here or click to browse</p>
                                </div>
                                <input type="file" id="image-file-input" accept="image/*" style="display: none;">
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="image-modal-footer">
                    <button type="button" class="btn btn-secondary modal-cancel">Cancel</button>
                    <button type="button" class="btn btn-primary modal-save">Save Changes</button>
                </div>
            </div>
        `;

        document.body.appendChild(this.imageModal);
        console.log('Image modal created and added to DOM');
        
        this.setupImageModalEvents();
        
        // Show modal
        setTimeout(() => {
            if (this.imageModal) {
                this.imageModal.classList.add('show');
                console.log('Image modal shown');
            }
        }, 100);
    }

    setupImageModalEvents() {
        const modal = this.imageModal;
        if (!modal) {
            console.error('Cannot setup events: image modal is null');
            return;
        }
        
        // Close modal events
        const closeBtn = modal.querySelector('.modal-close');
        const cancelBtn = modal.querySelector('.modal-cancel');
        const saveBtn = modal.querySelector('.modal-save');
        const urlInput = modal.querySelector('#image-url');
        const preview = modal.querySelector('#current-image-preview');
        const uploadArea = modal.querySelector('#image-upload-area');
        const fileInput = modal.querySelector('#image-file-input');
        
        if (closeBtn) closeBtn.addEventListener('click', () => this.cancel());
        if (cancelBtn) cancelBtn.addEventListener('click', () => this.cancel());
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.cancel();
        });
        
        // Save button
        if (saveBtn) saveBtn.addEventListener('click', () => this.saveImageChanges());
        
        // URL input change
        if (urlInput && preview) {
            urlInput.addEventListener('input', (e) => {
                preview.src = e.target.value;
            });
        }
        
        // File upload
        if (uploadArea && fileInput) {
            // Store bound handlers for proper cleanup
            this.boundHandlers.dragOver = this.handleDragOver.bind(this);
            this.boundHandlers.drop = this.handleDrop.bind(this);
            this.boundHandlers.fileChange = (e) => {
                if (e.target.files.length > 0) {
                    // Add a small delay to ensure modal is still available
                    setTimeout(() => {
                        if (this.isActive && this.imageModal) {
                            this.handleFileUpload(e.target.files[0]);
                        } else {
                            console.warn('Image editor is no longer active or modal is not available');
                        }
                    }, 10);
                }
            };
            
            uploadArea.addEventListener('click', () => fileInput.click());
            uploadArea.addEventListener('dragover', this.boundHandlers.dragOver);
            uploadArea.addEventListener('drop', this.boundHandlers.drop);
            fileInput.addEventListener('change', this.boundHandlers.fileChange);
        }
    }

    handleDragOver(e) {
        e.preventDefault();
        if (e.currentTarget) {
            e.currentTarget.classList.add('drag-over');
        }
    }

    handleDrop(e) {
        e.preventDefault();
        if (e.currentTarget) {
            e.currentTarget.classList.remove('drag-over');
        }
        
        const files = e.dataTransfer.files;
        if (files.length > 0 && files[0].type.startsWith('image/')) {
            // Check if editor is still active before processing
            if (this.isActive && this.imageModal) {
                this.handleFileUpload(files[0]);
            } else {
                console.warn('Image editor is no longer active or modal is not available for drag & drop');
            }
        }
    }

    async handleFileUpload(file) {
        if (!this.imageModal) {
            console.error('Image modal not available for file upload');
            return;
        }
        
        const uploadArea = this.imageModal.querySelector('#image-upload-area');
        if (!uploadArea) {
            console.error('Upload area not found in image modal');
            return;
        }
        
        uploadArea.innerHTML = '<div class="upload-progress">Uploading...</div>';
        
        try {
            const formData = new FormData();
            formData.append('image', file);
            formData.append('content_id', this.contentId);
            
            const response = await fetch('/api/admin/content/upload-image', {
                method: 'POST',
                body: formData
            });
            
            // Check if response is HTML (likely a redirect to login)
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/html')) {
                console.warn('Received HTML response, likely authentication required');
                uploadArea.innerHTML = '<div class="upload-error">Authentication required. Please log in.</div>';
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                const urlInput = this.imageModal.querySelector('#image-url');
                const preview = this.imageModal.querySelector('#current-image-preview');
                
                if (urlInput && preview) {
                    urlInput.value = data.data.url;
                    preview.src = data.data.url;
                    uploadArea.innerHTML = '<div class="upload-success">✓ Upload successful</div>';
                } else {
                    uploadArea.innerHTML = '<div class="upload-error">Modal elements not found</div>';
                }
            } else {
                uploadArea.innerHTML = '<div class="upload-error">Upload failed: ' + (data.error || 'Unknown error') + '</div>';
            }
        } catch (error) {
            console.error('Upload error:', error);
            uploadArea.innerHTML = '<div class="upload-error">Upload failed</div>';
        }
    }

    async saveImageChanges() {
        if (!this.imageModal) {
            console.error('Image modal not available for saving changes');
            return;
        }
        
        const modal = this.imageModal;
        const newSrc = modal.querySelector('#image-url')?.value || '';
        const newAlt = modal.querySelector('#image-alt')?.value || '';
        
        try {
            const success = await this.saveContent({
                src: newSrc,
                alt: newAlt
            });
            
            if (success) {
                this.element.src = newSrc;
                this.element.alt = newAlt;
                this.showNotification('Image updated successfully', 'success');
                this.deactivate();
            } else {
                this.showNotification('Failed to update image', 'error');
            }
        } catch (error) {
            console.error('Save error:', error);
            this.showNotification('Error updating image', 'error');
        }
    }

    destroyEditingInterface() {
        console.log('Destroying image editing interface for content ID:', this.contentId);
        
        if (this.imageModal) {
            // Remove specific event listeners if we have references
            const uploadArea = this.imageModal.querySelector('#image-upload-area');
            const fileInput = this.imageModal.querySelector('#image-file-input');
            
            if (uploadArea && this.boundHandlers.dragOver && this.boundHandlers.drop) {
                uploadArea.removeEventListener('dragover', this.boundHandlers.dragOver);
                uploadArea.removeEventListener('drop', this.boundHandlers.drop);
            }
            
            if (fileInput && this.boundHandlers.fileChange) {
                fileInput.removeEventListener('change', this.boundHandlers.fileChange);
            }
            
            // Clear bound handlers
            this.boundHandlers = {
                fileChange: null,
                dragOver: null,
                drop: null
            };
            
            // Remove modal from DOM
            try {
                document.body.removeChild(this.imageModal);
                console.log('Image modal removed from DOM');
            } catch (error) {
                console.warn('Error removing image modal from DOM:', error);
            }
            this.imageModal = null;
        } else {
            console.log('No image modal to destroy');
        }
    }

    getContent() {
        return {
            src: this.element.src,
            alt: this.element.alt || ''
        };
    }

    setContent(content) {
        if (typeof content === 'object') {
            this.element.src = content.src;
            this.element.alt = content.alt || '';
        }
    }

    async saveContent(content) {
        try {
            const response = await fetch('/api/admin/content/update-image', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content_id: this.contentId,
                    src: content.src,
                    alt: content.alt
                })
            });

            // Check if response is HTML (likely a redirect to login)
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/html')) {
                console.warn('Received HTML response, likely authentication required');
                this.showNotification('Authentication required. Please log in.', 'warning');
                return false;
            }

            const data = await response.json();
            return data.success;
        } catch (error) {
            console.error('Failed to save image content:', error);
            return false;
        }
    }
}

// ==================== INLINE CONFIG EDITOR ====================

class InlineConfigEditor extends BaseInlineEditor {
    constructor(element) {
        super(element);
        this.configKey = element.dataset.configKey;
        this.configType = element.dataset.configType || 'text';
        this.configModal = null;
    }

    createEditingInterface() {
        if (this.configType === 'select' || this.configType === 'color' || this.configType === 'number') {
            this.createConfigModal();
        } else {
            this.createSimpleConfigEditor();
        }
    }

    createSimpleConfigEditor() {
        this.element.contentEditable = true;
        this.element.focus();
        
        // Select all text
        const range = document.createRange();
        range.selectNodeContents(this.element);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
    }

    createConfigModal() {
        this.configModal = document.createElement('div');
        this.configModal.className = 'inline-config-modal';
        
        let inputHTML = '';
        const currentValue = this.getContent();
        
        switch (this.configType) {
            case 'color':
                inputHTML = `
                    <div class="config-input-group">
                        <label for="config-input">Color:</label>
                        <div class="color-input-group">
                            <input type="color" id="config-input" value="${currentValue}">
                            <input type="text" id="config-text" value="${currentValue}" class="form-control">
                        </div>
                    </div>
                `;
                break;
            case 'number':
                inputHTML = `
                    <div class="config-input-group">
                        <label for="config-input">Value:</label>
                        <input type="number" id="config-input" value="${currentValue}" class="form-control">
                    </div>
                `;
                break;
            case 'select':
                const options = this.element.dataset.options ? JSON.parse(this.element.dataset.options) : [];
                inputHTML = `
                    <div class="config-input-group">
                        <label for="config-input">Select:</label>
                        <select id="config-input" class="form-control">
                            ${options.map(option => 
                                `<option value="${option.value}" ${option.value === currentValue ? 'selected' : ''}>${option.label}</option>`
                            ).join('')}
                        </select>
                    </div>
                `;
                break;
            default:
                inputHTML = `
                    <div class="config-input-group">
                        <label for="config-input">Value:</label>
                        <input type="text" id="config-input" value="${currentValue}" class="form-control">
                    </div>
                `;
        }
        
        this.configModal.innerHTML = `
            <div class="config-modal-content">
                <div class="config-modal-header">
                    <h3>Edit ${this.formatConfigKey(this.configKey)}</h3>
                    <button class="modal-close" type="button">×</button>
                </div>
                
                <div class="config-modal-body">
                    ${inputHTML}
                </div>
                
                <div class="config-modal-footer">
                    <button type="button" class="btn btn-secondary modal-cancel">Cancel</button>
                    <button type="button" class="btn btn-primary modal-save">Save</button>
                </div>
            </div>
        `;

        document.body.appendChild(this.configModal);
        this.setupConfigModalEvents();
        
        // Show modal
        setTimeout(() => {
            this.configModal.classList.add('show');
        }, 100);
    }

    setupConfigModalEvents() {
        const modal = this.configModal;
        
        // Close modal events
        modal.querySelector('.modal-close').addEventListener('click', () => this.cancel());
        modal.querySelector('.modal-cancel').addEventListener('click', () => this.cancel());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.cancel();
        });
        
        // Save button
        modal.querySelector('.modal-save').addEventListener('click', () => this.saveConfigChanges());
        
        // Color picker sync
        if (this.configType === 'color') {
            const colorInput = modal.querySelector('#config-input');
            const textInput = modal.querySelector('#config-text');
            
            colorInput.addEventListener('input', (e) => {
                textInput.value = e.target.value;
            });
            
            textInput.addEventListener('input', (e) => {
                if (/^#[0-9A-F]{6}$/i.test(e.target.value)) {
                    colorInput.value = e.target.value;
                }
            });
        }
        
        // Focus input
        const input = modal.querySelector('#config-input');
        if (input) {
            input.focus();
            if (input.type === 'text') {
                input.select();
            }
        }
    }

    async saveConfigChanges() {
        const input = this.configModal.querySelector('#config-input');
        const newValue = input.value;
        
        try {
            const success = await this.saveContent(newValue);
            
            if (success) {
                this.setContent(newValue);
                this.showNotification('Configuration updated successfully', 'success');
                this.deactivate();
            } else {
                this.showNotification('Failed to update configuration', 'error');
            }
        } catch (error) {
            console.error('Save error:', error);
            this.showNotification('Error updating configuration', 'error');
        }
    }

    destroyEditingInterface() {
        this.element.contentEditable = false;
        
        if (this.configModal) {
            document.body.removeChild(this.configModal);
            this.configModal = null;
        }
    }

    getContent() {
        return this.element.textContent || this.element.dataset.value || '';
    }

    setContent(content) {
        this.element.textContent = content;
        this.element.dataset.value = content;
    }

    async saveContent(content) {
        try {
            const response = await fetch('/api/admin/configuration/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    key: this.configKey,
                    value: content
                })
            });

            const data = await response.json();
            return data.success;
        } catch (error) {
            console.error('Failed to save config:', error);
            return false;
        }
    }

    formatConfigKey(key) {
        return key.replace(/[_-]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
}

// Export inline editors for browser use
if (typeof window !== 'undefined') {
    window.BaseInlineEditor = BaseInlineEditor;
    window.InlineTextEditor = InlineTextEditor;
    window.InlineImageEditor = InlineImageEditor;
    window.InlineConfigEditor = InlineConfigEditor;
}

// Export inline editors for Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        BaseInlineEditor,
        InlineTextEditor,
        InlineImageEditor,
        InlineConfigEditor
    };
}