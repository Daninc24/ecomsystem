"""
SQLite Database Models for E-commerce System
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

# Association tables for many-to-many relationships
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

product_categories = db.Table('product_categories',
    db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

order_products = db.Table('order_products',
    db.Column('order_id', db.Integer, db.ForeignKey('order.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True),
    db.Column('quantity', db.Integer, nullable=False, default=1),
    db.Column('price', db.Float, nullable=False)
)


class User(UserMixin, db.Model):
    """User model"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_vendor = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    
    # Relationships
    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
                           backref=db.backref('users', lazy=True))
    orders = db.relationship('Order', backref='user', lazy=True)
    addresses = db.relationship('Address', backref='user', lazy=True)
    products = db.relationship('Product', backref='vendor', lazy=True)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password"""
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role_name):
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles)
    
    def get_full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'is_vendor': self.is_vendor,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'roles': [role.name for role in self.roles]
        }


class Role(db.Model):
    """Role model"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    permissions = db.Column(db.Text)  # JSON string of permissions
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def get_permissions(self):
        """Get permissions as list"""
        if self.permissions:
            return json.loads(self.permissions)
        return []
    
    def set_permissions(self, permissions_list):
        """Set permissions from list"""
        self.permissions = json.dumps(permissions_list)


class Category(db.Model):
    """Product category model"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Self-referential relationship
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    
    def get_path(self):
        """Get category path"""
        path = [self.name]
        parent = self.parent
        while parent:
            path.insert(0, parent.name)
            parent = parent.parent
        return ' > '.join(path)


class Product(db.Model):
    """Product model"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    short_description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False, index=True)
    compare_price = db.Column(db.Float)  # Original price for discounts
    cost_price = db.Column(db.Float)  # Cost for profit calculations
    sku = db.Column(db.String(100), unique=True, index=True)
    barcode = db.Column(db.String(100))
    inventory_quantity = db.Column(db.Integer, default=0)
    track_inventory = db.Column(db.Boolean, default=True)
    allow_backorder = db.Column(db.Boolean, default=False)
    weight = db.Column(db.Float)
    dimensions = db.Column(db.String(100))  # "L x W x H"
    images = db.Column(db.Text)  # JSON array of image URLs
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_featured = db.Column(db.Boolean, default=False, index=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    categories = db.relationship('Category', secondary=product_categories, lazy='subquery',
                                backref=db.backref('products', lazy=True))
    
    def get_images(self):
        """Get images as list"""
        if self.images:
            return json.loads(self.images)
        return []
    
    def set_images(self, images_list):
        """Set images from list"""
        self.images = json.dumps(images_list)
    
    def get_main_image(self):
        """Get main product image"""
        images = self.get_images()
        return images[0] if images else '/static/images/no-image.png'
    
    def get_discount_percentage(self):
        """Calculate discount percentage"""
        if self.compare_price and self.compare_price > self.price:
            return int(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0
    
    def is_in_stock(self):
        """Check if product is in stock"""
        if not self.track_inventory:
            return True
        return self.inventory_quantity > 0 or self.allow_backorder
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'short_description': self.short_description,
            'price': self.price,
            'compare_price': self.compare_price,
            'sku': self.sku,
            'inventory_quantity': self.inventory_quantity,
            'images': self.get_images(),
            'main_image': self.get_main_image(),
            'is_active': self.is_active,
            'is_featured': self.is_featured,
            'is_in_stock': self.is_in_stock(),
            'discount_percentage': self.get_discount_percentage(),
            'categories': [cat.name for cat in self.categories],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Order(db.Model):
    """Order model"""
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), default='pending', nullable=False, index=True)
    subtotal = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, default=0)
    shipping_amount = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    payment_status = db.Column(db.String(50), default='pending', index=True)
    payment_method = db.Column(db.String(50))
    payment_reference = db.Column(db.String(100))
    shipping_address = db.Column(db.Text)  # JSON string
    billing_address = db.Column(db.Text)   # JSON string
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    shipped_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def get_shipping_address(self):
        """Get shipping address as dict"""
        if self.shipping_address:
            return json.loads(self.shipping_address)
        return {}
    
    def set_shipping_address(self, address_dict):
        """Set shipping address from dict"""
        self.shipping_address = json.dumps(address_dict)
    
    def get_billing_address(self):
        """Get billing address as dict"""
        if self.billing_address:
            return json.loads(self.billing_address)
        return {}
    
    def set_billing_address(self, address_dict):
        """Set billing address from dict"""
        self.billing_address = json.dumps(address_dict)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'order_number': self.order_number,
            'status': self.status,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'shipping_amount': self.shipping_amount,
            'discount_amount': self.discount_amount,
            'total_amount': self.total_amount,
            'currency': self.currency,
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'shipped_at': self.shipped_at.isoformat() if self.shipped_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'items': [item.to_dict() for item in self.items]
        }


class OrderItem(db.Model):
    """Order item model"""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)  # Snapshot of product name
    product_sku = db.Column(db.String(100))  # Snapshot of SKU
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    
    # Relationships
    product = db.relationship('Product', backref='order_items')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'product_sku': self.product_sku,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total_price': self.total_price
        }


