from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from config import config, STORE_CONFIG

# Create Flask app with configuration
app = Flask(__name__)
config_name = os.environ.get('FLASK_CONFIG') or 'default'
app.config.from_object(config[config_name])

db = SQLAlchemy(app)

# Make store config available to templates
@app.context_processor
def inject_store_config():
    return dict(store_config=STORE_CONFIG)

# Custom template filters
@app.template_filter('from_json')
def from_json_filter(value):
    """Parse JSON string in templates."""
    import json
    try:
        return json.loads(value) if value else {}
    except (json.JSONDecodeError, TypeError):
        return {}

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='user')  # user, vendor, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Vendor-specific fields
    business_name = db.Column(db.String(100))
    business_description = db.Column(db.Text)
    business_address = db.Column(db.Text)
    business_phone = db.Column(db.String(20))
    is_verified = db.Column(db.Boolean, default=False)
    commission_rate = db.Column(db.Float, default=5.0)  # Platform commission percentage

class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    business_name = db.Column(db.String(100), nullable=False)
    business_description = db.Column(db.Text)
    business_address = db.Column(db.Text)
    business_phone = db.Column(db.String(20))
    business_email = db.Column(db.String(120))
    logo_url = db.Column(db.String(200))
    banner_url = db.Column(db.String(200))
    is_verified = db.Column(db.Boolean, default=False)
    commission_rate = db.Column(db.Float, default=5.0)
    total_sales = db.Column(db.Float, default=0.0)
    rating = db.Column(db.Float, default=0.0)
    total_reviews = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='vendor_profile')
    products = db.relationship('Product', backref='vendor', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50))
    image_url = db.Column(db.String(200))
    
    # Multi-vendor fields
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=True)
    is_featured = db.Column(db.Boolean, default=False)
    discount_percentage = db.Column(db.Float, default=0.0)
    tags = db.Column(db.String(200))  # Comma-separated tags
    weight = db.Column(db.Float)  # For shipping calculations
    dimensions = db.Column(db.String(50))  # LxWxH
    brand = db.Column(db.String(50))
    sku = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(20), default='active')  # active, inactive, pending
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    order_status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Enhanced order fields
    order_number = db.Column(db.String(20), unique=True)
    payment_method = db.Column(db.String(20))  # stripe, paypal, mpesa
    payment_status = db.Column(db.String(20), default='pending')
    payment_id = db.Column(db.String(100))  # External payment ID
    shipping_address = db.Column(db.Text)
    billing_address = db.Column(db.Text)
    shipping_cost = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    tracking_number = db.Column(db.String(50))
    estimated_delivery = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    commission_amount = db.Column(db.Float, default=0.0)
    vendor_earnings = db.Column(db.Float, default=0.0)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # stripe, paypal, mpesa
    payment_id = db.Column(db.String(100))  # External payment ID
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed, refunded
    transaction_fee = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Payment gateway specific fields
    stripe_payment_intent_id = db.Column(db.String(100))
    paypal_payment_id = db.Column(db.String(100))
    mpesa_checkout_request_id = db.Column(db.String(100))
    mpesa_receipt_number = db.Column(db.String(50))

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    title = db.Column(db.String(100))
    comment = db.Column(db.Text)
    is_verified_purchase = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='reviews')
    product = db.relationship('Product', backref='reviews')

class VendorEarnings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    gross_amount = db.Column(db.Float, nullable=False)
    commission_amount = db.Column(db.Float, nullable=False)
    net_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, paid, on_hold
    payout_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TradeAssurance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, claimed, resolved, expired
    protection_type = db.Column(db.String(50), nullable=False)  # quality, delivery, refund
    description = db.Column(db.Text)
    claim_reason = db.Column(db.Text)
    resolution = db.Column(db.Text)
    expires_at = db.Column(db.DateTime, nullable=False)
    claimed_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    order = db.relationship('Order', backref='trade_assurance')
    vendor = db.relationship('Vendor', backref='trade_assurances')
    customer = db.relationship('User', backref='trade_assurances')

