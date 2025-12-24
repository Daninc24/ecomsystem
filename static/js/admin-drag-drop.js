/**
 * Drag and Drop Functionality for Admin Interface
 * Provides comprehensive drag-and-drop capabilities for various admin components
 */

// ==================== BASE DRAG DROP MANAGER ====================

class DragDropManager {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            itemSelector: '.draggable-item',
            handleSelector: '.drag-handle',
            placeholderClass: 'drag-placeholder',
            draggingClass: 'dragging',
            dragOverClass: 'drag-over',
            onDrop: null,
            onDragStart: null,
            onDragEnd: null,
            ...options
        };
        
        this.draggedElement = null;
        this.placeholder = null;
        this.isMobile = false;
        
        this.init();
    }

    init() {
        if (!this.container) return;
        
        this.setupEventListeners();
        this.createPlaceholder();
    }

    setupEventListeners() {
        // Mouse events for desktop
        this.container.addEventListener('mousedown', this.handleMouseDown.bind(this));
        document.addEventListener('mousemove', this.handleMouseMove.bind(this));
        document.addEventListener('mouseup', this.handleMouseUp.bind(this));
        
        // Touch events for mobile
        this.container.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
        document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
        document.addEventListener('touchend', this.handleTouchEnd.bind(this));
        
        // Prevent default drag behavior on images and other elements
        this.container.addEventListener('dragstart', (e) => e.preventDefault());
    }

    createPlaceholder() {
        this.placeholder = document.createElement('div');
        this.placeholder.className = this.options.placeholderClass;
        this.placeholder.innerHTML = '<div class="placeholder-content">Drop here</div>';
    }

    handleMouseDown(e) {
        if (this.isMobile) return;
        this.handleDragStart(e, e.clientX, e.clientY);
    }

    handleTouchStart(e) {
        if (e.touches.length !== 1) return;
        const touch = e.touches[0];
        this.handleDragStart(e, touch.clientX, touch.clientY);
    }

    handleDragStart(e, clientX, clientY) {
        const target = e.target;
        const handle = target.closest(this.options.handleSelector);
        const item = target.closest(this.options.itemSelector);
        
        if (!handle || !item || !this.container.contains(item)) return;
        
        e.preventDefault();
        
        this.draggedElement = item;
        this.startX = clientX;
        this.startY = clientY;
        this.isDragging = false;
        
        // Add dragging class after a small delay to prevent accidental drags
        this.dragStartTimeout = setTimeout(() => {
            if (this.draggedElement) {
                this.startDrag();
            }
        }, 100);
    }

    startDrag() {
        if (!this.draggedElement) return;
        
        this.isDragging = true;
        this.draggedElement.classList.add(this.options.draggingClass);
        
        // Create drag ghost
        this.createDragGhost();
        
        // Insert placeholder
        this.insertPlaceholder();
        
        // Callback
        if (this.options.onDragStart) {
            this.options.onDragStart(this.draggedElement);
        }
        
        document.body.style.userSelect = 'none';
    }

    createDragGhost() {
        this.dragGhost = this.draggedElement.cloneNode(true);
        this.dragGhost.className = this.draggedElement.className + ' drag-ghost';
        this.dragGhost.style.position = 'fixed';
        this.dragGhost.style.pointerEvents = 'none';
        this.dragGhost.style.zIndex = '10000';
        this.dragGhost.style.opacity = '0.8';
        this.dragGhost.style.transform = 'rotate(5deg)';
        
        document.body.appendChild(this.dragGhost);
    }

    insertPlaceholder() {
        const rect = this.draggedElement.getBoundingClientRect();
        this.placeholder.style.height = rect.height + 'px';
        this.draggedElement.parentNode.insertBefore(this.placeholder, this.draggedElement);
        this.draggedElement.style.display = 'none';
    }

    handleMouseMove(e) {
        if (this.isMobile) return;
        this.handleDragMove(e, e.clientX, e.clientY);
    }

    handleTouchMove(e) {
        if (e.touches.length !== 1) return;
        const touch = e.touches[0];
        this.handleDragMove(e, touch.clientX, touch.clientY);
    }

    handleDragMove(e, clientX, clientY) {
        if (!this.draggedElement) return;
        
        const deltaX = clientX - this.startX;
        const deltaY = clientY - this.startY;
        
        // Start dragging if moved enough
        if (!this.isDragging && (Math.abs(deltaX) > 5 || Math.abs(deltaY) > 5)) {
            this.startDrag();
        }
        
        if (!this.isDragging) return;
        
        e.preventDefault();
        
        // Update ghost position
        if (this.dragGhost) {
            this.dragGhost.style.left = clientX - 20 + 'px';
            this.dragGhost.style.top = clientY - 20 + 'px';
        }
        
        // Find drop target
        const elementBelow = document.elementFromPoint(clientX, clientY);
        const dropTarget = this.findDropTarget(elementBelow);
        
        if (dropTarget && dropTarget !== this.placeholder) {
            this.updatePlaceholderPosition(dropTarget, clientY);
        }
    }

    findDropTarget(element) {
        if (!element) return null;
        
        const item = element.closest(this.options.itemSelector);
        if (item && this.container.contains(item) && item !== this.draggedElement) {
            return item;
        }
        
        return null;
    }

    updatePlaceholderPosition(dropTarget, clientY) {
        const rect = dropTarget.getBoundingClientRect();
        const midpoint = rect.top + rect.height / 2;
        
        if (clientY < midpoint) {
            // Insert before
            dropTarget.parentNode.insertBefore(this.placeholder, dropTarget);
        } else {
            // Insert after
            dropTarget.parentNode.insertBefore(this.placeholder, dropTarget.nextSibling);
        }
    }

    handleMouseUp(e) {
        if (this.isMobile) return;
        this.handleDragEnd();
    }

    handleTouchEnd(e) {
        this.handleDragEnd();
    }

    handleDragEnd() {
        if (this.dragStartTimeout) {
            clearTimeout(this.dragStartTimeout);
            this.dragStartTimeout = null;
        }
        
        if (!this.draggedElement) return;
        
        const wasActuallyDragging = this.isDragging;
        
        // Clean up
        this.draggedElement.classList.remove(this.options.draggingClass);
        this.draggedElement.style.display = '';
        
        if (this.dragGhost) {
            document.body.removeChild(this.dragGhost);
            this.dragGhost = null;
        }
        
        document.body.style.userSelect = '';
        
        if (wasActuallyDragging) {
            // Complete the drop
            this.completeDrop();
        }
        
        // Remove placeholder
        if (this.placeholder.parentNode) {
            this.placeholder.parentNode.removeChild(this.placeholder);
        }
        
        // Callback
        if (this.options.onDragEnd) {
            this.options.onDragEnd(this.draggedElement);
        }
        
        this.draggedElement = null;
        this.isDragging = false;
    }

    completeDrop() {
        if (!this.placeholder.parentNode) return;
        
        const fromIndex = this.getElementIndex(this.draggedElement);
        
        // Insert dragged element at placeholder position
        this.placeholder.parentNode.insertBefore(this.draggedElement, this.placeholder);
        
        const toIndex = this.getElementIndex(this.draggedElement);
        
        // Callback with drop information
        if (this.options.onDrop && fromIndex !== toIndex) {
            const itemId = this.draggedElement.getAttribute('data-item-id') || 
                          this.draggedElement.getAttribute('data-product-id') ||
                          this.draggedElement.getAttribute('data-block-id') ||
                          this.draggedElement.id;
            
            this.options.onDrop(fromIndex, toIndex, itemId);
        }
    }

    getElementIndex(element) {
        const siblings = Array.from(element.parentNode.children).filter(child => 
            child.matches(this.options.itemSelector) && child !== this.placeholder
        );
        return siblings.indexOf(element);
    }

    setMobileMode(isMobile) {
        this.isMobile = isMobile;
    }

    destroy() {
        // Remove event listeners and clean up
        if (this.dragGhost && this.dragGhost.parentNode) {
            this.dragGhost.parentNode.removeChild(this.dragGhost);
        }
        
        if (this.placeholder && this.placeholder.parentNode) {
            this.placeholder.parentNode.removeChild(this.placeholder);
        }
        
        if (this.dragStartTimeout) {
            clearTimeout(this.dragStartTimeout);
        }
    }
}

