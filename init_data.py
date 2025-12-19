#!/usr/bin/env python3
"""
Initialize the database with sample data for the enhanced E-commerce application.
Run this script after setting up the database to populate it with sample products and vendors.
"""

from app import app, db, User, Product, Vendor
from werkzeug.security import generate_password_hash
import uuid

def init_sample_data():
    """Initialize the database with sample data."""
    
    with app.app_context():
        # Create all tables
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
            print("Created admin user (username: admin, password: admin123)")
        
        # Create sample user if doesn't exist
        if not User.query.filter_by(username='user').first():
            user = User(
                username='user',
                email='user@example.com',
                password=generate_password_hash('user123'),
                role='user'
            )
            db.session.add(user)
            print("Created sample user (username: user, password: user123)")
        
        # Create sample vendors
        sample_vendors_data = [
            {
                'username': 'techstore',
                'email': 'contact@techstore.com',
                'password': 'vendor123',
                'business_name': 'TechStore Pro',
                'business_description': 'Your one-stop shop for the latest technology and gadgets. We specialize in high-quality electronics, accessories, and smart devices.',
                'business_address': '123 Tech Street, Silicon Valley, CA 94000',
                'business_phone': '+1 (555) 123-4567',
                'business_email': 'contact@techstore.com',
                'is_verified': True,
                'rating': 4.8,
                'total_reviews': 156
            },
            {
                'username': 'homestyle',
                'email': 'hello@homestyle.com',
                'password': 'vendor123',
                'business_name': 'HomeStyle Living',
                'business_description': 'Beautiful home decor and kitchen essentials to make your house a home. Curated collection of modern and classic designs.',
                'business_address': '456 Home Avenue, Design District, NY 10001',
                'business_phone': '+1 (555) 234-5678',
                'business_email': 'hello@homestyle.com',
                'is_verified': True,
                'rating': 4.6,
                'total_reviews': 89
            },
            {
                'username': 'fitnessgear',
                'email': 'support@fitnessgear.com',
                'password': 'vendor123',
                'business_name': 'FitnessGear Plus',
                'business_description': 'Premium fitness equipment and accessories for your healthy lifestyle. From yoga mats to professional workout gear.',
                'business_address': '789 Fitness Blvd, Health City, TX 75001',
                'business_phone': '+1 (555) 345-6789',
                'business_email': 'support@fitnessgear.com',
                'is_verified': True,
                'rating': 4.9,
                'total_reviews': 203
            }
        ]
        
        vendors = []
        for vendor_data in sample_vendors_data:
            # Check if vendor user exists
            existing_user = User.query.filter_by(username=vendor_data['username']).first()
            if not existing_user:
                # Create vendor user
                vendor_user = User(
                    username=vendor_data['username'],
                    email=vendor_data['email'],
                    password=generate_password_hash(vendor_data['password']),
                    role='vendor'
                )
                db.session.add(vendor_user)
                db.session.flush()  # Get user ID
                
                # Create vendor profile
                vendor = Vendor(
                    user_id=vendor_user.id,
                    business_name=vendor_data['business_name'],
                    business_description=vendor_data['business_description'],
                    business_address=vendor_data['business_address'],
                    business_phone=vendor_data['business_phone'],
                    business_email=vendor_data['business_email'],
                    is_verified=vendor_data['is_verified'],
                    rating=vendor_data['rating'],
                    total_reviews=vendor_data['total_reviews']
                )
                db.session.add(vendor)
                vendors.append(vendor)
                print(f"Created vendor: {vendor_data['business_name']} (username: {vendor_data['username']}, password: vendor123)")
        
        db.session.flush()  # Ensure vendors are created before products
        
        # Enhanced sample products data with vendor assignments
        sample_products = [
            # TechStore Pro products
            {
                'name': 'Wireless Bluetooth Headphones Pro',
                'description': 'Premium wireless headphones with active noise cancellation, 30-hour battery life, and crystal-clear audio quality. Perfect for music lovers and professionals.',
                'price': 199.99,
                'stock': 50,
                'category': 'Electronics',
                'image_url': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400',
                'vendor_index': 0,  # TechStore Pro
                'brand': 'AudioTech',
                'weight': 0.3,
                'dimensions': '20x18x8 cm',
                'tags': 'wireless, bluetooth, noise-cancelling, premium',
                'discount_percentage': 15.0,
                'is_featured': True
            },
            {
                'name': 'Smartphone Protective Case Ultra',
                'description': 'Military-grade protection with wireless charging compatibility. Drop-tested and scratch-resistant design.',
                'price': 34.99,
                'stock': 100,
                'category': 'Electronics',
                'image_url': 'https://images.unsplash.com/photo-1556656793-08538906a9f8?w=400',
                'vendor_index': 0,
                'brand': 'ShieldTech',
                'weight': 0.1,
                'dimensions': '16x8x1 cm',
                'tags': 'protection, wireless charging, durable',
                'discount_percentage': 0.0
            },
            {
                'name': 'Adjustable Laptop Stand Pro',
                'description': 'Ergonomic aluminum laptop stand with adjustable height and angle. Improves posture and provides better cooling.',
                'price': 79.99,
                'stock': 30,
                'category': 'Electronics',
                'image_url': 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400',
                'vendor_index': 0,
                'brand': 'ErgoTech',
                'weight': 1.2,
                'dimensions': '28x20x5 cm',
                'tags': 'ergonomic, adjustable, aluminum, cooling',
                'discount_percentage': 10.0
            },
            {
                'name': 'Wireless Gaming Mouse RGB',
                'description': 'High-precision gaming mouse with customizable RGB lighting and programmable buttons. 16000 DPI sensor.',
                'price': 89.99,
                'stock': 60,
                'category': 'Electronics',
                'image_url': 'https://images.unsplash.com/photo-1527814050087-3793815479db?w=400',
                'vendor_index': 0,
                'brand': 'GameTech',
                'weight': 0.15,
                'dimensions': '12x7x4 cm',
                'tags': 'gaming, wireless, rgb, precision',
                'discount_percentage': 20.0,
                'is_featured': True
            },
            
            # HomeStyle Living products
            {
                'name': 'Premium Ceramic Coffee Mug Set',
                'description': 'Set of 4 handcrafted ceramic mugs with ergonomic handles. Microwave and dishwasher safe. Perfect for your morning coffee ritual.',
                'price': 39.99,
                'stock': 75,
                'category': 'Home & Kitchen',
                'image_url': 'https://images.unsplash.com/photo-1514228742587-6b1558fcf93a?w=400',
                'vendor_index': 1,  # HomeStyle Living
                'brand': 'CeramicCraft',
                'weight': 1.5,
                'dimensions': '10x10x12 cm each',
                'tags': 'ceramic, handcrafted, dishwasher safe, set',
                'discount_percentage': 0.0
            },
            {
                'name': 'Smart LED Desk Lamp',
                'description': 'Modern LED desk lamp with touch controls, USB charging port, and adjustable brightness. Energy-efficient and stylish.',
                'price': 59.99,
                'stock': 25,
                'category': 'Home & Kitchen',
                'image_url': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400',
                'vendor_index': 1,
                'brand': 'LightCraft',
                'weight': 0.8,
                'dimensions': '45x15x15 cm',
                'tags': 'led, smart, usb charging, adjustable',
                'discount_percentage': 25.0,
                'is_featured': True
            },
            {
                'name': 'Decorative Plant Pot Collection',
                'description': 'Set of 3 modern ceramic plant pots with drainage holes. Perfect for small indoor plants and succulents.',
                'price': 24.99,
                'stock': 45,
                'category': 'Home & Kitchen',
                'image_url': 'https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=400',
                'vendor_index': 1,
                'brand': 'GreenHome',
                'weight': 2.0,
                'dimensions': '12x12x10 cm each',
                'tags': 'ceramic, drainage, modern, set of 3',
                'discount_percentage': 0.0
            },
            
            # FitnessGear Plus products
            {
                'name': 'Premium Yoga Mat Pro',
                'description': 'Extra-thick non-slip yoga mat made from eco-friendly TPE material. Perfect grip for all yoga styles and fitness routines.',
                'price': 49.99,
                'stock': 40,
                'category': 'Sports & Fitness',
                'image_url': 'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=400',
                'vendor_index': 2,  # FitnessGear Plus
                'brand': 'YogaPro',
                'weight': 1.8,
                'dimensions': '183x61x0.6 cm',
                'tags': 'yoga, non-slip, eco-friendly, extra-thick',
                'discount_percentage': 30.0,
                'is_featured': True
            },
            {
                'name': 'Insulated Water Bottle 32oz',
                'description': 'Double-wall vacuum insulated stainless steel water bottle. Keeps drinks cold for 24 hours, hot for 12 hours.',
                'price': 29.99,
                'stock': 80,
                'category': 'Sports & Fitness',
                'image_url': 'https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=400',
                'vendor_index': 2,
                'brand': 'HydroFit',
                'weight': 0.5,
                'dimensions': '27x7x7 cm',
                'tags': 'insulated, stainless steel, 32oz, vacuum',
                'discount_percentage': 0.0
            },
            
            # Admin products (no vendor)
            {
                'name': 'Portable Bluetooth Speaker',
                'description': '360-degree sound portable speaker with waterproof design and 12-hour battery life. Perfect for outdoor adventures.',
                'price': 129.99,
                'stock': 35,
                'category': 'Electronics',
                'image_url': 'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400',
                'vendor_index': None,  # Admin product
                'brand': 'SoundWave',
                'weight': 0.6,
                'dimensions': '18x18x6 cm',
                'tags': 'bluetooth, waterproof, 360-sound, portable',
                'discount_percentage': 0.0
            },
            {
                'name': 'Premium Notebook Set',
                'description': 'Set of 3 premium notebooks with dotted pages, elastic closure, and pen holder. Perfect for journaling and note-taking.',
                'price': 24.99,
                'stock': 90,
                'category': 'Office Supplies',
                'image_url': 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400',
                'vendor_index': None,
                'brand': 'NoteCraft',
                'weight': 0.8,
                'dimensions': '21x14x2 cm each',
                'tags': 'dotted pages, elastic closure, premium, set',
                'discount_percentage': 0.0
            }
        ]
        
        # Add sample products
        for product_data in sample_products:
            existing_product = Product.query.filter_by(name=product_data['name']).first()
            if not existing_product:
                # Generate SKU
                sku = f"SKU-{uuid.uuid4().hex[:8].upper()}"
                
                # Get vendor ID if specified
                vendor_id = None
                if product_data['vendor_index'] is not None and product_data['vendor_index'] < len(vendors):
                    vendor_id = vendors[product_data['vendor_index']].id
                
                product = Product(
                    name=product_data['name'],
                    description=product_data['description'],
                    price=product_data['price'],
                    stock=product_data['stock'],
                    category=product_data['category'],
                    image_url=product_data['image_url'],
                    vendor_id=vendor_id,
                    brand=product_data.get('brand', ''),
                    sku=sku,
                    weight=product_data.get('weight', 0),
                    dimensions=product_data.get('dimensions', ''),
                    tags=product_data.get('tags', ''),
                    discount_percentage=product_data.get('discount_percentage', 0),
                    is_featured=product_data.get('is_featured', False)
                )
                db.session.add(product)
                print(f"Added product: {product_data['name']}")
        
        # Commit all changes
        db.session.commit()
        print("\nDatabase initialization completed!")
        print("You can now run the application with: python app.py")
        print("\nDefault login credentials:")
        print("Admin - Username: admin, Password: admin123")
        print("User - Username: user, Password: user123")
        print("\nVendor accounts:")
        print("TechStore Pro - Username: techstore, Password: vendor123")
        print("HomeStyle Living - Username: homestyle, Password: vendor123")
        print("FitnessGear Plus - Username: fitnessgear, Password: vendor123")

if __name__ == '__main__':
    init_sample_data()