class Address(db.Model):
    """Address model"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'shipping' or 'billing'
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    company = db.Column(db.String(100))
    address_line_1 = db.Column(db.String(200), nullable=False)
    address_line_2 = db.Column(db.String(200))
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100))
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'type': self.type,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'company': self.company,
            'address_line_1': self.address_line_1,
            'address_line_2': self.address_line_2,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'phone': self.phone,
            'is_default': self.is_default
        }


class AdminSetting(db.Model):
    """Admin settings model"""
    __tablename__ = 'admin_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text)
    data_type = db.Column(db.String(20), default='string')  # string, number, boolean, json
    is_sensitive = db.Column(db.Boolean, default=False)
    requires_restart = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def get_value(self):
        """Get typed value"""
        if self.data_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on') if self.value else False
        elif self.data_type == 'number':
            try:
                return float(self.value) if self.value else 0
            except (ValueError, TypeError):
                return 0
        elif self.data_type == 'json':
            try:
                return json.loads(self.value) if self.value else {}
            except (json.JSONDecodeError, TypeError):
                return {}
        return self.value or ''
    
    def set_value(self, value):
        """Set typed value"""
        if self.data_type == 'json':
            self.value = json.dumps(value)
        else:
            self.value = str(value)


class ActivityLog(db.Model):
    """Activity log model for admin actions"""
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(50), index=True)
    resource_id = db.Column(db.String(50))
    details = db.Column(db.Text)  # JSON string
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    success = db.Column(db.Boolean, default=True, index=True)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationships
    user = db.relationship('User', backref='activity_logs')
    
    def get_details(self):
        """Get details as dict"""
        if self.details:
            try:
                return json.loads(self.details)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_details(self, details_dict):
        """Set details from dict"""
        self.details = json.dumps(details_dict)


def init_db(app):
    """Initialize database with app"""
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create default roles if they don't exist
        create_default_roles()
        
        # Create admin user if it doesn't exist
        create_admin_user(app)


def create_default_roles():
    """Create default roles"""
    default_roles = [
        {
            'name': 'admin',
            'description': 'Full system administrator',
            'permissions': ['*'],  # All permissions
            'is_default': False
        },
        {
            'name': 'vendor',
            'description': 'Product vendor',
            'permissions': ['product.create', 'product.edit', 'product.delete', 'order.view'],
            'is_default': False
        },
        {
            'name': 'customer',
            'description': 'Regular customer',
            'permissions': ['order.view', 'profile.edit'],
            'is_default': True
        }
    ]
    
    for role_data in default_roles:
        role = Role.query.filter_by(name=role_data['name']).first()
        if not role:
            role = Role(
                name=role_data['name'],
                description=role_data['description'],
                is_default=role_data['is_default']
            )
            role.set_permissions(role_data['permissions'])
            db.session.add(role)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Role creation skipped: {str(e)}")


def create_admin_user(app):
    """Create admin user if it doesn't exist"""
    admin_email = app.config.get('ADMIN_EMAIL', 'admin@markethubpro.com')
    admin_password = app.config.get('ADMIN_PASSWORD', 'admin123')
    
    admin_user = User.query.filter_by(email=admin_email).first()
    if not admin_user:
        admin_role = Role.query.filter_by(name='admin').first()
        
        admin_user = User(
            username='admin',
            email=admin_email,
            first_name='System',
            last_name='Administrator',
            is_active=True,
            is_verified=True
        )
        admin_user.set_password(admin_password)
        
        if admin_role:
            admin_user.roles.append(admin_role)
        
        db.session.add(admin_user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Admin user creation skipped: {str(e)}")
    else:
        # Ensure admin user has admin role
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role and admin_role not in admin_user.roles:
            admin_user.roles.append(admin_role)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()


def create_default_settings():
    """Create default admin settings"""
    default_settings = [
        {
            'key': 'site_name',
            'value': 'MarketHub Pro',
            'category': 'general',
            'description': 'The name of the website',
            'data_type': 'string'
        },
        {
            'key': 'site_description',
            'value': 'Your premier e-commerce marketplace',
            'category': 'general',
            'description': 'Site description for SEO and branding',
            'data_type': 'string'
        },
        {
            'key': 'contact_email',
            'value': 'contact@markethubpro.com',
            'category': 'general',
            'description': 'Primary contact email address',
            'data_type': 'string'
        },
        {
            'key': 'default_currency',
            'value': 'USD',
            'category': 'commerce',
            'description': 'Default currency for the platform',
            'data_type': 'string'
        },
        {
            'key': 'products_per_page',
            'value': '24',
            'category': 'display',
            'description': 'Number of products to display per page',
            'data_type': 'number'
        },
        {
            'key': 'enable_user_registration',
            'value': 'true',
            'category': 'security',
            'description': 'Allow new users to register accounts',
            'data_type': 'boolean'
        },
        {
            'key': 'maintenance_mode',
            'value': 'false',
            'category': 'system',
            'description': 'Enable maintenance mode to disable public access',
            'data_type': 'boolean'
        }
    ]
    
    for setting_data in default_settings:
        setting = AdminSetting.query.filter_by(key=setting_data['key']).first()
        if not setting:
            setting = AdminSetting(**setting_data)
            db.session.add(setting)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Settings creation skipped: {str(e)}")