// ==================== TREE DRAG DROP MANAGER ====================

class TreeDragDropManager extends DragDropManager {
    constructor(container, options = {}) {
        super(container, {
            ...options,
            itemSelector: '.tree-item',
            handleSelector: '.tree-drag-handle'
        });
        
        this.expandedNodes = new Set();
        this.dropIndicator = null;
    }

    init() {
        super.init();
        this.createDropIndicator();
    }

    createDropIndicator() {
        this.dropIndicator = document.createElement('div');
        this.dropIndicator.className = 'tree-drop-indicator';
    }

    handleDragMove(e, clientX, clientY) {
        if (!this.isDragging) {
            super.handleDragMove(e, clientX, clientY);
            return;
        }
        
        e.preventDefault();
        
        // Update ghost position
        if (this.dragGhost) {
            this.dragGhost.style.left = clientX - 20 + 'px';
            this.dragGhost.style.top = clientY - 20 + 'px';
        }
        
        // Find drop target for tree
        const elementBelow = document.elementFromPoint(clientX, clientY);
        const dropTarget = this.findTreeDropTarget(elementBelow, clientY);
        
        this.updateTreeDropIndicator(dropTarget);
    }

    findTreeDropTarget(element, clientY) {
        if (!element) return null;
        
        const treeItem = element.closest('.tree-item');
        if (!treeItem || !this.container.contains(treeItem) || treeItem === this.draggedElement) {
            return null;
        }
        
        const rect = treeItem.getBoundingClientRect();
        const third = rect.height / 3;
        
        let position = 'middle';
        if (clientY < rect.top + third) {
            position = 'before';
        } else if (clientY > rect.bottom - third) {
            position = 'after';
        }
        
        return {
            element: treeItem,
            position: position,
            rect: rect
        };
    }