class AdminAction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # user_action, vendor_action, order_action, etc.
    target_type = db.Column(db.String(50), nullable=False)  # user, vendor, order, product
    target_id = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    details = db.Column(db.Text)  # JSON string for additional details
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    admin = db.relationship('User', backref='admin_actions')

class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='general')
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    updated_by_user = db.relationship('User', backref='system_settings_updates')

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
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            flash('Admin access required')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def vendor_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.role not in ['vendor', 'admin']:
            flash('Vendor access required')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def generate_order_number():
    """Generate a unique order number."""
    import random
    import string
    timestamp = datetime.now().strftime('%Y%m%d')
    random_part = ''.join(random.choices(string.digits, k=4))
    return f"ORD-{timestamp}-{random_part}"

# Routes
@app.route('/')
def index():
    products = Product.query.limit(8).all()
    return render_template('index.html', products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/products')
def products():
    category = request.args.get('category')
    search = request.args.get('search')
    sort_by = request.args.get('sort', 'name')
    
    query = Product.query
    
    if category:
        query = query.filter_by(category=category)
    
    if search:
        query = query.filter(Product.name.contains(search))
    
    if sort_by == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.name)
    
    products = query.all()
    categories = db.session.query(Product.category).distinct().all()
    
    return render_template('products.html', products=products, categories=categories)

@app.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template('product_detail.html', product=product)

@app.route('/contact')
def contact():
    return render_template('contact.html')

# Vendor Registration and Management Routes
@app.route('/become_vendor', methods=['GET', 'POST'])
@login_required
def become_vendor():
    user = User.query.get(session['user_id'])
    
    # Check if user is already a vendor
    if user.role == 'vendor':
        flash('You are already a vendor')
        return redirect(url_for('vendor_dashboard'))
    
    if request.method == 'POST':
        # Create vendor profile
        vendor = Vendor(
            user_id=user.id,
            business_name=request.form['business_name'],
            business_description=request.form['business_description'],
            business_address=request.form['business_address'],
            business_phone=request.form['business_phone'],
            business_email=request.form['business_email']
        )
        
        # Update user role
        user.role = 'vendor'
        
        db.session.add(vendor)
        db.session.commit()
        
        flash('Vendor application submitted successfully! Awaiting admin approval.')
        return redirect(url_for('vendor_dashboard'))
    
    return render_template('become_vendor.html')

@app.route('/vendor_dashboard')
@vendor_required
def vendor_dashboard():
    user = User.query.get(session['user_id'])
    vendor = Vendor.query.filter_by(user_id=user.id).first()
    
    if not vendor:
        return redirect(url_for('become_vendor'))
    
    # Get vendor statistics
    total_products = Product.query.filter_by(vendor_id=vendor.id).count()
    total_orders = db.session.query(OrderItem).filter_by(vendor_id=vendor.id).count()
    total_earnings = db.session.query(db.func.sum(VendorEarnings.net_amount)).filter_by(
        vendor_id=vendor.id, status='paid'
    ).scalar() or 0
    
    recent_orders = db.session.query(Order, OrderItem).join(OrderItem).filter(
        OrderItem.vendor_id == vendor.id
    ).order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('vendor/dashboard.html',
                         vendor=vendor,
                         total_products=total_products,
                         total_orders=total_orders,
                         total_earnings=total_earnings,
                         recent_orders=recent_orders)

@app.route('/vendor/products')
@vendor_required
def vendor_products():
    user = User.query.get(session['user_id'])
    vendor = Vendor.query.filter_by(user_id=user.id).first()
    
    if not vendor:
        flash('Please complete your vendor registration first')
        return redirect(url_for('become_vendor'))
    
    products = Product.query.filter_by(vendor_id=vendor.id).all()
    return render_template('vendor/products.html', products=products, vendor=vendor)

