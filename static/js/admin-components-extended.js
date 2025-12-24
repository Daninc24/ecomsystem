/**
 * Extended Admin Frontend Components
 * Additional component classes for specialized admin functionality
 */

// ==================== PRODUCT MANAGER COMPONENT ====================

class ProductManagerComponent extends BaseAdminComponent {
    constructor() {
        super('product-management-container');
        this.products = [];
        this.categories = [];
        this.selectedProducts = new Set();
    }

    render() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="product-manager">
                <div class="product-manager-header">
                    <h2>Product Management</h2>
                    <div class="product-manager-actions">
                        <button class="btn btn-primary" data-action="addProduct">
                            <i class="icon-plus"></i> Add Product
                        </button>
                        <button class="btn btn-secondary" data-action="bulkEdit" id="bulk-edit-btn" disabled>
                            <i class="icon-edit"></i> Bulk Edit (<span id="selected-count">0</span>)
                        </button>
                        <button class="btn btn-secondary" data-action="importProducts">
                            <i class="icon-upload"></i> Import
                        </button>
                    </div>
                </div>
                
                <div class="product-manager-filters">
                    <div class="filter-group">
                        <input type="text" class="form-control" placeholder="Search products..." id="product-search">
                        <select class="form-control" id="category-filter">
                            <option value="">All Categories</option>
                        </select>
                        <select class="form-control" id="status-filter">
                            <option value="">All Status</option>
                            <option value="active">Active</option>
                            <option value="inactive">Inactive</option>
                            <option value="out_of_stock">Out of Stock</option>
                        </select>
                    </div>
                </div>
                
                <div class="product-manager-content">
                    <div class="category-tree-panel" id="category-tree-panel">
                        <h3>Categories</h3>
                        <div class="category-tree" id="category-tree">
                            <!-- Category tree will be populated here -->
                        </div>
                    </div>
                    