    updateTreeDropIndicator(dropTarget) {
        // Remove existing indicator
        if (this.dropIndicator.parentNode) {
            this.dropIndicator.parentNode.removeChild(this.dropIndicator);
        }
        
        if (!dropTarget) return;
        
        const { element, position, rect } = dropTarget;
        
        if (position === 'before') {
            element.parentNode.insertBefore(this.dropIndicator, element);
        } else if (position === 'after') {
            element.parentNode.insertBefore(this.dropIndicator, element.nextSibling);
        } else {
            // Middle - would become child
            const childContainer = element.querySelector('.tree-children');
            if (childContainer) {
                childContainer.appendChild(this.dropIndicator);
            }
        }
        
        this.currentDropTarget = dropTarget;
    }

    completeDrop() {
        if (!this.currentDropTarget) return;
        
        const { element, position } = this.currentDropTarget;
        const fromPath = this.getTreePath(this.draggedElement);
        let toPath;
        
        if (position === 'before') {
            element.parentNode.insertBefore(this.draggedElement, element);
            toPath = this.getTreePath(this.draggedElement);
        } else if (position === 'after') {
            element.parentNode.insertBefore(this.draggedElement, element.nextSibling);
            toPath = this.getTreePath(this.draggedElement);
        } else {
            // Become child
            let childContainer = element.querySelector('.tree-children');
            if (!childContainer) {
                childContainer = document.createElement('div');
                childContainer.className = 'tree-children';
                element.appendChild(childContainer);
            }
            childContainer.appendChild(this.draggedElement);
            toPath = this.getTreePath(this.draggedElement);
        }
        
        // Callback with tree-specific information
        if (this.options.onDrop && fromPath !== toPath) {
            const itemId = this.draggedElement.getAttribute('data-category-id') || 
                          this.draggedElement.getAttribute('data-item-id') ||
                          this.draggedElement.id;
            
            this.options.onDrop(fromPath, toPath, itemId);
        }
        
        this.currentDropTarget = null;
    }

    getTreePath(element) {
        const path = [];
        let current = element;
        
        while (current && this.container.contains(current)) {
            const id = current.getAttribute('data-category-id') || 
                      current.getAttribute('data-item-id') ||
                      current.id;
            if (id) {
                path.unshift(id);
            }
            
            current = current.parentNode.closest('.tree-item');
        }
        
        return path.join('/');
    }