@app.route('/vendor/add_product', methods=['GET', 'POST'])
@vendor_required
def vendor_add_product():
    user = User.query.get(session['user_id'])
    vendor = Vendor.query.filter_by(user_id=user.id).first()
    
    if not vendor:
        flash('Please complete your vendor registration first')
        return redirect(url_for('become_vendor'))
    
    if request.method == 'POST':
        import uuid
        sku = f"SKU-{uuid.uuid4().hex[:8].upper()}"
        
        product = Product(
            name=request.form['name'],
            description=request.form['description'],
            price=float(request.form['price']),
            stock=int(request.form['stock']),
            category=request.form['category'],
            image_url=request.form['image_url'],
            vendor_id=vendor.id,
            brand=request.form.get('brand', ''),
            sku=sku,
            weight=float(request.form.get('weight', 0) or 0),
            dimensions=request.form.get('dimensions', ''),
            tags=request.form.get('tags', ''),
            discount_percentage=float(request.form.get('discount_percentage', 0) or 0)
        )
        
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully')
        return redirect(url_for('vendor_products'))
    
    return render_template('vendor/add_product.html', vendor=vendor)

@app.route('/vendor/edit_product/<int:id>', methods=['GET', 'POST'])
@vendor_required
def vendor_edit_product(id):
    user = User.query.get(session['user_id'])
    vendor = Vendor.query.filter_by(user_id=user.id).first()
    product = Product.query.filter_by(id=id, vendor_id=vendor.id).first_or_404()
    
    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = float(request.form['price'])
        product.stock = int(request.form['stock'])
        product.category = request.form['category']
        product.image_url = request.form['image_url']
        product.brand = request.form.get('brand', '')
        product.weight = float(request.form.get('weight', 0) or 0)
        product.dimensions = request.form.get('dimensions', '')
        product.tags = request.form.get('tags', '')
        product.discount_percentage = float(request.form.get('discount_percentage', 0) or 0)
        product.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Product updated successfully')
        return redirect(url_for('vendor_products'))
    
    return render_template('vendor/edit_product.html', product=product, vendor=vendor)

@app.route('/vendor/orders')
@vendor_required
def vendor_orders():
    user = User.query.get(session['user_id'])
    vendor = Vendor.query.filter_by(user_id=user.id).first()
    
    if not vendor:
        flash('Please complete your vendor registration first')
        return redirect(url_for('become_vendor'))
    
    # Simplified query to avoid join ambiguity
    order_items = OrderItem.query.filter_by(vendor_id=vendor.id).all()
    orders_data = []
    
    for item in order_items:
        order = Order.query.get(item.order_id)
        product = Product.query.get(item.product_id)
        orders_data.append({
            'order': order,
            'order_item': item,
            'product': product
        })
    
    # Sort by order creation date (newest first)
    orders_data.sort(key=lambda x: x['order'].created_at, reverse=True)
    
    return render_template('vendor/orders.html', orders_data=orders_data, vendor=vendor)

@app.route('/vendors')
def vendors():
    vendors = Vendor.query.filter_by(is_verified=True).all()
    return render_template('vendors.html', vendors=vendors)

@app.route('/vendor/<int:id>')
def vendor_profile(id):
    vendor = Vendor.query.get_or_404(id)
    products = Product.query.filter_by(vendor_id=vendor.id, status='active').all()
    return render_template('vendor_profile.html', vendor=vendor, products=products)

# Enhanced Payment Routes
@app.route('/payment/<payment_method>')
@login_required
def payment_page(payment_method):
    if payment_method not in ['stripe', 'paypal', 'mpesa']:
        flash('Invalid payment method')
        return redirect(url_for('checkout'))
    
    cart_items = db.session.query(Cart, Product).join(Product).filter(
        Cart.user_id == session['user_id']
    ).all()
    
    if not cart_items:
        flash('Your cart is empty')
        return redirect(url_for('cart'))
    
    total = sum(item.Cart.quantity * item.Product.price for item in cart_items)
    
    return render_template(f'payment/{payment_method}.html', 
                         cart_items=cart_items, 
                         total=total,
                         payment_method=payment_method)