                    <div class="product-list-panel">
                        <div class="product-list" id="product-list">
                            <!-- Products will be populated here -->
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.loadCategories();
        this.loadProducts();
    }

    async loadCategories() {
        try {
            const data = await this.apiCall('/api/admin/products/categories');
            if (data.success) {
                this.categories = data.data.categories;
                this.renderCategoryTree();
                this.populateCategoryFilter();
            }
        } catch (error) {
            console.error('Failed to load categories:', error);
        }
    }

    renderCategoryTree() {
        const treeContainer = document.getElementById('category-tree');
        if (!treeContainer) return;

        const treeHTML = this.buildCategoryTree(this.categories);
        treeContainer.innerHTML = treeHTML;
    }

    buildCategoryTree(categories, parentId = null, level = 0) {
        const children = categories.filter(cat => cat.parent_id === parentId);
        if (children.length === 0) return '';

        return `
            <ul class="category-tree-level level-${level}">
                ${children.map(category => `
                    <li class="category-item" data-category-id="${category.id}">
                        <div class="category-content">
                            <div class="drag-handle">
                                <i class="icon-drag"></i>
                            </div>
                            <div class="category-info">
                                <span class="category-name" data-editable="text" data-content-id="category-${category.id}">
                                    ${category.name}
                                </span>
                                <span class="product-count">(${category.product_count || 0})</span>
                            </div>
                            <div class="category-actions">
                                <button class="btn btn-sm btn-secondary" data-action="addSubcategory" data-category-id="${category.id}">
                                    <i class="icon-plus"></i>
                                </button>
                                <button class="btn btn-sm btn-danger" data-action="deleteCategory" data-category-id="${category.id}">
                                    <i class="icon-trash"></i>
                                </button>
                            </div>
                        </div>
                        ${this.buildCategoryTree(categories, category.id, level + 1)}
                    </li>
                `).join('')}
            </ul>
        `;
    }

    populateCategoryFilter() {
        const categoryFilter = document.getElementById('category-filter');
        if (!categoryFilter) return;

        const options = this.categories.map(category => 
            `<option value="${category.id}">${category.name}</option>`
        ).join('');
        
        categoryFilter.innerHTML = '<option value="">All Categories</option>' + options;
    }

    async loadProducts() {
        try {
            const data = await this.apiCall('/api/admin/products');
            if (data.success) {
                this.products = data.data.products;
                this.renderProducts();
            }
        } catch (error) {
            console.error('Failed to load products:', error);
        }
    }

    renderProducts() {
        const productList = document.getElementById('product-list');
        if (!productList) return;

        if (this.products.length === 0) {
            productList.innerHTML = '<div class="empty-state">No products found</div>';
            return;
        }

        const productsHTML = this.products.map(product => `
            <div class="product-item" data-product-id="${product.id}">
                <div class="product-checkbox">
                    <input type="checkbox" class="product-select" data-product-id="${product.id}">
                </div>
                <div class="drag-handle">
                    <i class="icon-drag"></i>
                </div>
                <div class="product-image">
                    <img src="${product.image_url || '/static/images/placeholder-product.png'}" alt="${product.name}">
                </div>
                <div class="product-info">
                    <div class="product-name" data-editable="text" data-content-id="product-name-${product.id}">
                        ${product.name}
                    </div>
                    <div class="product-sku">SKU: ${product.sku || 'N/A'}</div>
                    <div class="product-category">${this.getCategoryName(product.category_id)}</div>
                    <div class="product-meta">
                        <span class="product-price" data-editable="text" data-content-id="product-price-${product.id}">
                            $${product.price}
                        </span>
                        <span class="product-stock ${product.stock <= 5 ? 'low-stock' : ''}">
                            Stock: ${product.stock}
                        </span>
                        <span class="product-status status-${product.status}">${product.status}</span>
                    </div>
                </div>
                <div class="product-actions">
                    <button class="btn btn-sm btn-secondary" data-action="editProduct" data-product-id="${product.id}">
                        <i class="icon-edit"></i> Edit
                    </button>
                    <button class="btn btn-sm btn-primary" data-action="duplicateProduct" data-product-id="${product.id}">
                        <i class="icon-copy"></i> Duplicate
                    </button>
                    <button class="btn btn-sm btn-danger" data-action="deleteProduct" data-product-id="${product.id}">
                        <i class="icon-trash"></i> Delete
                    </button>
                </div>
            </div>
        `).join('');

        productList.innerHTML = productsHTML;
    }

    getCategoryName(categoryId) {
        const category = this.categories.find(cat => cat.id === categoryId);
        return category ? category.name : 'Uncategorized';
    }

    setupEventListeners() {
        if (!this.container) return;

        // Product selection
        this.container.addEventListener('change', (e) => {
            if (e.target.classList.contains('product-select')) {
                const productId = e.target.getAttribute('data-product-id');
                if (e.target.checked) {
                    this.selectedProducts.add(productId);
                } else {
                    this.selectedProducts.delete(productId);
                }
                this.updateBulkEditButton();
            }
        });

        // Action buttons
        this.container.addEventListener('click', (e) => {
            const action = e.target.getAttribute('data-action');
            const productId = e.target.getAttribute('data-product-id');
            const categoryId = e.target.getAttribute('data-category-id');

            switch (action) {
                case 'addProduct':
                    this.openAddProductModal();
                    break;
                case 'editProduct':
                    this.openEditProductModal(productId);
                    break;
                case 'duplicateProduct':
                    this.duplicateProduct(productId);
                    break;
                case 'deleteProduct':
                    this.deleteProduct(productId);
                    break;
                case 'bulkEdit':
                    this.openBulkEditModal();
                    break;
                case 'importProducts':
                    this.openImportModal();
                    break;
                case 'addSubcategory':
                    this.addSubcategory(categoryId);
                    break;
                case 'deleteCategory':
                    this.deleteCategory(categoryId);
                    break;
            }
        });

        // Search and filters
        const searchInput = document.getElementById('product-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => {
                this.applyFilters();
            }, 300));
        }

        const categoryFilter = document.getElementById('category-filter');
        const statusFilter = document.getElementById('status-filter');
        
        if (categoryFilter) {
            categoryFilter.addEventListener('change', () => this.applyFilters());
        }
        
        if (statusFilter) {
            statusFilter.addEventListener('change', () => this.applyFilters());
        }
    }

    updateBulkEditButton() {
        const bulkEditBtn = document.getElementById('bulk-edit-btn');
        const selectedCount = document.getElementById('selected-count');
        
        if (bulkEditBtn && selectedCount) {
            const count = this.selectedProducts.size;
            selectedCount.textContent = count;
            bulkEditBtn.disabled = count === 0;
        }
    }

    async duplicateProduct(productId) {
        try {
            const data = await this.apiCall(`/api/admin/products/${productId}/duplicate`, {
                method: 'POST'
            });
            
            if (data.success) {
                this.loadProducts();
                this.showNotification('Product duplicated successfully', 'success');
            }
        } catch (error) {
            console.error('Failed to duplicate product:', error);
            this.showNotification('Failed to duplicate product', 'error');
        }
    }

    openAddProductModal() {
        const modal = this.createModal('Add New Product', this.getProductFormHTML());
        this.setupProductFormEvents(modal);
    }

    openEditProductModal(productId) {
        const product = this.products.find(p => p.id == productId);
        if (!product) return;
        
        const modal = this.createModal('Edit Product', this.getProductFormHTML(product));
        this.setupProductFormEvents(modal, product);
    }

    getProductFormHTML(product = null) {
        const isEdit = product !== null;
        return `
            <form id="product-form" class="admin-form">
                <div class="form-row">
                    <div class="form-group">
                        <label for="product-name">Product Name *</label>
                        <input type="text" id="product-name" name="name" required 
                               value="${product ? product.name : ''}" placeholder="Enter product name">
                    </div>
                    <div class="form-group">
                        <label for="product-sku">SKU</label>
                        <input type="text" id="product-sku" name="sku" 
                               value="${product ? product.sku : ''}" placeholder="Product SKU">
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="product-description">Description</label>
                    <textarea id="product-description" name="description" rows="4" 
                              placeholder="Product description">${product ? product.description : ''}</textarea>
                </div>
                
                <div class="form-group">
                    <label for="product-short-description">Short Description</label>
                    <textarea id="product-short-description" name="short_description" rows="2" 
                              placeholder="Brief product description">${product ? product.short_description : ''}</textarea>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="product-price">Price *</label>
                        <input type="number" id="product-price" name="price" step="0.01" required 
                               value="${product ? product.price : ''}" placeholder="0.00">
                    </div>
                    <div class="form-group">
                        <label for="product-compare-price">Compare Price</label>
                        <input type="number" id="product-compare-price" name="compare_price" step="0.01" 
                               value="${product ? product.compare_price || '' : ''}" placeholder="0.00">
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="product-inventory">Inventory Quantity</label>
                        <input type="number" id="product-inventory" name="inventory_quantity" 
                               value="${product ? product.inventory_quantity : '0'}" placeholder="0">
                    </div>
                    <div class="form-group">
                        <label for="product-weight">Weight (kg)</label>
                        <input type="number" id="product-weight" name="weight" step="0.01" 
                               value="${product ? product.weight || '' : ''}" placeholder="0.00">
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="product-categories">Categories</label>
                    <select id="product-categories" name="category_ids" multiple>
                        ${this.getCategoryOptionsHTML(product)}
                    </select>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="product-active" name="is_active" 
                                   ${product ? (product.is_active ? 'checked' : '') : 'checked'}>
                            Active
                        </label>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="product-featured" name="is_featured" 
                                   ${product ? (product.is_featured ? 'checked' : '') : ''}>
                            Featured
                        </label>
                    </div>
                </div>
                
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" data-action="cancel">Cancel</button>
                    <button type="submit" class="btn btn-primary">
                        ${isEdit ? 'Update Product' : 'Create Product'}
                    </button>
                </div>
            </form>
        `;
    }

    getCategoryOptionsHTML(product = null) {
        if (!this.categories) return '';
        
        const selectedCategories = product ? product.categories.map(c => c.id) : [];
        
        return this.categories.map(category => 
            `<option value="${category.id}" ${selectedCategories.includes(category.id) ? 'selected' : ''}>
                ${category.name}
            </option>`
        ).join('');
    }

    setupProductFormEvents(modal, product = null) {
        const form = modal.querySelector('#product-form');
        const isEdit = product !== null;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            const productData = {};
            
            // Convert form data to object
            for (let [key, value] of formData.entries()) {
                if (key === 'category_ids') {
                    if (!productData.category_ids) productData.category_ids = [];
                    productData.category_ids.push(parseInt(value));
                } else if (key === 'is_active' || key === 'is_featured') {
                    productData[key] = true;
                } else {
                    productData[key] = value;
                }
            }
            
            // Handle unchecked checkboxes
            if (!productData.is_active) productData.is_active = false;
            if (!productData.is_featured) productData.is_featured = false;
            
            try {
                const url = isEdit ? `/api/admin/products/${product.id}` : '/api/admin/products';
                const method = isEdit ? 'PUT' : 'POST';
                
                const data = await this.apiCall(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(productData)
                });
                
                if (data.success) {
                    this.closeModal(modal);
                    this.loadProducts();
                    this.showNotification(
                        isEdit ? 'Product updated successfully' : 'Product created successfully', 
                        'success'
                    );
                } else {
                    this.showNotification(data.error || 'Failed to save product', 'error');
                }
            } catch (error) {
                console.error('Failed to save product:', error);
                this.showNotification('Failed to save product', 'error');
            }
        });
        
        // Cancel button
        modal.querySelector('[data-action="cancel"]').addEventListener('click', () => {
            this.closeModal(modal);
        });
    }

    async deleteProduct(productId) {
        if (!confirm('Are you sure you want to delete this product?')) return;
        
        try {
            const data = await this.apiCall(`/api/admin/products/${productId}`, {
                method: 'DELETE'
            });
            
            if (data.success) {
                this.loadProducts();
                this.showNotification('Product deleted successfully', 'success');
            } else {
                this.showNotification(data.error || 'Failed to delete product', 'error');
            }
        } catch (error) {
            console.error('Failed to delete product:', error);
            this.showNotification('Failed to delete product', 'error');
        }
    }

    createModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'admin-modal';
        modal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close modal events
        modal.querySelector('.modal-close').addEventListener('click', () => {
            this.closeModal(modal);
        });
        
        modal.querySelector('.modal-overlay').addEventListener('click', () => {
            this.closeModal(modal);
        });
        
        return modal;
    }

    closeModal(modal) {
        modal.remove();
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    openBulkEditModal() {
        if (this.selectedProducts.size === 0) {
            this.showNotification('Please select products to edit', 'warning');
            return;
        }

        const modal = this.createModal('Bulk Edit Products', this.getBulkEditFormHTML());
        this.setupBulkEditFormEvents(modal);
    }

    getBulkEditFormHTML() {
        return `
            <form id="bulk-edit-form" class="admin-form">
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="bulk-edit-price" name="edit_price">
                        Update Price
                    </label>
                    <input type="number" id="bulk-price" name="price" step="0.01" 
                           placeholder="New price" disabled>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="bulk-edit-status" name="edit_status">
                        Update Status
                    </label>
                    <select id="bulk-status" name="is_active" disabled>
                        <option value="true">Active</option>
                        <option value="false">Inactive</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="bulk-edit-featured" name="edit_featured">
                        Update Featured Status
                    </label>
                    <select id="bulk-featured" name="is_featured" disabled>
                        <option value="true">Featured</option>
                        <option value="false">Not Featured</option>
                    </select>
                </div>
                
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" data-action="cancel">Cancel</button>
                    <button type="submit" class="btn btn-primary">Update Selected Products</button>
                </div>
            </form>
        `;
    }

    setupBulkEditFormEvents(modal) {
        const form = modal.querySelector('#bulk-edit-form');
        
        // Enable/disable inputs based on checkboxes
        const checkboxes = form.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const targetId = e.target.id.replace('bulk-edit-', 'bulk-');
                const targetInput = form.querySelector(`#${targetId}`);
                if (targetInput) {
                    targetInput.disabled = !e.target.checked;
                }
            });
        });
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            const updates = {};
            
            // Only include checked fields
            if (formData.get('edit_price')) updates.price = parseFloat(formData.get('price'));
            if (formData.get('edit_status')) updates.is_active = formData.get('is_status') === 'true';
            if (formData.get('edit_featured')) updates.is_featured = formData.get('is_featured') === 'true';
            
            if (Object.keys(updates).length === 0) {
                this.showNotification('Please select at least one field to update', 'warning');
                return;
            }
            
            try {
                // Update each selected product
                const promises = Array.from(this.selectedProducts).map(productId => 
                    this.apiCall(`/api/admin/products/${productId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(updates)
                    })
                );
                
                const results = await Promise.all(promises);
                const successful = results.filter(r => r.success).length;
                
                this.closeModal(modal);
                this.loadProducts();
                this.selectedProducts.clear();
                this.updateBulkEditButton();
                
                this.showNotification(`${successful} products updated successfully`, 'success');
                
            } catch (error) {
                console.error('Bulk edit failed:', error);
                this.showNotification('Failed to update products', 'error');
            }
        });
        
        // Cancel button
        modal.querySelector('[data-action="cancel"]').addEventListener('click', () => {
            this.closeModal(modal);
        });
    }

    showNotification(message, type) {
        console.log(`${type.toUpperCase()}: ${message}`);
    }
}

// ==================== CONTENT EDITOR COMPONENT ====================

class ContentEditorComponent extends BaseAdminComponent {
    constructor() {
        super('content-editor-container');
        this.contentBlocks = [];
        this.activeEditor = null;
        this.versionHistory = new Map();
    }

    render() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="content-editor">
                <div class="content-editor-header">
                    <h2>Content Management</h2>
                    <div class="content-editor-actions">
                        <button class="btn btn-primary" data-action="addContent">
                            <i class="icon-plus"></i> Add Content Block
                        </button>
                        <button class="btn btn-secondary" data-action="previewChanges">
                            <i class="icon-eye"></i> Preview
                        </button>
                        <button class="btn btn-success" data-action="publishChanges">
                            <i class="icon-check"></i> Publish All
                        </button>
                    </div>
                </div>
                
                <div class="content-editor-toolbar">
                    <div class="toolbar-group">
                        <button class="toolbar-btn" data-action="undo" title="Undo">
                            <i class="icon-undo"></i>
                        </button>
                        <button class="toolbar-btn" data-action="redo" title="Redo">
                            <i class="icon-redo"></i>
                        </button>
                    </div>
                    <div class="toolbar-group">
                        <button class="toolbar-btn" data-action="bold" title="Bold">
                            <i class="icon-bold"></i>
                        </button>
                        <button class="toolbar-btn" data-action="italic" title="Italic">
                            <i class="icon-italic"></i>
                        </button>
                        <button class="toolbar-btn" data-action="underline" title="Underline">
                            <i class="icon-underline"></i>
                        </button>
                    </div>
                    <div class="toolbar-group">
                        <button class="toolbar-btn" data-action="link" title="Insert Link">
                            <i class="icon-link"></i>
                        </button>
                        <button class="toolbar-btn" data-action="image" title="Insert Image">
                            <i class="icon-image"></i>
                        </button>
                    </div>
                </div>
                
                <div class="content-editor-workspace">
                    <div class="content-blocks" id="content-blocks">
                        <!-- Content blocks will be populated here -->
                    </div>
                </div>
                
                <div class="content-editor-sidebar">
                    <div class="sidebar-section">
                        <h3>Version History</h3>
                        <div class="version-list" id="version-list">
                            <!-- Version history will be populated here -->
                        </div>
                    </div>
                    
                    <div class="sidebar-section">
                        <h3>Media Library</h3>
                        <div class="media-library" id="media-library">
                            <!-- Media library will be populated here -->
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.loadContentBlocks();
        this.loadMediaLibrary();
    }

    async loadContentBlocks() {
        try {
            const data = await this.apiCall('/api/admin/content/blocks');
            if (data.success) {
                this.contentBlocks = data.data.blocks;
                this.renderContentBlocks();
            }
        } catch (error) {
            console.error('Failed to load content blocks:', error);
        }
    }

    renderContentBlocks() {
        const blocksContainer = document.getElementById('content-blocks');
        if (!blocksContainer) return;

        const blocksHTML = this.contentBlocks.map(block => `
            <div class="content-block" data-block-id="${block.id}" data-block-type="${block.type}">
                <div class="content-block-header">
                    <div class="drag-handle">
                        <i class="icon-drag"></i>
                    </div>
                    <div class="block-info">
                        <span class="block-title">${block.title}</span>
                        <span class="block-type">${block.type}</span>
                    </div>
                    <div class="block-actions">
                        <button class="btn btn-sm btn-secondary" data-action="editBlock" data-block-id="${block.id}">
                            <i class="icon-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-primary" data-action="duplicateBlock" data-block-id="${block.id}">
                            <i class="icon-copy"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" data-action="deleteBlock" data-block-id="${block.id}">
                            <i class="icon-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="content-block-body">
                    ${this.renderBlockContent(block)}
                </div>
            </div>
        `).join('');

        blocksContainer.innerHTML = blocksHTML;
    }

    renderBlockContent(block) {
        switch (block.type) {
            case 'text':
                return `
                    <div class="rich-text-editor" data-editable="rich-text" data-content-id="${block.id}">
                        ${block.content}
                    </div>
                `;
            case 'image':
                return `
                    <div class="image-block">
                        <img src="${block.content.url}" alt="${block.content.alt}" data-editable="image" data-content-id="${block.id}">
                        <div class="image-caption" data-editable="text" data-content-id="${block.id}-caption">
                            ${block.content.caption || ''}
                        </div>
                    </div>
                `;
            case 'gallery':
                return `
                    <div class="gallery-block">
                        <div class="gallery-images">
                            ${block.content.images.map(img => `
                                <img src="${img.url}" alt="${img.alt}" data-editable="image" data-content-id="${img.id}">
                            `).join('')}
                        </div>
                        <button class="btn btn-secondary add-image-btn" data-action="addGalleryImage" data-block-id="${block.id}">
                            <i class="icon-plus"></i> Add Image
                        </button>
                    </div>
                `;
            case 'video':
                return `
                    <div class="video-block">
                        <video controls data-editable="video" data-content-id="${block.id}">
                            <source src="${block.content.url}" type="video/mp4">
                        </video>
                        <div class="video-caption" data-editable="text" data-content-id="${block.id}-caption">
                            ${block.content.caption || ''}
                        </div>
                    </div>
                `;
            default:
                return `<div class="unknown-block-type">Unknown block type: ${block.type}</div>`;
        }
    }

    async loadMediaLibrary() {
        try {
            const data = await this.apiCall('/api/admin/content/media');
            if (data.success) {
                this.renderMediaLibrary(data.data.media);
            }
        } catch (error) {
            console.error('Failed to load media library:', error);
        }
    }

    renderMediaLibrary(media) {
        const mediaLibrary = document.getElementById('media-library');
        if (!mediaLibrary) return;

        const mediaHTML = media.map(item => `
            <div class="media-item" data-media-id="${item.id}">
                <div class="media-thumbnail">
                    ${item.type === 'image' ? 
                        `<img src="${item.thumbnail_url}" alt="${item.name}">` :
                        `<div class="media-icon"><i class="icon-${item.type}"></i></div>`
                    }
                </div>
                <div class="media-info">
                    <div class="media-name">${item.name}</div>
                    <div class="media-size">${this.formatFileSize(item.size)}</div>
                </div>
                <div class="media-actions">
                    <button class="btn btn-sm btn-primary" data-action="insertMedia" data-media-id="${item.id}">
                        <i class="icon-plus"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" data-action="deleteMedia" data-media-id="${item.id}">
                        <i class="icon-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');

        mediaLibrary.innerHTML = mediaHTML;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    setupEventListeners() {
        if (!this.container) return;

        // Toolbar actions
        this.container.addEventListener('click', (e) => {
            const action = e.target.getAttribute('data-action');
            const blockId = e.target.getAttribute('data-block-id');
            const mediaId = e.target.getAttribute('data-media-id');

            switch (action) {
                case 'addContent':
                    this.openAddContentModal();
                    break;
                case 'previewChanges':
                    this.previewChanges();
                    break;
                case 'publishChanges':
                    this.publishAllChanges();
                    break;
                case 'editBlock':
                    this.editBlock(blockId);
                    break;
                case 'duplicateBlock':
                    this.duplicateBlock(blockId);
                    break;
                case 'deleteBlock':
                    this.deleteBlock(blockId);
                    break;
                case 'insertMedia':
                    this.insertMedia(mediaId);
                    break;
                case 'deleteMedia':
                    this.deleteMedia(mediaId);
                    break;
                // Toolbar formatting actions
                case 'bold':
                case 'italic':
                case 'underline':
                    this.applyFormatting(action);
                    break;
                case 'link':
                    this.insertLink();
                    break;
                case 'image':
                    this.insertImage();
                    break;
                case 'undo':
                    this.undo();
                    break;
                case 'redo':
                    this.redo();
                    break;
            }
        });
    }

    applyFormatting(command) {
        if (this.activeEditor) {
            document.execCommand(command, false, null);
            this.saveContentVersion();
        }
    }

    insertLink() {
        const url = prompt('Enter URL:');
        if (url && this.activeEditor) {
            document.execCommand('createLink', false, url);
            this.saveContentVersion();
        }
    }

    insertImage() {
        const url = prompt('Enter image URL:');
        if (url && this.activeEditor) {
            document.execCommand('insertImage', false, url);
            this.saveContentVersion();
        }
    }

    saveContentVersion() {
        if (this.activeEditor) {
            const blockId = this.activeEditor.getAttribute('data-content-id');
            const content = this.activeEditor.innerHTML;
            
            if (!this.versionHistory.has(blockId)) {
                this.versionHistory.set(blockId, []);
            }
            
            this.versionHistory.get(blockId).push({
                content: content,
                timestamp: new Date(),
                id: Date.now()
            });
        }
    }

    undo() {
        if (this.activeEditor) {
            document.execCommand('undo', false, null);
        }
    }

    redo() {
        if (this.activeEditor) {
            document.execCommand('redo', false, null);
        }
    }

    async publishAllChanges() {
        try {
            const changes = Array.from(this.versionHistory.entries()).map(([blockId, versions]) => ({
                block_id: blockId,
                content: versions[versions.length - 1].content
            }));

            const data = await this.apiCall('/api/admin/content/publish', {
                method: 'POST',
                body: JSON.stringify({ changes })
            });

            if (data.success) {
                this.showNotification('All changes published successfully', 'success');
                this.versionHistory.clear();
            }
        } catch (error) {
            console.error('Failed to publish changes:', error);
            this.showNotification('Failed to publish changes', 'error');
        }
    }

    showNotification(message, type) {
        console.log(`${type.toUpperCase()}: ${message}`);
    }
}

// ==================== THEME CUSTOMIZER COMPONENT ====================

class ThemeCustomizerComponent extends BaseAdminComponent {
    constructor() {
        super('theme-customizer-container');
        this.currentTheme = {};
        this.previewHandler = null;
        this.colorPickers = new Map();
    }

    render() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="theme-customizer">
                <div class="theme-customizer-header">
                    <h2>Theme Customization</h2>
                    <div class="theme-actions">
                        <button class="btn btn-info" data-action="createTheme">
                            <i class="icon-plus"></i> Create Theme
                        </button>
                        <button class="btn btn-secondary" data-action="resetTheme">
                            <i class="icon-refresh"></i> Reset
                        </button>
                        <button class="btn btn-primary" data-action="saveTheme">
                            <i class="icon-save"></i> Save Theme
                        </button>
                        <button class="btn btn-success" data-action="publishTheme">
                            <i class="icon-check"></i> Publish
                        </button>
                    </div>
                </div>
                
                <div class="theme-customizer-content">
                    <div class="theme-controls">
                        <div class="control-section">
                            <h3>Colors</h3>
                            <div class="color-controls" id="color-controls">
                                <!-- Color controls will be populated here -->
                            </div>
                        </div>
                        
                        <div class="control-section">
                            <h3>Typography</h3>
                            <div class="typography-controls" id="typography-controls">
                                <!-- Typography controls will be populated here -->
                            </div>
                        </div>
                        
                        <div class="control-section">
                            <h3>Layout</h3>
                            <div class="layout-controls" id="layout-controls">
                                <!-- Layout controls will be populated here -->
                            </div>
                        </div>
                        
                        <div class="control-section">
                            <h3>Components</h3>
                            <div class="component-controls" id="component-controls">
                                <!-- Component controls will be populated here -->
                            </div>
                        </div>
                    </div>
                    
                    <div class="theme-preview">
                        <div class="preview-header">
                            <h3>Live Preview</h3>
                            <div class="preview-controls">
                                <button class="preview-device active" data-device="desktop">
                                    <i class="icon-monitor"></i>
                                </button>
                                <button class="preview-device" data-device="tablet">
                                    <i class="icon-tablet"></i>
                                </button>
                                <button class="preview-device" data-device="mobile">
                                    <i class="icon-smartphone"></i>
                                </button>
                            </div>
                        </div>
                        <div class="preview-frame" id="preview-frame">
                            <iframe id="preview-iframe" src="/preview" frameborder="0"></iframe>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.loadCurrentTheme();
    }

    async loadCurrentTheme() {
        try {
            const data = await this.apiCall('/api/admin/theme/current');
            if (data.success) {
                this.currentTheme = data.data.theme;
                this.renderThemeControls();
            }
        } catch (error) {
            console.error('Failed to load current theme:', error);
        }
    }

    renderThemeControls() {
        this.renderColorControls();
        this.renderTypographyControls();
        this.renderLayoutControls();
        this.renderComponentControls();
    }

    renderColorControls() {
        const colorControls = document.getElementById('color-controls');
        if (!colorControls) return;

        const colors = this.currentTheme.colors || {};
        const colorHTML = Object.entries(colors).map(([key, value]) => `
            <div class="control-group">
                <label for="color-${key}">${this.formatLabel(key)}</label>
                <div class="color-input-group">
                    <input type="color" id="color-${key}" class="color-picker" data-property="colors.${key}" value="${value}">
                    <input type="text" class="color-text" data-property="colors.${key}" value="${value}">
                </div>
            </div>
        `).join('');

        colorControls.innerHTML = colorHTML;
    }

    renderTypographyControls() {
        const typographyControls = document.getElementById('typography-controls');
        if (!typographyControls) return;

        const typography = this.currentTheme.typography || {};
        const typographyHTML = `
            <div class="control-group">
                <label for="font-family">Font Family</label>
                <select id="font-family" class="form-control" data-property="typography.fontFamily">
                    <option value="Arial, sans-serif" ${typography.fontFamily === 'Arial, sans-serif' ? 'selected' : ''}>Arial</option>
                    <option value="Georgia, serif" ${typography.fontFamily === 'Georgia, serif' ? 'selected' : ''}>Georgia</option>
                    <option value="'Times New Roman', serif" ${typography.fontFamily === "'Times New Roman', serif" ? 'selected' : ''}>Times New Roman</option>
                    <option value="'Helvetica Neue', sans-serif" ${typography.fontFamily === "'Helvetica Neue', sans-serif" ? 'selected' : ''}>Helvetica Neue</option>
                </select>
            </div>
            
            <div class="control-group">
                <label for="font-size-base">Base Font Size</label>
                <div class="range-input-group">
                    <input type="range" id="font-size-base" class="range-input" data-property="typography.baseFontSize" 
                           min="12" max="20" value="${typography.baseFontSize || 16}">
                    <span class="range-value">${typography.baseFontSize || 16}px</span>
                </div>
            </div>
            
            <div class="control-group">
                <label for="line-height">Line Height</label>
                <div class="range-input-group">
                    <input type="range" id="line-height" class="range-input" data-property="typography.lineHeight" 
                           min="1" max="2" step="0.1" value="${typography.lineHeight || 1.5}">
                    <span class="range-value">${typography.lineHeight || 1.5}</span>
                </div>
            </div>
        `;

        typographyControls.innerHTML = typographyHTML;
    }

    renderLayoutControls() {
        const layoutControls = document.getElementById('layout-controls');
        if (!layoutControls) return;

        const layout = this.currentTheme.layout || {};
        const layoutHTML = `
            <div class="control-group">
                <label for="container-width">Container Width</label>
                <div class="range-input-group">
                    <input type="range" id="container-width" class="range-input" data-property="layout.containerWidth" 
                           min="1000" max="1400" value="${layout.containerWidth || 1200}">
                    <span class="range-value">${layout.containerWidth || 1200}px</span>
                </div>
            </div>
            
            <div class="control-group">
                <label for="border-radius">Border Radius</label>
                <div class="range-input-group">
                    <input type="range" id="border-radius" class="range-input" data-property="layout.borderRadius" 
                           min="0" max="20" value="${layout.borderRadius || 4}">
                    <span class="range-value">${layout.borderRadius || 4}px</span>
                </div>
            </div>
            
            <div class="control-group">
                <label for="spacing-unit">Spacing Unit</label>
                <div class="range-input-group">
                    <input type="range" id="spacing-unit" class="range-input" data-property="layout.spacingUnit" 
                           min="4" max="16" value="${layout.spacingUnit || 8}">
                    <span class="range-value">${layout.spacingUnit || 8}px</span>
                </div>
            </div>
        `;

        layoutControls.innerHTML = layoutHTML;
    }

    renderComponentControls() {
        const componentControls = document.getElementById('component-controls');
        if (!componentControls) return;

        const components = this.currentTheme.components || {};
        const componentHTML = `
            <div class="control-group">
                <label for="button-style">Button Style</label>
                <select id="button-style" class="form-control" data-property="components.buttonStyle">
                    <option value="rounded" ${components.buttonStyle === 'rounded' ? 'selected' : ''}>Rounded</option>
                    <option value="square" ${components.buttonStyle === 'square' ? 'selected' : ''}>Square</option>
                    <option value="pill" ${components.buttonStyle === 'pill' ? 'selected' : ''}>Pill</option>
                </select>
            </div>
            
            <div class="control-group">
                <label for="card-shadow">Card Shadow</label>
                <select id="card-shadow" class="form-control" data-property="components.cardShadow">
                    <option value="none" ${components.cardShadow === 'none' ? 'selected' : ''}>None</option>
                    <option value="subtle" ${components.cardShadow === 'subtle' ? 'selected' : ''}>Subtle</option>
                    <option value="medium" ${components.cardShadow === 'medium' ? 'selected' : ''}>Medium</option>
                    <option value="strong" ${components.cardShadow === 'strong' ? 'selected' : ''}>Strong</option>
                </select>
            </div>
        `;

        componentControls.innerHTML = componentHTML;
    }

    setupEventListeners() {
        if (!this.container) return;

        // Theme control changes
        this.container.addEventListener('input', (e) => {
            if (e.target.hasAttribute('data-property')) {
                this.handleThemeChange(e.target);
            }
        });

        this.container.addEventListener('change', (e) => {
            if (e.target.hasAttribute('data-property')) {
                this.handleThemeChange(e.target);
            }
        });

        // Preview device switching
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('preview-device')) {
                this.switchPreviewDevice(e.target.getAttribute('data-device'));
            }

            const action = e.target.getAttribute('data-action');
            switch (action) {
                case 'resetTheme':
                    this.resetTheme();
                    break;
                case 'saveTheme':
                    this.saveTheme();
                    break;
                case 'publishTheme':
                    this.publishTheme();
                    break;
            }
        });
    }

    handleThemeChange(input) {
        const property = input.getAttribute('data-property');
        const value = input.type === 'range' ? parseFloat(input.value) : input.value;
        
        this.setNestedProperty(this.currentTheme, property, value);
        
        // Update range value display
        if (input.type === 'range') {
            const valueDisplay = input.parentNode.querySelector('.range-value');
            if (valueDisplay) {
                valueDisplay.textContent = value + (property.includes('Size') || property.includes('Width') || property.includes('Radius') || property.includes('Unit') ? 'px' : '');
            }
        }
        
        // Update preview
        if (this.previewHandler) {
            this.previewHandler.updatePreview(this.currentTheme);
        }
    }

    setNestedProperty(obj, path, value) {
        const keys = path.split('.');
        let current = obj;
        
        for (let i = 0; i < keys.length - 1; i++) {
            if (!(keys[i] in current)) {
                current[keys[i]] = {};
            }
            current = current[keys[i]];
        }
        
        current[keys[keys.length - 1]] = value;
    }

    switchPreviewDevice(device) {
        const previewFrame = document.getElementById('preview-frame');
        const deviceButtons = document.querySelectorAll('.preview-device');
        
        deviceButtons.forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-device="${device}"]`).classList.add('active');
        
        previewFrame.className = `preview-frame device-${device}`;
    }

    setPreviewHandler(handler) {
        this.previewHandler = handler;
    }

    formatLabel(key) {
        return key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
    }

    setupEventListeners() {
        if (!this.container) return;

        // Theme action buttons
        this.container.addEventListener('click', (e) => {
            const action = e.target.getAttribute('data-action');
            
            switch (action) {
                case 'createTheme':
                    this.openCreateThemeModal();
                    break;
                case 'resetTheme':
                    this.resetTheme();
                    break;
                case 'saveTheme':
                    this.saveTheme();
                    break;
                case 'publishTheme':
                    this.publishTheme();
                    break;
            }
        });

        // Device preview buttons
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('preview-device')) {
                const device = e.target.getAttribute('data-device');
                this.switchPreviewDevice(device);
            }
        });

        // Theme control inputs
        this.container.addEventListener('input', (e) => {
            if (e.target.hasAttribute('data-property')) {
                const property = e.target.getAttribute('data-property');
                const value = e.target.value;
                this.updateThemeProperty(property, value);
            }
        });

        // Range input updates
        this.container.addEventListener('input', (e) => {
            if (e.target.classList.contains('range-input')) {
                const valueSpan = e.target.parentNode.querySelector('.range-value');
                if (valueSpan) {
                    const unit = e.target.id.includes('font') ? 'px' : 
                                e.target.id.includes('width') ? 'px' : 
                                e.target.id.includes('radius') ? 'px' : '';
                    valueSpan.textContent = e.target.value + unit;
                }
            }
        });
    }

    openCreateThemeModal() {
        const modal = this.createModal('Create New Theme', this.getCreateThemeFormHTML());
        this.setupCreateThemeFormEvents(modal);
    }

    getCreateThemeFormHTML() {
        return `
            <form id="create-theme-form" class="admin-form">
                <div class="form-group">
                    <label for="theme-name">Theme Name *</label>
                    <input type="text" id="theme-name" name="name" required 
                           placeholder="Enter theme name">
                </div>
                
                <div class="form-group">
                    <label for="base-theme">Base Theme</label>
                    <select id="base-theme" name="base_theme" class="form-control">
                        <option value="default">Default Theme</option>
                        <option value="dark">Dark Theme</option>
                        <option value="minimal">Minimal Theme</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="theme-description">Description</label>
                    <textarea id="theme-description" name="description" rows="3" 
                              placeholder="Brief description of the theme"></textarea>
                </div>
                
                <div class="form-section">
                    <h4>Quick Customization</h4>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="primary-color">Primary Color</label>
                            <input type="color" id="primary-color" name="primary_color" value="#ff4747">
                        </div>
                        <div class="form-group">
                            <label for="secondary-color">Secondary Color</label>
                            <input type="color" id="secondary-color" name="secondary_color" value="#ff6b35">
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="background-color">Background Color</label>
                            <input type="color" id="background-color" name="background_color" value="#ffffff">
                        </div>
                        <div class="form-group">
                            <label for="text-color">Text Color</label>
                            <input type="color" id="text-color" name="text_color" value="#333333">
                        </div>
                    </div>
                </div>
                
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" data-action="cancel">Cancel</button>
                    <button type="submit" class="btn btn-primary">Create Theme</button>
                </div>
            </form>
        `;
    }

    setupCreateThemeFormEvents(modal) {
        const form = modal.querySelector('#create-theme-form');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            const themeData = {
                name: formData.get('name'),
                base_theme: formData.get('base_theme'),
                settings: {
                    primary_color: formData.get('primary_color'),
                    secondary_color: formData.get('secondary_color'),
                    background_color: formData.get('background_color'),
                    text_color: formData.get('text_color')
                }
            };
            
            try {
                const data = await this.apiCall('/api/admin/theme/create', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(themeData)
                });
                
                if (data.success) {
                    this.closeModal(modal);
                    this.showNotification('Theme created successfully', 'success');
                    this.loadCurrentTheme(); // Refresh the theme list
                } else {
                    this.showNotification(data.error || 'Failed to create theme', 'error');
                }
            } catch (error) {
                console.error('Failed to create theme:', error);
                this.showNotification('Failed to create theme', 'error');
            }
        });
        
        // Cancel button
        modal.querySelector('[data-action="cancel"]').addEventListener('click', () => {
            this.closeModal(modal);
        });
    }

    updateThemeProperty(property, value) {
        const keys = property.split('.');
        let current = this.currentTheme;
        
        // Navigate to the nested property
        for (let i = 0; i < keys.length - 1; i++) {
            if (!current[keys[i]]) {
                current[keys[i]] = {};
            }
            current = current[keys[i]];
        }
        
        // Set the value
        current[keys[keys.length - 1]] = value;
        
        // Apply the change to preview
        this.applyThemeChange(property, value);
    }

    applyThemeChange(property, value) {
        // Apply the change to the preview iframe
        const iframe = document.getElementById('preview-iframe');
        if (iframe && iframe.contentWindow) {
            try {
                const cssProperty = property.replace(/\./g, '-').replace(/([A-Z])/g, '-$1').toLowerCase();
                iframe.contentWindow.document.documentElement.style.setProperty(`--${cssProperty}`, value);
            } catch (error) {
                console.error('Failed to apply theme change to preview:', error);
            }
        }
    }

    resetTheme() {
        if (confirm('Are you sure you want to reset all theme changes?')) {
            this.loadCurrentTheme();
        }
    }

    createModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'admin-modal';
        modal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close modal events
        modal.querySelector('.modal-close').addEventListener('click', () => {
            this.closeModal(modal);
        });
        
        modal.querySelector('.modal-overlay').addEventListener('click', () => {
            this.closeModal(modal);
        });
        
        return modal;
    }

    closeModal(modal) {
        modal.remove();
    }

    async publishTheme() {
        if (confirm('Are you sure you want to publish this theme? This will make it live on your site.')) {
            try {
                const data = await this.apiCall('/api/admin/theme/publish', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ theme: this.currentTheme })
                });
                
                if (data.success) {
                    this.showNotification('Theme published successfully', 'success');
                } else {
                    this.showNotification(data.error || 'Failed to publish theme', 'error');
                }
            } catch (error) {
                console.error('Failed to publish theme:', error);
                this.showNotification('Failed to publish theme', 'error');
            }
        }
    }

    async saveTheme() {
        try {
            const data = await this.apiCall('/api/admin/theme/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ theme: this.currentTheme })
            });

            if (data.success) {
                this.showNotification('Theme saved successfully', 'success');
            } else {
                this.showNotification(data.error || 'Failed to save theme', 'error');
            }
        } catch (error) {
            console.error('Failed to save theme:', error);
            this.showNotification('Failed to save theme', 'error');
        }
    }

    showNotification(message, type) {
        console.log(`${type.toUpperCase()}: ${message}`);
        // You can implement a proper notification system here
    }

    async publishTheme() {
        try {
            const data = await this.apiCall('/api/admin/theme/publish', {
                method: 'POST',
                body: JSON.stringify({ theme: this.currentTheme })
            });

            if (data.success) {
                this.showNotification('Theme published successfully', 'success');
            }
        } catch (error) {
            console.error('Failed to publish theme:', error);
            this.showNotification('Failed to publish theme', 'error');
        }
    }

    async resetTheme() {
        if (!confirm('Are you sure you want to reset the theme to defaults?')) return;

        try {
            const data = await this.apiCall('/api/admin/theme/reset', {
                method: 'POST'
            });

            if (data.success) {
                this.currentTheme = data.data.theme;
                this.renderThemeControls();
                if (this.previewHandler) {
                    this.previewHandler.updatePreview(this.currentTheme);
                }
                this.showNotification('Theme reset to defaults', 'success');
            }
        } catch (error) {
            console.error('Failed to reset theme:', error);
            this.showNotification('Failed to reset theme', 'error');
        }
    }

    showNotification(message, type) {
        console.log(`${type.toUpperCase()}: ${message}`);
    }
}

// Export components for browser use
if (typeof window !== 'undefined') {
    window.ProductManagerComponent = ProductManagerComponent;
    window.ContentEditorComponent = ContentEditorComponent;
    window.ThemeCustomizerComponent = ThemeCustomizerComponent;
}

// Export additional components for Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ProductManagerComponent,
        ContentEditorComponent,
        ThemeCustomizerComponent
    };
}