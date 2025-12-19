# E-Commerce Application Testing Checklist

## Pre-Testing Setup
- [ ] Run `python setup.py` to initialize the application
- [ ] Verify database `ecommerce.db` is created
- [ ] Start application with `python app.py` or `python run.py`
- [ ] Open browser to `http://localhost:5000`

## 1. Authentication System Testing

### User Registration
- [ ] Navigate to `/register`
- [ ] Test form validation (empty fields, invalid email, password mismatch)
- [ ] Register a new user successfully
- [ ] Verify duplicate username/email prevention
- [ ] Check user is redirected to login page after registration

### User Login
- [ ] Navigate to `/login`
- [ ] Test form validation (empty fields, invalid credentials)
- [ ] Login with admin credentials (admin/admin123)
- [ ] Login with regular user credentials (user/user123)
- [ ] Verify session persistence across page navigation
- [ ] Test logout functionality

## 2. Product System Testing

### Product Browsing
- [ ] Visit homepage - verify featured products display
- [ ] Navigate to `/products` - verify all products load
- [ ] Test search functionality with various keywords
- [ ] Test category filtering
- [ ] Test price sorting (low to high, high to low)
- [ ] Verify product images load correctly

### Product Details
- [ ] Click on any product to view details
- [ ] Verify all product information displays correctly
- [ ] Test quantity selector (min/max validation)
- [ ] Test "Add to Cart" button (requires login)

## 3. Shopping Cart Testing

### Cart Operations (Logged in users only)
- [ ] Add products to cart from product listing
- [ ] Add products to cart from product detail page
- [ ] Navigate to `/cart` to view cart contents
- [ ] Test quantity updates (increase/decrease)
- [ ] Test item removal from cart
- [ ] Verify cart total calculations are correct
- [ ] Test cart persistence across sessions

### Cart Edge Cases
- [ ] Test adding same product multiple times
- [ ] Test cart with zero quantity items
- [ ] Test cart when not logged in (should redirect to login)

## 4. Checkout System Testing

### Checkout Process
- [ ] Navigate to `/checkout` with items in cart
- [ ] Verify order summary displays correctly
- [ ] Fill out shipping information form
- [ ] Test form validation (required fields)
- [ ] Submit order successfully
- [ ] Verify order confirmation and redirect to orders page
- [ ] Check that cart is emptied after successful order

### Checkout Edge Cases
- [ ] Try to access checkout with empty cart
- [ ] Test checkout when not logged in

## 5. Order Management Testing

### User Orders
- [ ] Navigate to `/orders` to view order history
- [ ] Verify orders display with correct information
- [ ] Check order status displays correctly
- [ ] Test with user who has no orders

## 6. Admin Dashboard Testing

### Admin Access
- [ ] Login as admin (admin/admin123)
- [ ] Navigate to `/admin` - verify dashboard loads
- [ ] Check statistics display correctly (users, products, orders)
- [ ] Verify recent orders section

### Product Management
- [ ] Navigate to `/admin/products`
- [ ] Test adding new product (`/admin/add_product`)
  - [ ] Test form validation
  - [ ] Add product successfully
  - [ ] Verify product appears in catalog
- [ ] Test editing existing product
  - [ ] Modify product details
  - [ ] Verify changes reflect in catalog
- [ ] Test deleting product
  - [ ] Confirm deletion prompt
  - [ ] Verify product removed from catalog

### Order Management
- [ ] Navigate to `/admin/orders`
- [ ] View all orders in system
- [ ] Test updating order status
- [ ] Verify status changes are saved

### Admin Security
- [ ] Try accessing admin pages as regular user (should be denied)
- [ ] Try accessing admin pages when not logged in (should redirect)

## 7. User Interface Testing

### Responsive Design
- [ ] Test on desktop browser (1920x1080)
- [ ] Test on tablet size (768px width)
- [ ] Test on mobile size (375px width)
- [ ] Verify navigation menu works on mobile
- [ ] Check all forms are usable on mobile

### Navigation
- [ ] Test all navigation links work correctly
- [ ] Verify breadcrumbs and page titles
- [ ] Test browser back/forward buttons
- [ ] Check footer links and information

### Visual Elements
- [ ] Verify CSS styles load correctly
- [ ] Check button hover effects
- [ ] Test loading states and animations
- [ ] Verify error/success message display
- [ ] Check image loading and fallbacks

## 8. JavaScript Functionality Testing

### Form Validation
- [ ] Test client-side validation on registration form
- [ ] Test client-side validation on login form
- [ ] Test client-side validation on product forms (admin)
- [ ] Verify error messages display correctly

### Dynamic Features
- [ ] Test "Add to Cart" AJAX functionality
- [ ] Test cart quantity updates without page refresh
- [ ] Test search with live filtering (if implemented)
- [ ] Test notification system for user feedback

### Browser Compatibility
- [ ] Test in Chrome
- [ ] Test in Firefox
- [ ] Test in Safari (if available)
- [ ] Test in Edge (if available)

## 9. Security Testing

### Authentication Security
- [ ] Verify passwords are hashed in database
- [ ] Test session timeout behavior
- [ ] Try accessing protected routes without login
- [ ] Test CSRF protection on forms

### Input Validation
- [ ] Test SQL injection attempts in forms
- [ ] Test XSS attempts in text fields
- [ ] Verify file upload restrictions (if any)
- [ ] Test input length limits

## 10. Performance Testing

### Load Testing
- [ ] Test with multiple products (50+)
- [ ] Test with multiple users (create several accounts)
- [ ] Test with large cart (10+ items)
- [ ] Monitor page load times

### Database Performance
- [ ] Check query performance with sample data
- [ ] Verify no N+1 query problems
- [ ] Test database connection handling

## 11. Error Handling Testing

### Server Errors
- [ ] Test behavior when database is unavailable
- [ ] Test invalid URL routes (404 errors)
- [ ] Test server error handling (500 errors)

### User Errors
- [ ] Test invalid form submissions
- [ ] Test accessing non-existent products
- [ ] Test invalid search queries

## 12. Data Integrity Testing

### Database Consistency
- [ ] Verify foreign key relationships work correctly
- [ ] Test data validation at database level
- [ ] Check for orphaned records after deletions

### Business Logic
- [ ] Verify stock levels decrease after orders
- [ ] Test inventory management (out of stock scenarios)
- [ ] Verify order totals match cart calculations

## Final Verification

### Complete User Journey
- [ ] Register new account
- [ ] Browse and search products
- [ ] Add multiple items to cart
- [ ] Complete checkout process
- [ ] View order in order history
- [ ] Login as admin and process the order

### Code Quality
- [ ] Check for console errors in browser
- [ ] Verify no broken links
- [ ] Check all images load correctly
- [ ] Verify all forms submit correctly

## Bug Reporting Template

When you find issues, document them as follows:

**Bug Title**: Brief description
**Steps to Reproduce**:
1. Step 1
2. Step 2
3. Step 3

**Expected Result**: What should happen
**Actual Result**: What actually happened
**Browser/Device**: Browser and device information
**Screenshot**: If applicable

---

## Test Results Summary

- **Total Tests**: ___
- **Passed**: ___
- **Failed**: ___
- **Critical Issues**: ___
- **Minor Issues**: ___

**Overall Status**: ✅ Ready for Production / ⚠️ Needs Fixes / ❌ Major Issues

**Tester**: _______________
**Date**: _______________
**Version**: _______________