@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    from payment_services import PaymentServiceFactory
    
    payment_method = request.json.get('payment_method')
    order_id = request.json.get('order_id')
    
    try:
        payment_service = PaymentServiceFactory.get_service(payment_method)
        
        if payment_method == 'stripe':
            result = payment_service.create_payment_intent(
                amount=request.json.get('amount'),
                metadata={'order_id': order_id}
            )
        elif payment_method == 'paypal':
            result = payment_service.create_payment(
                amount=request.json.get('amount'),
                return_url=url_for('payment_success', _external=True),
                cancel_url=url_for('payment_cancel', _external=True)
            )
        elif payment_method == 'mpesa':
            result = payment_service.stk_push(
                phone_number=request.json.get('phone_number'),
                amount=request.json.get('amount'),
                account_reference=f"Order-{order_id}",
                transaction_desc="E-commerce payment",
                callback_url=url_for('mpesa_callback', _external=True)
            )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/payment/success')
@login_required
def payment_success():
    return render_template('payment/success.html')

@app.route('/payment/cancel')
@login_required
def payment_cancel():
    return render_template('payment/cancel.html')

@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    # Handle M-Pesa callback
    callback_data = request.json
    # Process the callback and update payment status
    # This would typically update the Payment and Order models
    return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'})

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    product_id = request.json.get('product_id')
    quantity = request.json.get('quantity', 1)
    
    existing_cart_item = Cart.query.filter_by(
        user_id=session['user_id'], 
        product_id=product_id
    ).first()
    
    if existing_cart_item:
        existing_cart_item.quantity += quantity
    else:
        cart_item = Cart(
            user_id=session['user_id'],
            product_id=product_id,
            quantity=quantity
        )
        db.session.add(cart_item)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Added to cart'})

@app.route('/cart')
@login_required
def cart():
    cart_items = db.session.query(Cart, Product).join(Product).filter(
        Cart.user_id == session['user_id']
    ).all()
    
    total = sum(item.Cart.quantity * item.Product.price for item in cart_items)
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/update_cart', methods=['POST'])
@login_required
def update_cart():
    cart_id = request.json.get('cart_id')
    quantity = request.json.get('quantity')
    
    cart_item = Cart.query.get(cart_id)
    if cart_item and cart_item.user_id == session['user_id']:
        if quantity <= 0:
            db.session.delete(cart_item)
        else:
            cart_item.quantity = quantity
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False})

@app.route('/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    cart_id = request.json.get('cart_id')
    
    cart_item = Cart.query.get(cart_id)
    if cart_item and cart_item.user_id == session['user_id']:
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False})