    handleDragEnd() {
        super.handleDragEnd();
        
        // Clean up tree-specific elements
        if (this.dropIndicator && this.dropIndicator.parentNode) {
            this.dropIndicator.parentNode.removeChild(this.dropIndicator);
        }
    }
}

// ==================== GRID DRAG DROP MANAGER ====================

class GridDragDropManager extends DragDropManager {
    constructor(container, options = {}) {
        super(container, {
            ...options,
            itemSelector: '.grid-item',
            handleSelector: '.grid-drag-handle'
        });
        
        this.gridColumns = 0;
        this.gridRows = 0;
        this.calculateGrid();
    }

    calculateGrid() {
        if (!this.container) return;
        
        const items = this.container.querySelectorAll(this.options.itemSelector);
        if (items.length === 0) return;
        
        const containerRect = this.container.getBoundingClientRect();
        const firstItemRect = items[0].getBoundingClientRect();
        
        this.gridColumns = Math.floor(containerRect.width / firstItemRect.width);
        this.gridRows = Math.ceil(items.length / this.gridColumns);
    }

    findDropTarget(element) {
        if (!element) return null;
        
        const gridItem = element.closest(this.options.itemSelector);
        if (gridItem && this.container.contains(gridItem) && gridItem !== this.draggedElement) {
            return gridItem;
        }
        
        return null;
    }

    updatePlaceholderPosition(dropTarget, clientX, clientY) {
        const rect = dropTarget.getBoundingClientRect();
        const midX = rect.left + rect.width / 2;
        const midY = rect.top + rect.height / 2;
        
        // Determine drop position based on quadrants
        let insertBefore = false;
        
        if (clientX < midX && clientY < midY) {
            // Top-left quadrant
            insertBefore = true;
        } else if (clientX > midX && clientY < midY) {
            // Top-right quadrant
            insertBefore = false;
        } else if (clientX < midX && clientY > midY) {
            // Bottom-left quadrant
            insertBefore = true;
        } else {
            // Bottom-right quadrant
            insertBefore = false;
        }
        
        if (insertBefore) {
            dropTarget.parentNode.insertBefore(this.placeholder, dropTarget);
        } else {
            dropTarget.parentNode.insertBefore(this.placeholder, dropTarget.nextSibling);
        }
    }

    setMobileMode(isMobile) {
        super.setMobileMode(isMobile);
        
        if (isMobile) {
            // Adjust grid for mobile
            this.gridColumns = 1;
        } else {
            this.calculateGrid();
        }
    }
}

// ==================== SORTABLE LIST MANAGER ====================

class SortableListManager extends DragDropManager {
    constructor(container, options = {}) {
        super(container, {
            ...options,
            itemSelector: '.sortable-item',
            handleSelector: '.sort-handle'
        });
        
        this.sortOrder = [];
        this.updateSortOrder();
    }

    updateSortOrder() {
        const items = this.container.querySelectorAll(this.options.itemSelector);
        this.sortOrder = Array.from(items).map(item => 
            item.getAttribute('data-sort-id') || item.id
        );
    }

    completeDrop() {
        super.completeDrop();
        
        const newSortOrder = [];
        const items = this.container.querySelectorAll(this.options.itemSelector);
        
        Array.from(items).forEach(item => {
            const id = item.getAttribute('data-sort-id') || item.id;
            if (id) {
                newSortOrder.push(id);
            }
        });
        
        // Check if order actually changed
        if (JSON.stringify(this.sortOrder) !== JSON.stringify(newSortOrder)) {
            this.sortOrder = newSortOrder;
            
            if (this.options.onSortChange) {
                this.options.onSortChange(this.sortOrder);
            }
        }
    }

    getSortOrder() {
        return [...this.sortOrder];
    }

    setSortOrder(order) {
        this.sortOrder = [...order];
        
        // Reorder DOM elements to match
        const items = Array.from(this.container.querySelectorAll(this.options.itemSelector));
        
        order.forEach((id, index) => {
            const item = items.find(el => 
                (el.getAttribute('data-sort-id') || el.id) === id
            );
            
            if (item) {
                this.container.appendChild(item);
            }
        });
    }
}

// Export drag and drop managers
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        DragDropManager,
        TreeDragDropManager,
        GridDragDropManager,
        SortableListManager
    };
}