"""
Enhanced E-Commerce Application with MongoDB (using mock for testing)
AliExpress-inspired design with modern features
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
try:
    from flask_pymongo import PyMongo
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from bson import ObjectId
import os
import json
import uuid
from config_mongo import config, STORE_CONFIG, PRODUCT_CATEGORIES, ORDER_STATUSES

# Import mock MongoDB if real MongoDB is not available
from simple_mongo_mock import mock_mongo

# Create Flask app with MongoDB configuration
app = Flask(__name__)
config_name = os.environ.get('FLASK_CONFIG') or 'default'
app.config.from_object(config[config_name])

# Initialize MongoDB (force mock for testing)
print("⚠️ Using mock MongoDB for testing")
mongo = mock_mongo
mongo.init_app(app)

# Make store config available to templates
@app.context_processor
def inject_store_config():
    return dict(
        store_config=STORE_CONFIG,
        product_categories=PRODUCT_CATEGORIES,
        order_statuses=ORDER_STATUSES
    )

# Custom template filters
@app.template_filter('from_json')
def from_json_filter(value):
    """Parse JSON string in templates."""
    try:
        return json.loads(value) if value else {}
    except (json.JSONDecodeError, TypeError):
        return {}

@app.template_filter('objectid')
def objectid_filter(value):
    """Convert ObjectId to string."""
    return str(value) if value else ''

@app.template_filter('safe_strftime')
def safe_strftime_filter(value, format_string='%Y-%m-%d'):
    """Safely format datetime objects, handling strings and None values."""
    if not value:
        return 'N/A'
    
    # If it's already a string, return it as-is or a default
    if isinstance(value, str):
        return 'Recently'
    
    # If it's a datetime object, format it
    try:
        if hasattr(value, 'strftime'):
            return value.strftime(format_string)
        else:
            return 'Recently'
    except (AttributeError, TypeError, ValueError):
        return 'Recently'

# Helper functions
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
        if not user or user.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def vendor_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
        if not user or user.get('role') not in ['vendor', 'admin']:
            flash('Vendor access required', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def generate_order_number():
    """Generate a unique order number."""
    timestamp = datetime.now().strftime('%Y%m%d')
    random_part = str(uuid.uuid4().hex[:6]).upper()
    return f"MH{timestamp}{random_part}"

def generate_sku():
    """Generate a unique SKU."""
    return f"SKU-{uuid.uuid4().hex[:8].upper()}"

# ==================== MAIN ROUTES ====================

@app.route('/')
def index():
    """Enhanced homepage with AliExpress-inspired design."""
    # Get featured products
    featured_products = list(mongo.db.products.find({
        'status': 'active',
        'is_featured': True
    }).limit(12))
    
    # Get products by category for showcase
    category_products = {}
    for category in PRODUCT_CATEGORIES[:6]:  # Show top 6 categories
        products = list(mongo.db.products.find({
            'basic_info.category': category['name'],
            'status': 'active'
        }).limit(8))
        if products:
            category_products[category['name']] = {
                'category': category,
                'products': products
            }
    
    # Get flash deals (products with high discounts)
    flash_deals = list(mongo.db.products.find({
        'status': 'active',
        'pricing.discount_percentage': {'$gte': 20}
    }).limit(10))
    
    # Get top vendors
    top_vendors = list(mongo.db.vendors.find({
        'verification.is_verified': True
    }).sort('performance.rating', -1).limit(8))
    
    # Get recent reviews
    recent_reviews = list(mongo.db.reviews.find().sort('created_at', -1).limit(6))
    
    return render_template('index_enhanced.html',
                         featured_products=featured_products,
                         category_products=category_products,
                         flash_deals=flash_deals,
                         top_vendors=top_vendors,
                         recent_reviews=recent_reviews)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        
        # Check if user exists
        if mongo.db.users.find_one({'username': username}):
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if mongo.db.users.find_one({'email': email}):
            flash('Email already exists', 'error')
            return render_template('register.html')
        
        # Create user document
        user_doc = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'role': 'user',
            'profile': {
                'first_name': first_name,
                'last_name': last_name,
                'avatar_url': '',
                'phone': '',
                'date_of_birth': None,
                'gender': ''
            },
            'addresses': [],
            'preferences': {
                'language': 'en',
                'currency': 'USD',
                'notifications': {
                    'email': True,
                    'sms': False,
                    'push': True
                }
            },
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'last_login': None,
            'is_active': True,
            'email_verified': False
        }
        
        result = mongo.db.users.insert_one(user_doc)
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = mongo.db.users.find_one({'username': username})
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            session['role'] = user['role']
            
            # Update last login
            mongo.db.users.update_one(
                {'_id': user['_id']},
                {'$set': {'last_login': datetime.utcnow()}}
            )
            
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('index'))

@app.route('/products')
def products():
    """Enhanced products page with advanced filtering."""
    page = int(request.args.get('page', 1))
    per_page = app.config['PRODUCTS_PER_PAGE']
    
    # Build query
    query = {'status': 'active'}
    
    # Category filter
    category = request.args.get('category')
    if category:
        query['basic_info.category'] = category
    
    # Search filter
    search = request.args.get('search')
    if search:
        query['$or'] = [
            {'basic_info.name': {'$regex': search, '$options': 'i'}},
            {'basic_info.description': {'$regex': search, '$options': 'i'}},
            {'seo.tags': {'$in': [search]}}
        ]
    
    # Price range filter
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    if min_price is not None or max_price is not None:
        price_query = {}
        if min_price is not None:
            price_query['$gte'] = min_price
        if max_price is not None:
            price_query['$lte'] = max_price
        query['pricing.price'] = price_query
    
    # Sorting
    sort_by = request.args.get('sort', 'name')
    sort_options = {
        'name': ('basic_info.name', 1),
        'price_asc': ('pricing.price', 1),
        'price_desc': ('pricing.price', -1),
        'newest': ('created_at', -1),
        'popular': ('views', -1),
        'rating': ('rating', -1)
    }
    sort_field, sort_direction = sort_options.get(sort_by, ('basic_info.name', 1))
    
    # Get products with pagination
    skip = (page - 1) * per_page
    products = list(mongo.db.products.find(query)
                   .sort(sort_field, sort_direction)
                   .skip(skip)
                   .limit(per_page))
    
    # Get total count for pagination
    total_products = mongo.db.products.count_documents(query)
    total_pages = (total_products + per_page - 1) // per_page
    
    # Get categories for filter
    categories = PRODUCT_CATEGORIES
    
    return render_template('products_enhanced.html',
                         products=products,
                         categories=categories,
                         current_page=page,
                         total_pages=total_pages,
                         total_products=total_products,
                         has_prev=page > 1,
                         has_next=page < total_pages,
                         prev_num=page - 1 if page > 1 else None,
                         next_num=page + 1 if page < total_pages else None)

@app.route('/product/<product_id>')
def product_detail(product_id):
    """Enhanced product detail page."""
    try:
        product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
        if not product:
            flash('Product not found', 'error')
            return redirect(url_for('products'))
        
        # Get vendor info
        vendor = None
        if product.get('vendor_id'):
            vendor = mongo.db.vendors.find_one({'_id': ObjectId(product['vendor_id'])})
        
        # Get reviews
        reviews = list(mongo.db.reviews.find({'product_id': ObjectId(product_id)})
                      .sort('created_at', -1).limit(10))
        
        # Get related products
        related_products = list(mongo.db.products.find({
            'basic_info.category': product['basic_info']['category'],
            '_id': {'$ne': ObjectId(product_id)},
            'status': 'active'
        }).limit(8))
        
        # Update view count
        mongo.db.products.update_one(
            {'_id': ObjectId(product_id)},
            {'$inc': {'views': 1}}
        )
        
        return render_template('product_detail_enhanced.html',
                             product=product,
                             vendor=vendor,
                             reviews=reviews,
                             related_products=related_products)
    
    except Exception as e:
        flash('Error loading product', 'error')
        return redirect(url_for('products'))

# ==================== DYNAMIC API ROUTES ====================

@app.route('/api/search')
def api_search():
    """Real-time search API endpoint for MongoDB."""
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify({'success': False, 'message': 'Query too short'})
    
    try:
        # Search in products using MongoDB text search
        search_query = {
            'status': 'active',
            '$or': [
                {'basic_info.name': {'$regex': query, '$options': 'i'}},
                {'basic_info.description': {'$regex': query, '$options': 'i'}},
                {'basic_info.category': {'$regex': query, '$options': 'i'}},
                {'seo.tags': {'$in': [query]}}
            ]
        }
        
        products = list(mongo.db.products.find(search_query).limit(10))
        
        results = []
        for product in products:
            # Get vendor info if exists
            vendor_name = None
            if product.get('vendor_id'):
                vendor = mongo.db.vendors.find_one({'_id': ObjectId(product['vendor_id'])})
                if vendor:
                    vendor_name = vendor['business_info']['name']
            
            results.append({
                'id': str(product['_id']),
                'name': product['basic_info']['name'],
                'price': product['pricing']['price'],
                'image_url': product['media']['main_image'],
                'vendor_name': vendor_name
            })
        
        return jsonify({'success': True, 'results': results})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/products/filter', methods=['POST'])
def api_filter_products():
    """Dynamic product filtering API for MongoDB."""
    try:
        filters = request.json
        
        # Build MongoDB query
        query = {'status': 'active'}
        
        # Apply category filter
        if filters.get('categories'):
            query['basic_info.category'] = {'$in': filters['categories']}
        
        # Apply price filter
        if filters.get('price_max'):
            query['pricing.price'] = {'$lte': filters['price_max']}
        
        # Apply search filter
        if filters.get('search'):
            search_term = filters['search']
            query['$or'] = [
                {'basic_info.name': {'$regex': search_term, '$options': 'i'}},
                {'basic_info.description': {'$regex': search_term, '$options': 'i'}},
                {'seo.tags': {'$in': [search_term]}}
            ]
        
        # Apply sorting
        sort_option = filters.get('sort', 'name')
        sort_options = {
            'name': ('basic_info.name', 1),
            'price_asc': ('pricing.price', 1),
            'price_desc': ('pricing.price', -1),
            'newest': ('created_at', -1),
            'popular': ('views', -1)
        }
        sort_field, sort_direction = sort_options.get(sort_option, ('basic_info.name', 1))
        
        # Get products
        products_cursor = mongo.db.products.find(query).sort(sort_field, sort_direction).limit(50)
        
        products = []
        for product in products_cursor:
            # Get vendor info
            vendor_name = None
            if product.get('vendor_id'):
                vendor = mongo.db.vendors.find_one({'_id': ObjectId(product['vendor_id'])})
                if vendor:
                    vendor_name = vendor['business_info']['name']
            
            products.append({
                'id': str(product['_id']),
                'name': product['basic_info']['name'],
                'description': product['basic_info']['description'],
                'price': product['pricing']['price'],
                'image_url': product['media']['main_image'],
                'vendor_name': vendor_name,
                'discount_percentage': product['pricing'].get('discount_percentage', 0),
                'is_featured': product.get('is_featured', False)
            })
        
        return jsonify({
            'success': True,
            'products': products,
            'total': len(products)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/cart/count')
def api_cart_count():
    """Get current cart item count from MongoDB."""
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({'success': True, 'count': 0})
    
    try:
        count = mongo.db.cart.count_documents({'user_id': ObjectId(session['user_id'])})
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ==================== CART AND ORDER ROUTES ====================

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """Add product to cart in MongoDB."""
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please log in to add items to cart', 'redirect': url_for('login')})
    
    try:
        product_id = request.json.get('product_id')
        quantity = request.json.get('quantity', 1)
        
        # Check if product exists
        product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'})
        
        # Check stock
        if product['inventory']['stock'] < quantity:
            return jsonify({'success': False, 'message': 'Insufficient stock'})
        
        # Check if item already in cart
        existing_item = mongo.db.cart.find_one({
            'user_id': ObjectId(session['user_id']),
            'product_id': ObjectId(product_id)
        })
        
        if existing_item:
            # Update quantity
            new_quantity = existing_item['quantity'] + quantity
            if product['inventory']['stock'] < new_quantity:
                return jsonify({'success': False, 'message': 'Insufficient stock'})
            
            mongo.db.cart.update_one(
                {'_id': existing_item['_id']},
                {'$set': {'quantity': new_quantity, 'updated_at': datetime.utcnow()}}
            )
        else:
            # Add new item
            cart_item = {
                'user_id': ObjectId(session['user_id']),
                'product_id': ObjectId(product_id),
                'quantity': quantity,
                'price': product['pricing']['price'],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            mongo.db.cart.insert_one(cart_item)
        
        return jsonify({'success': True, 'message': 'Added to cart successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/update_cart', methods=['POST'])
def update_cart():
    """Update cart item quantity."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please log in'})
    
    try:
        cart_id = request.json.get('cart_id')
        quantity = request.json.get('quantity', 1)
        
        # Update cart item
        result = mongo.db.cart.update_one(
            {'_id': ObjectId(cart_id), 'user_id': ObjectId(session['user_id'])},
            {'$set': {'quantity': quantity, 'updated_at': datetime.utcnow()}}
        )
        
        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Cart updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Cart item not found'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    """Remove item from cart."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please log in'})
    
    try:
        cart_id = request.json.get('cart_id')
        
        # Remove cart item
        result = mongo.db.cart.delete_one({
            '_id': ObjectId(cart_id), 
            'user_id': ObjectId(session['user_id'])
        })
        
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Item removed from cart'})
        else:
            return jsonify({'success': False, 'message': 'Cart item not found'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/cart')
def cart():
    """Shopping cart page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cart_items = list(mongo.db.cart.find({'user_id': ObjectId(session['user_id'])}))
    
    # Get product details for cart items
    cart_with_products = []
    total = 0
    
    for item in cart_items:
        product = mongo.db.products.find_one({'_id': item['product_id']})
        if product:
            item_total = item['quantity'] * item['price']
            cart_with_products.append({
                'cart_item': item,
                'product': product,
                'item_total': item_total
            })
            total += item_total
    
    return render_template('cart_enhanced.html', cart_items=cart_with_products, total=total)

@app.route('/orders')
def orders():
    """User orders page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        user_orders = list(mongo.db.orders.find({'user_id': ObjectId(session['user_id'])})
                          .sort('created_at', -1))
    except Exception as e:
        # Handle case when orders collection doesn't exist or other errors
        print(f"Orders error: {e}")
        user_orders = []
    
    return render_template('orders.html', orders=user_orders)

@app.route('/profile')
def profile():
    """User profile page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
        if not user:
            flash('User not found. Please log in again.', 'error')
            return redirect(url_for('login'))
        return render_template('profile.html', user=user, store_config=store_config)
    except Exception as e:
        print(f"Profile route error: {e}")
        flash('Error loading profile. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/contact')
def contact():
    """Contact page."""
    return render_template('contact.html')

@app.route('/vendors')
def vendors():
    """Vendors listing page."""
    vendors = list(mongo.db.vendors.find({'verification.is_verified': True})
                  .sort('performance.rating', -1))
    return render_template('vendors.html', vendors=vendors)

@app.route('/become_vendor')
def become_vendor():
    """Become vendor page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('become_vendor.html')

@app.route('/checkout')
def checkout():
    """Checkout page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('checkout.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
    if not user or user.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('index'))
    
    return render_template('admin/dashboard.html')

@app.route('/vendor/dashboard')
def vendor_dashboard():
    """Vendor dashboard page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
    if not user or user.get('role') not in ['vendor', 'admin']:
        flash('Vendor access required', 'error')
        return redirect(url_for('index'))
    
    return render_template('vendor/dashboard.html')

# ==================== FOOTER PAGES ====================

@app.route('/help-center')
def help_center():
    """Help Center page with SEO optimization."""
    return render_template('help_center.html')

@app.route('/track-order')
def track_order():
    """Track Order page."""
    return render_template('track_order.html')

@app.route('/returns-refunds')
def returns_refunds():
    """Returns & Refunds policy page."""
    return render_template('returns_refunds.html')

@app.route('/size-guide')
def size_guide():
    """Size Guide page."""
    return render_template('size_guide.html')

@app.route('/flash-deals')
def flash_deals():
    """Flash Deals page with SEO optimization."""
    # Get products with high discounts
    deals = list(mongo.db.products.find({
        'status': 'active',
        'pricing.discount_percentage': {'$gte': 20}
    }).sort('pricing.discount_percentage', -1).limit(50))
    
    return render_template('flash_deals.html', deals=deals)

@app.route('/new-arrivals')
def new_arrivals():
    """New Arrivals page with SEO optimization."""
    # Get recently added products
    arrivals = list(mongo.db.products.find({
        'status': 'active'
    }).sort('created_at', -1).limit(50))
    
    return render_template('new_arrivals.html', arrivals=arrivals)

@app.route('/best-sellers')
def best_sellers():
    """Best Sellers page with SEO optimization."""
    # Get products with high views/sales
    bestsellers = list(mongo.db.products.find({
        'status': 'active'
    }).sort('views', -1).limit(50))
    
    return render_template('best_sellers.html', bestsellers=bestsellers)

@app.route('/gift-cards')
def gift_cards():
    """Gift Cards page."""
    return render_template('gift_cards.html')

@app.route('/seller-center')
def seller_center():
    """Seller Center page."""
    return render_template('seller_center.html')

@app.route('/seller-protection')
def seller_protection():
    """Seller Protection page."""
    return render_template('seller_protection.html')

@app.route('/advertising')
def advertising():
    """Advertising page."""
    return render_template('advertising.html')

@app.route('/success-stories')
def success_stories():
    """Success Stories page."""
    return render_template('success_stories.html')

@app.route('/about')
def about():
    """About Us page with SEO optimization."""
    return render_template('about.html')

@app.route('/careers')
def careers():
    """Careers page."""
    return render_template('careers.html')

@app.route('/press')
def press():
    """Press page."""
    return render_template('press.html')

@app.route('/investor-relations')
def investor_relations():
    """Investor Relations page."""
    return render_template('investor_relations.html')

@app.route('/sustainability')
def sustainability():
    """Sustainability page."""
    return render_template('sustainability.html')

@app.route('/footer-test')
def footer_test():
    """Footer styling test page."""
    return render_template('footer_test.html')

@app.route('/css-test')
def css_test():
    """CSS variables test page."""
    return render_template('css_test.html')

@app.route('/css-debug')
def css_debug():
    """CSS debug test page."""
    # Convert STORE_CONFIG dict to object-like access
    store_config = type('obj', (object,), STORE_CONFIG)()
    return render_template('css_debug.html', store_config=store_config)

@app.route('/privacy-policy')
def privacy_policy():
    """Privacy Policy page."""
    return render_template('privacy_policy.html')

@app.route('/terms-of-service')
def terms_of_service():
    """Terms of Service page."""
    return render_template('terms_of_service.html')

@app.route('/cookie-policy')
def cookie_policy():
    """Cookie Policy page."""
    return render_template('cookie_policy.html')

# ==================== SEO ROUTES ====================

@app.route('/sitemap.xml')
def sitemap():
    """Generate XML sitemap for SEO."""
    from flask import Response
    
    # Get all products for sitemap
    products = list(mongo.db.products.find({'status': 'active'}))
    categories = list(set([cat['name'] for cat in PRODUCT_CATEGORIES]))
    
    sitemap_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>http://127.0.0.1:5002/</loc>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>http://127.0.0.1:5002/products</loc>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>
    <url>
        <loc>http://127.0.0.1:5002/flash-deals</loc>
        <changefreq>daily</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>http://127.0.0.1:5002/new-arrivals</loc>
        <changefreq>daily</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>http://127.0.0.1:5002/best-sellers</loc>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>'''
    
    # Add product pages
    for product in products:
        sitemap_xml += f'''
    <url>
        <loc>http://127.0.0.1:5002/product/{product['_id']}</loc>
        <changefreq>weekly</changefreq>
        <priority>0.7</priority>
    </url>'''
    
    # Add category pages
    for category in categories:
        sitemap_xml += f'''
    <url>
        <loc>http://127.0.0.1:5002/products?category={category}</loc>
        <changefreq>weekly</changefreq>
        <priority>0.6</priority>
    </url>'''
    
    sitemap_xml += '''
</urlset>'''
    
    return Response(sitemap_xml, mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    """Generate robots.txt for SEO."""
    from flask import Response
    
    robots_txt = '''User-agent: *
Allow: /
Disallow: /admin/
Disallow: /vendor/
Disallow: /cart
Disallow: /checkout
Disallow: /login
Disallow: /register
Disallow: /api/

Sitemap: http://127.0.0.1:5002/sitemap.xml'''
    
    return Response(robots_txt, mimetype='text/plain')

if __name__ == '__main__':
    # Initialize sample data if needed
    with app.app_context():
        # Create indexes for better performance
        mongo.db.users.create_index('username', unique=True)
        mongo.db.users.create_index('email', unique=True)
        mongo.db.products.create_index([('basic_info.name', 'text'), ('basic_info.description', 'text')])
        mongo.db.products.create_index('basic_info.category')
        mongo.db.products.create_index('pricing.price')
        mongo.db.products.create_index('status')
        
        # Create admin user if doesn't exist
        if not mongo.db.users.find_one({'username': 'admin'}):
            admin_user = {
                'username': 'admin',
                'email': 'admin@markethubpro.com',
                'password': generate_password_hash('admin123'),
                'role': 'admin',
                'profile': {
                    'first_name': 'Admin',
                    'last_name': 'User',
                    'avatar_url': '',
                    'phone': '',
                    'date_of_birth': None,
                    'gender': ''
                },
                'addresses': [],
                'preferences': {
                    'language': 'en',
                    'currency': 'USD',
                    'notifications': {
                        'email': True,
                        'sms': False,
                        'push': True
                    }
                },
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'last_login': None,
                'is_active': True,
                'email_verified': True
            }
            mongo.db.users.insert_one(admin_user)
            print("✅ Admin user created (username: admin, password: admin123)")
    
    app.run(debug=True, port=5002)