@app.route('/checkout')
@login_required
def checkout():
    # Get cart items with product and vendor information
    cart_items = db.session.query(Cart, Product).join(Product).filter(
        Cart.user_id == session['user_id']
    ).all()
    
    if not cart_items:
        flash('Your cart is empty')
        return redirect(url_for('cart'))
    
    # Calculate totals
    subtotal = sum(item.Cart.quantity * item.Product.price for item in cart_items)
    shipping_cost = 10.0  # Fixed shipping for now
    tax_rate = 0.08  # 8% tax
    tax_amount = subtotal * tax_rate
    total = subtotal + shipping_cost + tax_amount
    
    # Group items by vendor for multi-vendor support
    vendor_groups = {}
    for item in cart_items:
        vendor_id = item.Product.vendor_id or 0  # 0 for admin products
        
        # Get vendor information if exists
        vendor = None
        if item.Product.vendor_id:
            vendor = Vendor.query.get(item.Product.vendor_id)
        
        vendor_name = vendor.business_name if vendor else "E-Store"
        
        if vendor_id not in vendor_groups:
            vendor_groups[vendor_id] = {
                'vendor_name': vendor_name,
                'vendor_items': [],  # Changed from 'items' to 'vendor_items' to avoid conflict
                'subtotal': 0
            }
        
        # Create a tuple-like object for template compatibility
        item_with_vendor = type('ItemWithVendor', (), {
            'Cart': item.Cart,
            'Product': item.Product,
            'Vendor': vendor
        })()
        
        vendor_groups[vendor_id]['vendor_items'].append(item_with_vendor)
        vendor_groups[vendor_id]['subtotal'] += item.Cart.quantity * item.Product.price
    
    return render_template('checkout.html', 
                         cart_items=cart_items,
                         vendor_groups=vendor_groups,
                         subtotal=subtotal,
                         shipping_cost=shipping_cost,
                         tax_amount=tax_amount,
                         total=total)

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    # Get cart items with product information
    cart_items = db.session.query(Cart, Product).join(Product).filter(
        Cart.user_id == session['user_id']
    ).all()
    
    if not cart_items:
        return jsonify({'success': False, 'message': 'Cart is empty'})
    
    # Calculate totals
    subtotal = sum(item.Cart.quantity * item.Product.price for item in cart_items)
    shipping_cost = 10.0
    tax_rate = 0.08
    tax_amount = subtotal * tax_rate
    total = subtotal + shipping_cost + tax_amount
    
    # Create order
    import json
    order = Order(
        user_id=session['user_id'],
        total_price=total,
        order_number=generate_order_number(),
        shipping_address=json.dumps(request.json.get('shipping_address', {})),
        billing_address=json.dumps(request.json.get('billing_address', {})),
        shipping_cost=shipping_cost,
        tax_amount=tax_amount,
        payment_method=request.json.get('payment_method', 'pending')
    )
    
    db.session.add(order)
    db.session.flush()  # Get order ID
    
    # Create order items, vendor earnings, and trade assurance
    for item in cart_items:
        vendor_id = item.Product.vendor_id
        commission_rate = 5.0  # Default commission
        
        if vendor_id:
            vendor = Vendor.query.get(vendor_id)
            if vendor:
                commission_rate = vendor.commission_rate
        
        item_total = item.Cart.quantity * item.Product.price
        commission_amount = item_total * (commission_rate / 100)
        vendor_earnings = item_total - commission_amount
        
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.Product.id,
            vendor_id=vendor_id,
            quantity=item.Cart.quantity,
            price=item.Product.price,
            commission_amount=commission_amount,
            vendor_earnings=vendor_earnings
        )
        db.session.add(order_item)
        
        # Create vendor earnings record
        if vendor_id:
            earnings = VendorEarnings(
                vendor_id=vendor_id,
                order_id=order.id,
                gross_amount=item_total,
                commission_amount=commission_amount,
                net_amount=vendor_earnings
            )
            db.session.add(earnings)
            
            # Create trade assurance for vendor orders
            from datetime import timedelta
            trade_assurance = TradeAssurance(
                order_id=order.id,
                vendor_id=vendor_id,
                customer_id=session['user_id'],
                amount=item_total,
                protection_type='quality',  # Default protection type
                description=f'Trade assurance for {item.Product.name}',
                expires_at=datetime.utcnow() + timedelta(days=30)  # 30 days protection
            )
            db.session.add(trade_assurance)
        
        # Update product stock
        item.Product.stock -= item.Cart.quantity
        
        # Remove from cart
        db.session.delete(item.Cart)
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'order_id': order.id,
        'order_number': order.order_number,
        'total': total
    })

@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=session['user_id']).order_by(
        Order.created_at.desc()
    ).all()
    return render_template('orders.html', orders=user_orders)

@app.route('/order/<int:order_id>/claim_trade_assurance', methods=['POST'])
@login_required
def claim_trade_assurance(order_id):
    order = Order.query.filter_by(id=order_id, user_id=session['user_id']).first_or_404()
    
    # Find active trade assurances for this order
    assurances = TradeAssurance.query.filter_by(
        order_id=order_id,
        customer_id=session['user_id'],
        status='active'
    ).all()
    
    if not assurances:
        return jsonify({'success': False, 'message': 'No active trade assurance found for this order'})
    
    claim_reason = request.json.get('reason', '')
    
    # Update all assurances for this order to claimed status
    for assurance in assurances:
        assurance.status = 'claimed'
        assurance.claim_reason = claim_reason
        assurance.claimed_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('Trade assurance claim submitted successfully. Our team will review it shortly.')
    return jsonify({'success': True, 'message': 'Claim submitted successfully'})

