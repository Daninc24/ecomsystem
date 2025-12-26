"""
Main Flask Application with SQLite Database
E-commerce System with Dynamic Admin Interface
"""

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash
from datetime import datetime, timezone
import logging

# Import configurations and models
from config_sqlite import config
from models_sqlite import (
    db, init_db, User, Role, Product, Category, Order, OrderItem, 
    Address, AdminSetting, ActivityLog, create_default_settings
)

# Import admin system
from admin.api.main_api import admin_api
from admin.services.configuration_manager import ConfigurationManager
from admin.services.content_manager import ContentManager
from admin.services.theme_manager import ThemeManager
from admin.services.user_manager import UserManager


def create_app(config_name=None):
    """Application factory"""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    init_db(app)
    
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Make CSRF token available in templates
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)
    
    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    register_blueprints(app)
    
    # Initialize admin services
    init_admin_services(app)
    
    # Create default data
    with app.app_context():
        create_default_settings()
        create_sample_data()
    
    # Configure logging
    configure_logging(app)
    
    return app


def register_blueprints(app):
    """Register application blueprints"""
    
    # Register admin API
    app.register_blueprint(admin_api, url_prefix='/api/admin')
    
    # Main routes
    @app.route('/')
    def index():
        """Home page"""
        # Get featured products
        featured_products = Product.query.filter_by(is_featured=True, is_active=True).limit(8).all()
        
        # Get categories
        categories = Category.query.filter_by(is_active=True, parent_id=None).limit(8).all()
        
        # Get category products for showcase
        category_products = {}
        for category in categories[:4]:  # Limit to 4 categories for homepage
            products = Product.query.filter(
                Product.categories.any(Category.id == category.id),
                Product.is_active == True
            ).limit(6).all()
            
            if products:
                category_products[category.name] = {
                    'category': {
                        'name': category.name,
                        'slug': category.slug,
                        'icon': '🛍️',  # Default icon
                        'color': '#ff4747'  # Default color
                    },
                    'products': products
                }
        
        # Get flash deals (featured products with discounts)
        flash_deals = Product.query.filter(
            Product.is_active == True,
            Product.compare_price.isnot(None),
            Product.compare_price > Product.price
        ).limit(6).all()
        
        return render_template('index_enhanced.html', 
                             featured_products=featured_products,
                             categories=categories,
                             category_products=category_products,
                             flash_deals=flash_deals)
    
    @app.route('/products')
    def products():
        """Products listing page"""
        page = request.args.get('page', 1, type=int)
        category_id = request.args.get('category', type=int)
        search = request.args.get('search', '')
        
        query = Product.query.filter_by(is_active=True)
        
        if category_id:
            query = query.filter(Product.categories.any(Category.id == category_id))
        
        if search:
            query = query.filter(Product.name.contains(search))
        
        products = query.paginate(
            page=page, 
            per_page=app.config['POSTS_PER_PAGE'], 
            error_out=False
        )
        
        categories = Category.query.filter_by(is_active=True).all()
        
        return render_template('products_enhanced.html', 
                             products=products,
                             categories=categories,
                             current_category=category_id,
                             search_query=search)
    
    @app.route('/product/<slug>')
    def product_detail(slug):
        """Product detail page"""
        product = Product.query.filter_by(slug=slug, is_active=True).first_or_404()
        
        # Get related products from same categories
        related_products = Product.query.filter(
            Product.categories.any(Category.id.in_([cat.id for cat in product.categories])),
            Product.id != product.id,
            Product.is_active == True
        ).limit(4).all()
        
        return render_template('product_detail_enhanced.html', 
                             product=product,
                             related_products=related_products)
    
    # Authentication routes
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Login page"""
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            remember = bool(request.form.get('remember'))
            
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password) and user.is_active:
                login_user(user, remember=remember)
                user.last_login = datetime.now(timezone.utc)
                db.session.commit()
                
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                
                # Redirect based on user role
                if user.has_role('admin'):
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('index'))
            else:
                flash('Invalid email or password', 'error')
        
        return render_template('login.html')
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """Registration page"""
        # Check if registration is enabled
        setting = AdminSetting.query.filter_by(key='enable_user_registration').first()
        if setting and not setting.get_value():
            flash('User registration is currently disabled', 'error')
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            
            # Check if user already exists
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'error')
                return render_template('register.html')
            
            if User.query.filter_by(username=username).first():
                flash('Username already taken', 'error')
                return render_template('register.html')
            
            # Create new user
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                is_verified=False
            )
            user.set_password(password)
            
            # Assign default role
            default_role = Role.query.filter_by(is_default=True).first()
            if default_role:
                user.roles.append(default_role)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        
        return render_template('register.html')
    
    @app.route('/logout')
    @login_required
    def logout():
        """Logout"""
        logout_user()
        flash('You have been logged out', 'info')
        return redirect(url_for('index'))
    
    # Admin dashboard
    @app.route('/admin')
    @login_required
    def admin_dashboard():
        """Admin dashboard"""
        if not current_user.has_role('admin'):
            flash('Access denied', 'error')
            return redirect(url_for('index'))
        
        # Get dashboard statistics
        stats = {
            'total_users': User.query.count(),
            'total_products': Product.query.count(),
            'total_orders': Order.query.count(),
            'pending_orders': Order.query.filter_by(status='pending').count(),
        }
        
        # Get recent orders
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
        
        # Get recent activity
        recent_activity = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
        
        return render_template('admin/frontend_dashboard.html',
                             stats=stats,
                             recent_orders=recent_orders,
                             recent_activity=recent_activity)
    
    # Admin test page for inline editing and product management
    @app.route('/admin/test')
    @login_required
    def admin_test():
        """Admin test page for inline editing and product management"""
        if not current_user.has_role('admin'):
            flash('Access denied', 'error')
            return redirect(url_for('index'))
        
        return render_template('admin_test.html')
    
    # Debug page for inline editing issues
    @app.route('/admin/debug')
    @login_required
    def admin_debug():
        """Debug page for inline editing issues"""
        if not current_user.has_role('admin'):
            flash('Access denied', 'error')
            return redirect(url_for('index'))
        
        return render_template('debug_inline_editing.html')
    
    # Product management test page
    @app.route('/admin/products-test')
    @login_required
    def admin_products_test():
        """Product management test page"""
        if not current_user.has_role('admin'):
            flash('Access denied', 'error')
            return redirect(url_for('index'))
        
        return render_template('product_management_test.html')

    @app.route('/preview')
    def theme_preview():
        """Theme preview page for admin"""
        # This is a simplified version of the main page for theme preview
        featured_products = Product.query.filter_by(is_featured=True, is_active=True).limit(4).all()
        categories = Category.query.filter_by(is_active=True, parent_id=None).limit(4).all()
        
        return render_template('index_enhanced.html', 
                             featured_products=featured_products,
                             categories=categories,
                             category_products={},
                             flash_deals=[],
                             is_preview=True)
    
    # Cart functionality
    @app.route('/cart')
    def cart():
        """Shopping cart"""
        cart_items = session.get('cart', {})
        
        # Get product details for cart items
        products = []
        total = 0
        
        for product_id, quantity in cart_items.items():
            product = Product.query.get(int(product_id))
            if product and product.is_active:
                item_total = product.price * quantity
                products.append({
                    'product': product,
                    'quantity': quantity,
                    'total': item_total
                })
                total += item_total
        
        return render_template('cart_enhanced.html', 
                             cart_items=products,
                             cart_total=total)
    
    @app.route('/add_to_cart/<int:product_id>')
    def add_to_cart(product_id):
        """Add product to cart"""
        product = Product.query.get_or_404(product_id)
        
        if not product.is_active or not product.is_in_stock():
            flash('Product is not available', 'error')
            return redirect(url_for('product_detail', slug=product.slug))
        
        cart = session.get('cart', {})
        cart[str(product_id)] = cart.get(str(product_id), 0) + 1
        session['cart'] = cart
        
        flash(f'{product.name} added to cart', 'success')
        return redirect(url_for('product_detail', slug=product.slug))
    
    @app.route('/remove_from_cart/<int:product_id>')
    def remove_from_cart(product_id):
        """Remove product from cart"""
        cart = session.get('cart', {})
        cart.pop(str(product_id), None)
        session['cart'] = cart
        
        flash('Item removed from cart', 'info')
        return redirect(url_for('cart'))
    
    # API endpoints
    @app.route('/api/cart/count')
    def api_cart_count():
        """Get cart item count"""
        cart_count = sum(session.get('cart', {}).values())
        return jsonify({'count': cart_count})
    
    @app.route('/api/cart/items')
    def api_cart_items():
        """Get cart items"""
        cart_items = session.get('cart', {})
        
        # Get product details for cart items
        products = []
        total = 0
        
        for product_id, quantity in cart_items.items():
            product = Product.query.get(int(product_id))
            if product and product.is_active:
                item_total = product.price * quantity
                products.append({
                    'id': product.id,
                    'name': product.name,
                    'price': product.price,
                    'quantity': quantity,
                    'total': item_total,
                    'image': product.get_main_image()
                })
                total += item_total
        
        return jsonify({
            'items': products,
            'total': total,
            'count': sum(cart_items.values())
        })

    @app.route('/api/dashboard/stats')
    def api_dashboard_stats():
        """Get dashboard statistics"""
        try:
            stats = {
                'total_users': User.query.count(),
                'total_products': Product.query.count(),
                'total_orders': Order.query.count(),
                'active_products': Product.query.filter_by(is_active=True).count(),
                'revenue': sum([order.total_amount for order in Order.query.all()]),
                'pending_orders': Order.query.filter_by(status='pending').count()
            }
            return jsonify({
                'success': True,
                'data': stats
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # Additional routes for template compatibility
    @app.route('/contact')
    def contact():
        """Contact page"""
        return render_template('contact.html')
    
    @app.route('/help-center')
    def help_center():
        """Help center page"""
        return render_template('help_center.html')
    
    @app.route('/track-order')
    def track_order():
        """Track order page"""
        return render_template('track_order.html')
    
    @app.route('/become-vendor')
    def become_vendor():
        """Become vendor page"""
        return render_template('become_vendor.html')
    
    @app.route('/vendors')
    def vendors():
        """Vendors listing page"""
        return render_template('vendors.html')
    
    @app.route('/orders')
    @login_required
    def orders():
        """User orders page"""
        user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
        return render_template('orders.html', orders=user_orders)
    
    @app.route('/profile')
    @login_required
    def profile():
        """User profile page"""
        return render_template('profile.html', user=current_user)
    
    @app.route('/about')
    def about():
        """About page"""
        return render_template('about.html')
    
    @app.route('/careers')
    def careers():
        """Careers page"""
        return render_template('careers.html')
    
    @app.route('/press')
    def press():
        """Press page"""
        return render_template('press.html')
    
    @app.route('/investor-relations')
    def investor_relations():
        """Investor relations page"""
        return render_template('investor_relations.html')
    
    @app.route('/returns-refunds')
    def returns_refunds():
        """Returns and refunds page"""
        return render_template('returns_refunds.html')
    
    @app.route('/size-guide')
    def size_guide():
        """Size guide page"""
        return render_template('size_guide.html')
    
    @app.route('/flash-deals')
    def flash_deals():
        """Flash deals page"""
        return render_template('flash_deals.html')
    
    @app.route('/new-arrivals')
    def new_arrivals():
        """New arrivals page"""
        return render_template('new_arrivals.html')
    
    @app.route('/best-sellers')
    def best_sellers():
        """Best sellers page"""
        return render_template('best_sellers.html')
    
    @app.route('/gift-cards')
    def gift_cards():
        """Gift cards page"""
        return render_template('gift_cards.html')
    
    @app.route('/seller-center')
    def seller_center():
        """Seller center page"""
        return render_template('seller_center.html')
    
    @app.route('/seller-protection')
    def seller_protection():
        """Seller protection page"""
        return render_template('seller_protection.html')
    
    @app.route('/advertising')
    def advertising():
        """Advertising page"""
        return render_template('advertising.html')
    
    @app.route('/success-stories')
    def success_stories():
        """Success stories page"""
        return render_template('success_stories.html')
    
    @app.route('/cookie-policy')
    def cookie_policy():
        """Cookie policy page"""
        return render_template('cookie_policy.html')
    
    @app.route('/privacy-policy')
    def privacy_policy():
        """Privacy policy page"""
        return render_template('privacy_policy.html')
    
    @app.route('/terms-of-service')
    def terms_of_service():
        """Terms of service page"""
        return render_template('terms_of_service.html')
    
    @app.route('/sustainability')
    def sustainability():
        """Sustainability page"""
        return render_template('sustainability.html')
    
    @app.route('/trade-assurance-info')
    def trade_assurance_info():
        """Trade assurance info page"""
        return render_template('trade_assurance_info.html')
    
    @app.route('/checkout')
    @login_required
    def checkout():
        """Checkout page"""
        cart_items = session.get('cart', {})
        if not cart_items:
            flash('Your cart is empty', 'info')
            return redirect(url_for('cart'))
        
        # Get product details for cart items
        products = []
        total = 0
        
        for product_id, quantity in cart_items.items():
            product = Product.query.get(int(product_id))
            if product and product.is_active:
                item_total = product.price * quantity
                products.append({
                    'product': product,
                    'quantity': quantity,
                    'total': item_total
                })
                total += item_total
        
        return render_template('checkout.html', 
                             cart_items=products,
                             cart_total=total)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500
    
    # Context processors
    @app.context_processor
    def inject_globals():
        """Inject global template variables"""
        # Get site settings
        site_name = AdminSetting.query.filter_by(key='site_name').first()
        site_description = AdminSetting.query.filter_by(key='site_description').first()
        contact_email = AdminSetting.query.filter_by(key='contact_email').first()
        
        # Get cart count
        cart_count = sum(session.get('cart', {}).values())
        
        # Create store_config object for template compatibility
        store_config = {
            'name': site_name.get_value() if site_name else 'MarketHub Pro',
            'description': site_description.get_value() if site_description else 'Your premier e-commerce marketplace',
            'tagline': 'Global Marketplace',
            'contact_email': contact_email.get_value() if contact_email else 'contact@markethubpro.com',
            'logo_url': '/static/images/logo.png',
            'favicon_url': '/static/images/favicon.ico',
            'social_media': {
                'facebook': '#',
                'twitter': '#',
                'instagram': '#',
                'linkedin': '#',
                'youtube': '#'
            },
            'company_info': {
                'address': '123 Business Street, City, State 12345',
                'phone': '+1 (555) 123-4567',
                'email': contact_email.get_value() if contact_email else 'contact@markethubpro.com'
            },
            'features': {
                'free_shipping': True,
                'buyer_protection': True,
                'secure_payments': True,
                'money_back_guarantee': True
            }
        }
        
        return {
            'site_name': store_config['name'],
            'site_description': store_config['description'],
            'store_config': store_config,
            'cart_count': cart_count,
            'current_year': datetime.now().year
        }


def init_admin_services(app):
    """Initialize admin services"""
    with app.app_context():
        # Initialize admin services with SQLite database
        app.config_manager = ConfigurationManager(db)
        app.content_manager = ContentManager(db)
        app.theme_manager = ThemeManager(db)
        app.user_manager = UserManager(db)


def create_sample_data():
    """Create sample data for development"""
    if Product.query.count() > 0:
        return  # Data already exists
    
    # Create sample categories
    categories_data = [
        {'name': 'Electronics', 'slug': 'electronics', 'description': 'Electronic devices and gadgets'},
        {'name': 'Clothing', 'slug': 'clothing', 'description': 'Fashion and apparel'},
        {'name': 'Home & Garden', 'slug': 'home-garden', 'description': 'Home improvement and garden supplies'},
        {'name': 'Sports', 'slug': 'sports', 'description': 'Sports and outdoor equipment'},
    ]
    
    categories = []
    for cat_data in categories_data:
        existing_category = Category.query.filter_by(slug=cat_data['slug']).first()
        if not existing_category:
            category = Category(**cat_data)
            db.session.add(category)
            categories.append(category)
        else:
            categories.append(existing_category)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Category creation skipped: {str(e)}")
        return
    
    # Create sample products
    products_data = [
        {
            'name': 'Wireless Bluetooth Headphones',
            'slug': 'wireless-bluetooth-headphones',
            'description': 'High-quality wireless headphones with noise cancellation',
            'short_description': 'Premium wireless headphones',
            'price': 99.99,
            'compare_price': 149.99,
            'sku': 'WBH001',
            'inventory_quantity': 50,
            'is_featured': True,
            'categories': [categories[0]]  # Electronics
        },
        {
            'name': 'Cotton T-Shirt',
            'slug': 'cotton-t-shirt',
            'description': '100% cotton comfortable t-shirt available in multiple colors',
            'short_description': 'Comfortable cotton t-shirt',
            'price': 19.99,
            'compare_price': 29.99,
            'sku': 'CTS001',
            'inventory_quantity': 100,
            'is_featured': True,
            'categories': [categories[1]]  # Clothing
        },
        {
            'name': 'LED Desk Lamp',
            'slug': 'led-desk-lamp',
            'description': 'Adjustable LED desk lamp with multiple brightness levels',
            'short_description': 'Modern LED desk lamp',
            'price': 39.99,
            'sku': 'LDL001',
            'inventory_quantity': 25,
            'categories': [categories[2]]  # Home & Garden
        },
        {
            'name': 'Yoga Mat',
            'slug': 'yoga-mat',
            'description': 'Non-slip yoga mat perfect for all types of yoga practice',
            'short_description': 'Premium yoga mat',
            'price': 29.99,
            'sku': 'YM001',
            'inventory_quantity': 75,
            'categories': [categories[3]]  # Sports
        }
    ]
    
    for product_data in products_data:
        existing_product = Product.query.filter_by(slug=product_data['slug']).first()
        if not existing_product:
            product = Product(**product_data)
            db.session.add(product)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Product creation skipped: {str(e)}")


def configure_logging(app):
    """Configure application logging"""
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = logging.FileHandler('logs/ecommerce.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('E-commerce application startup')


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5001)