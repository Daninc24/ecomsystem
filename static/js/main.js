// Main JavaScript file for E-commerce site

// Utility functions
function showError(elementId, message) {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }
}

function clearErrors() {
    const errorElements = document.querySelectorAll('.error-message');
    errorElements.forEach(element => {
        element.textContent = '';
        element.style.display = 'none';
    });
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Add to cart functionality
function addToCart(productId, quantity = 1) {
    fetch('/add_to_cart', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            product_id: productId,
            quantity: quantity
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Product added to cart!', 'success');
        } else {
            showNotification('Error adding product to cart', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error adding product to cart', 'error');
    });
}

// Notification system
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 4px;
        color: white;
        font-weight: bold;
        z-index: 1000;
        animation: slideIn 0.3s ease-out;
    `;
    
    // Set background color based on type
    switch (type) {
        case 'success':
            notification.style.backgroundColor = '#27ae60';
            break;
        case 'error':
            notification.style.backgroundColor = '#e74c3c';
            break;
        case 'warning':
            notification.style.backgroundColor = '#f39c12';
            break;
        default:
            notification.style.backgroundColor = '#3498db';
    }
    
    // Add to document
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Mobile navigation toggle
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }
    
    // Close mobile menu when clicking on a link
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (navMenu) {
                navMenu.classList.remove('active');
            }
        });
    });
});

// Form validation helpers
function validateForm(formId, validationRules) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    let isValid = true;
    clearErrors();
    
    for (const fieldName in validationRules) {
        const field = form.querySelector(`[name="${fieldName}"]`);
        const rules = validationRules[fieldName];
        
        if (!field) continue;
        
        const value = field.value.trim();
        
        // Required validation
        if (rules.required && !value) {
            showError(`${fieldName}-error`, `${rules.label || fieldName} is required`);
            isValid = false;
            continue;
        }
        
        // Min length validation
        if (rules.minLength && value.length < rules.minLength) {
            showError(`${fieldName}-error`, `${rules.label || fieldName} must be at least ${rules.minLength} characters`);
            isValid = false;
            continue;
        }
        
        // Max length validation
        if (rules.maxLength && value.length > rules.maxLength) {
            showError(`${fieldName}-error`, `${rules.label || fieldName} must be no more than ${rules.maxLength} characters`);
            isValid = false;
            continue;
        }
        
        // Email validation
        if (rules.email && !isValidEmail(value)) {
            showError(`${fieldName}-error`, 'Please enter a valid email address');
            isValid = false;
            continue;
        }
        
        // Custom validation
        if (rules.custom && !rules.custom(value)) {
            showError(`${fieldName}-error`, rules.customMessage || 'Invalid value');
            isValid = false;
            continue;
        }
    }
    
    return isValid;
}

// Search functionality with debounce
function debounce(func, wait) {
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

// Live search for products
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        const debouncedSearch = debounce(function(searchTerm) {
            if (searchTerm.length >= 2) {
                // Auto-submit form when user types
                const form = searchInput.closest('form');
                if (form) {
                    form.submit();
                }
            }
        }, 500);
        
        searchInput.addEventListener('input', function() {
            debouncedSearch(this.value);
        });
    }
});

// Quantity input validation
document.addEventListener('DOMContentLoaded', function() {
    const quantityInputs = document.querySelectorAll('input[type="number"]');
    quantityInputs.forEach(input => {
        input.addEventListener('change', function() {
            const min = parseInt(this.getAttribute('min')) || 1;
            const max = parseInt(this.getAttribute('max')) || Infinity;
            let value = parseInt(this.value);
            
            if (isNaN(value) || value < min) {
                this.value = min;
            } else if (value > max) {
                this.value = max;
            }
        });
    });
});

// Loading states for buttons
function setButtonLoading(button, isLoading) {
    if (isLoading) {
        button.disabled = true;
        button.dataset.originalText = button.textContent;
        button.textContent = 'Loading...';
        button.style.opacity = '0.7';
    } else {
        button.disabled = false;
        button.textContent = button.dataset.originalText || button.textContent;
        button.style.opacity = '1';
    }
}

// Enhanced add to cart with loading state
function addToCartWithLoading(productId, quantity = 1, buttonElement = null) {
    if (buttonElement) {
        setButtonLoading(buttonElement, true);
    }
    
    fetch('/add_to_cart', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            product_id: productId,
            quantity: quantity
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Product added to cart!', 'success');
        } else {
            showNotification('Error adding product to cart', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error adding product to cart', 'error');
    })
    .finally(() => {
        if (buttonElement) {
            setButtonLoading(buttonElement, false);
        }
    });
}

// Image lazy loading
document.addEventListener('DOMContentLoaded', function() {
    const images = document.querySelectorAll('img[data-src]');
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
});

// Smooth scrolling for anchor links
document.addEventListener('DOMContentLoaded', function() {
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    
    anchorLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
});

// Local storage helpers
const Storage = {
    set: function(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.error('Error saving to localStorage:', e);
        }
    },
    
    get: function(key) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : null;
        } catch (e) {
            console.error('Error reading from localStorage:', e);
            return null;
        }
    },
    
    remove: function(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) {
            console.error('Error removing from localStorage:', e);
        }
    }
};

// Recently viewed products
function addToRecentlyViewed(productId) {
    let recentlyViewed = Storage.get('recentlyViewed') || [];
    
    // Remove if already exists
    recentlyViewed = recentlyViewed.filter(id => id !== productId);
    
    // Add to beginning
    recentlyViewed.unshift(productId);
    
    // Keep only last 10
    recentlyViewed = recentlyViewed.slice(0, 10);
    
    Storage.set('recentlyViewed', recentlyViewed);
}

// Add to recently viewed when on product detail page
document.addEventListener('DOMContentLoaded', function() {
    const productDetailPage = document.querySelector('.product-detail');
    if (productDetailPage) {
        const addToCartBtn = document.getElementById('addToCartBtn');
        if (addToCartBtn) {
            const productId = addToCartBtn.getAttribute('data-product-id');
            if (productId) {
                addToRecentlyViewed(parseInt(productId));
            }
        }
    }
});

// Price formatting
function formatPrice(price) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(price);
}

// Update all price displays
function updatePriceDisplays() {
    const priceElements = document.querySelectorAll('.price');
    priceElements.forEach(element => {
        const price = parseFloat(element.textContent.replace(/[^0-9.]/g, ''));
        if (!isNaN(price)) {
            element.textContent = formatPrice(price);
        }
    });
}

// Initialize price formatting on page load
document.addEventListener('DOMContentLoaded', updatePriceDisplays);

// Export functions for use in other scripts
window.ECommerce = {
    addToCart,
    addToCartWithLoading,
    showNotification,
    validateForm,
    setButtonLoading,
    Storage,
    formatPrice
};