@app.route('/trade_assurance_info')
def trade_assurance_info():
    return render_template('trade_assurance_info.html')

@app.route('/profile')
@login_required
def profile():
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

# Admin Routes
@app.route('/admin')
@admin_required
def admin_dashboard():
    # Basic stats
    total_users = User.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_vendors = Vendor.query.count()
    
    # Revenue stats
    total_revenue = db.session.query(db.func.sum(Order.total_price)).filter(
        Order.payment_status == 'completed'
    ).scalar() or 0
    
    pending_orders = Order.query.filter_by(order_status='pending').count()
    active_trade_assurances = TradeAssurance.query.filter_by(status='active').count()
    
    # Recent activities
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_vendors = Vendor.query.order_by(Vendor.created_at.desc()).limit(5).all()
    
    # Trade assurance claims
    pending_claims = TradeAssurance.query.filter_by(status='claimed').count()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_products=total_products,
                         total_orders=total_orders,
                         total_vendors=total_vendors,
                         total_revenue=total_revenue,
                         pending_orders=pending_orders,
                         active_trade_assurances=active_trade_assurances,
                         pending_claims=pending_claims,
                         recent_orders=recent_orders,
                         recent_users=recent_users,
                         recent_vendors=recent_vendors)

@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/vendors')
@admin_required
def admin_vendors():
    vendors = Vendor.query.order_by(Vendor.created_at.desc()).all()
    return render_template('admin/vendors.html', vendors=vendors)

@app.route('/admin/vendor/<int:id>/verify', methods=['POST'])
@admin_required
def verify_vendor(id):
    vendor = Vendor.query.get_or_404(id)
    vendor.is_verified = True
    
    # Log admin action
    action = AdminAction(
        admin_id=session['user_id'],
        action_type='vendor_verification',
        target_type='vendor',
        target_id=vendor.id,
        description=f'Verified vendor: {vendor.business_name}'
    )
    db.session.add(action)
    db.session.commit()
    
    flash(f'Vendor {vendor.business_name} has been verified')
    return redirect(url_for('admin_vendors'))

@app.route('/admin/trade_assurance')
@admin_required
def admin_trade_assurance():
    assurances = TradeAssurance.query.order_by(TradeAssurance.created_at.desc()).all()
    return render_template('admin/trade_assurance.html', assurances=assurances)

@app.route('/admin/trade_assurance/<int:id>/resolve', methods=['POST'])
@admin_required
def resolve_trade_assurance(id):
    assurance = TradeAssurance.query.get_or_404(id)
    resolution = request.form.get('resolution')
    action = request.form.get('action')  # approve_claim, reject_claim
    
    if action == 'approve_claim':
        assurance.status = 'resolved'
        assurance.resolution = resolution
        assurance.resolved_at = datetime.utcnow()
        
        # Process refund or compensation logic here
        flash('Trade assurance claim approved and resolved')
    elif action == 'reject_claim':
        assurance.status = 'active'
        assurance.resolution = resolution
        flash('Trade assurance claim rejected')
    
    # Log admin action
    admin_action = AdminAction(
        admin_id=session['user_id'],
        action_type='trade_assurance_resolution',
        target_type='trade_assurance',
        target_id=assurance.id,
        description=f'Resolved trade assurance claim: {action}',
        details=resolution
    )
    db.session.add(admin_action)
    db.session.commit()
    
    return redirect(url_for('admin_trade_assurance'))

@app.route('/admin/settings')
@admin_required
def admin_settings():
    settings = SystemSettings.query.all()
    settings_by_category = {}
    for setting in settings:
        if setting.category not in settings_by_category:
            settings_by_category[setting.category] = []
        settings_by_category[setting.category].append(setting)
    
    return render_template('admin/settings.html', settings_by_category=settings_by_category)

@app.route('/admin/settings/update', methods=['POST'])
@admin_required
def update_settings():
    for key, value in request.form.items():
        if key.startswith('setting_'):
            setting_key = key.replace('setting_', '')
            setting = SystemSettings.query.filter_by(key=setting_key).first()
            if setting:
                setting.value = value
                setting.updated_by = session['user_id']
                setting.updated_at = datetime.utcnow()
    
    db.session.commit()
    flash('Settings updated successfully')
    return redirect(url_for('admin_settings'))

@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    # Sales analytics
    from sqlalchemy import func, extract
    
    # Monthly sales
    monthly_sales = db.session.query(
        extract('month', Order.created_at).label('month'),
        func.sum(Order.total_price).label('total')
    ).filter(Order.payment_status == 'completed').group_by(
        extract('month', Order.created_at)
    ).all()
    
    # Top selling products
    top_products = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('total_sold')
    ).join(OrderItem).group_by(Product.id).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(10).all()
    
    # Vendor performance
    vendor_performance = db.session.query(
        Vendor.business_name,
        func.sum(VendorEarnings.gross_amount).label('total_sales'),
        func.count(OrderItem.id).label('total_orders')
    ).join(VendorEarnings).join(OrderItem, VendorEarnings.order_id == OrderItem.order_id).group_by(
        Vendor.id
    ).order_by(func.sum(VendorEarnings.gross_amount).desc()).limit(10).all()
    
    return render_template('admin/analytics.html',
                         monthly_sales=monthly_sales,
                         top_products=top_products,
                         vendor_performance=vendor_performance)

@app.route('/admin/logs')
@admin_required
def admin_logs():
    logs = AdminAction.query.order_by(AdminAction.created_at.desc()).limit(100).all()
    return render_template('admin/logs.html', logs=logs)

@app.route('/admin/products')
@admin_required
def admin_products():
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/add_product', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        product = Product(
            name=request.form['name'],
            description=request.form['description'],
            price=float(request.form['price']),
            stock=int(request.form['stock']),
            category=request.form['category'],
            image_url=request.form['image_url']
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/add_product.html')

@app.route('/admin/edit_product/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = float(request.form['price'])
        product.stock = int(request.form['stock'])
        product.category = request.form['category']
        product.image_url = request.form['image_url']
        
        db.session.commit()
        flash('Product updated successfully')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/edit_product.html', product=product)

@app.route('/admin/delete_product/<int:id>')
@admin_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully')
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/update_order_status', methods=['POST'])
@admin_required
def update_order_status():
    order_id = request.json.get('order_id')
    status = request.json.get('status')
    
    order = Order.query.get(order_id)
    if order:
        order.order_status = status
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create admin user if doesn't exist
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@example.com',
                password=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
        
        # Initialize system settings
        default_settings = [
            ('site_name', 'E-Store', 'Website name', 'general'),
            ('site_description', 'Modern Multi-Vendor Marketplace', 'Website description', 'general'),
            ('commission_rate', '5.0', 'Default commission rate for vendors (%)', 'financial'),
            ('trade_assurance_period', '30', 'Trade assurance protection period (days)', 'trade_assurance'),
            ('auto_approve_vendors', 'false', 'Automatically approve new vendors', 'vendors'),
            ('min_order_amount', '10.0', 'Minimum order amount', 'orders'),
            ('shipping_cost', '10.0', 'Default shipping cost', 'shipping'),
            ('tax_rate', '8.0', 'Tax rate (%)', 'financial'),
            ('currency', 'USD', 'Default currency', 'general'),
            ('currency_symbol', '$', 'Currency symbol', 'general'),
        ]
        
        for key, value, description, category in default_settings:
            if not SystemSettings.query.filter_by(key=key).first():
                setting = SystemSettings(
                    key=key,
                    value=value,
                    description=description,
                    category=category
                )
                db.session.add(setting)
        
        db.session.commit()
    
    app.run(debug=True)