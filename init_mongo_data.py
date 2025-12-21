#!/usr/bin/env python3
"""
Initialize MongoDB with enhanced sample data for the AliExpress-inspired E-commerce application.
"""

from app_mongo import app, mongo
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from bson import ObjectId
import uuid

def init_sample_data():
    """Initialize MongoDB with comprehensive sample data."""
    
    with app.app_context():
        print("🚀 Initializing MongoDB with sample data...")
        
        # Clear existing data (optional - comment out for production)
        # mongo.db.users.delete_many({})
        # mongo.db.vendors.delete_many({})
        # mongo.db.products.delete_many({})
        
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
                    'avatar_url': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop&crop=face',
                    'phone': '+1-555-0001',
                    'date_of_birth': None,
                    'gender': 'other'
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
        
        # Create sample users
        sample_users = [
            {
                'username': 'john_doe',
                'email': 'john@example.com',
                'password': generate_password_hash('user123'),
                'role': 'user',
                'profile': {
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'avatar_url': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face',
                    'phone': '+1-555-0002',
                    'date_of_birth': datetime(1990, 5, 15),
                    'gender': 'male'
                },
                'addresses': [
                    {
                        'type': 'shipping',
                        'street': '123 Main Street',
                        'city': 'New York',
                        'state': 'NY',
                        'zip_code': '10001',
                        'country': 'USA',
                        'is_default': True
                    }
                ],
                'preferences': {
                    'language': 'en',
                    'currency': 'USD',
                    'notifications': {
                        'email': True,
                        'sms': True,
                        'push': True
                    }
                },
                'created_at': datetime.utcnow() - timedelta(days=30),
                'updated_at': datetime.utcnow(),
                'last_login': datetime.utcnow() - timedelta(days=1),
                'is_active': True,
                'email_verified': True
            },
            {
                'username': 'jane_smith',
                'email': 'jane@example.com',
                'password': generate_password_hash('user123'),
                'role': 'user',
                'profile': {
                    'first_name': 'Jane',
                    'last_name': 'Smith',
                    'avatar_url': 'https://images.unsplash.com/photo-1494790108755-2616b612b786?w=100&h=100&fit=crop&crop=face',
                    'phone': '+1-555-0003',
                    'date_of_birth': datetime(1985, 8, 22),
                    'gender': 'female'
                },
                'addresses': [
                    {
                        'type': 'shipping',
                        'street': '456 Oak Avenue',
                        'city': 'Los Angeles',
                        'state': 'CA',
                        'zip_code': '90210',
                        'country': 'USA',
                        'is_default': True
                    }
                ],
                'preferences': {
                    'language': 'en',
                    'currency': 'USD',
                    'notifications': {
                        'email': True,
                        'sms': False,
                        'push': True
                    }
                },
                'created_at': datetime.utcnow() - timedelta(days=45),
                'updated_at': datetime.utcnow(),
                'last_login': datetime.utcnow() - timedelta(hours=2),
                'is_active': True,
                'email_verified': True
            }
        ]
        
        user_ids = []
        for user_data in sample_users:
            if not mongo.db.users.find_one({'username': user_data['username']}):
                result = mongo.db.users.insert_one(user_data)
                user_ids.append(result.inserted_id)
                print(f"✅ Created user: {user_data['username']}")
        
        # Create vendor users and vendors
        sample_vendors_data = [
            {
                'user': {
                    'username': 'techstore_pro',
                    'email': 'contact@techstorepro.com',
                    'password': generate_password_hash('vendor123'),
                    'role': 'vendor',
                    'profile': {
                        'first_name': 'Tech',
                        'last_name': 'Store',
                        'avatar_url': 'https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=100&h=100&fit=crop&crop=face',
                        'phone': '+1-555-1001',
                        'date_of_birth': None,
                        'gender': 'other'
                    }
                },
                'vendor': {
                    'business_info': {
                        'name': 'TechStore Pro',
                        'description': 'Your premier destination for cutting-edge technology and innovative gadgets. We specialize in high-quality electronics, smart devices, and tech accessories.',
                        'category': 'Electronics',
                        'website': 'https://techstorepro.com',
                        'logo_url': 'https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=200&h=200&fit=crop',
                        'banner_url': 'https://images.unsplash.com/photo-1518709268805-4e9042af2176?w=800&h=300&fit=crop'
                    },
                    'contact_info': {
                        'email': 'contact@techstorepro.com',
                        'phone': '+1-555-1001',
                        'address': {
                            'street': '123 Tech Street',
                            'city': 'Silicon Valley',
                            'state': 'CA',
                            'zip_code': '94000',
                            'country': 'USA'
                        }
                    },
                    'verification': {
                        'is_verified': True,
                        'verification_date': datetime.utcnow() - timedelta(days=60),
                        'documents': ['business_license.pdf', 'tax_certificate.pdf']
                    },
                    'performance': {
                        'rating': 4.8,
                        'total_reviews': 156,
                        'total_sales': 125000.00,
                        'total_orders': 890,
                        'response_rate': 98.5,
                        'response_time': 2
                    },
                    'settings': {
                        'commission_rate': 5.0,
                        'auto_approve_orders': True,
                        'vacation_mode': False
                    }
                }
            },
            {
                'user': {
                    'username': 'homestyle_living',
                    'email': 'hello@homestyleliving.com',
                    'password': generate_password_hash('vendor123'),
                    'role': 'vendor',
                    'profile': {
                        'first_name': 'Home',
                        'last_name': 'Style',
                        'avatar_url': 'https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=100&h=100&fit=crop&crop=face',
                        'phone': '+1-555-1002',
                        'date_of_birth': None,
                        'gender': 'other'
                    }
                },
                'vendor': {
                    'business_info': {
                        'name': 'HomeStyle Living',
                        'description': 'Transform your house into a beautiful home with our curated collection of modern and classic home decor, furniture, and kitchen essentials.',
                        'category': 'Home & Garden',
                        'website': 'https://homestyleliving.com',
                        'logo_url': 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=200&h=200&fit=crop',
                        'banner_url': 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=800&h=300&fit=crop'
                    },
                    'contact_info': {
                        'email': 'hello@homestyleliving.com',
                        'phone': '+1-555-1002',
                        'address': {
                            'street': '456 Home Avenue',
                            'city': 'Design District',
                            'state': 'NY',
                            'zip_code': '10001',
                            'country': 'USA'
                        }
                    },
                    'verification': {
                        'is_verified': True,
                        'verification_date': datetime.utcnow() - timedelta(days=45),
                        'documents': ['business_license.pdf', 'tax_certificate.pdf']
                    },
                    'performance': {
                        'rating': 4.6,
                        'total_reviews': 89,
                        'total_sales': 78000.00,
                        'total_orders': 456,
                        'response_rate': 96.2,
                        'response_time': 3
                    },
                    'settings': {
                        'commission_rate': 5.0,
                        'auto_approve_orders': True,
                        'vacation_mode': False
                    }
                }
            },
            {
                'user': {
                    'username': 'fitness_gear_plus',
                    'email': 'support@fitnessgearpus.com',
                    'password': generate_password_hash('vendor123'),
                    'role': 'vendor',
                    'profile': {
                        'first_name': 'Fitness',
                        'last_name': 'Gear',
                        'avatar_url': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=100&h=100&fit=crop&crop=face',
                        'phone': '+1-555-1003',
                        'date_of_birth': None,
                        'gender': 'other'
                    }
                },
                'vendor': {
                    'business_info': {
                        'name': 'FitnessGear Plus',
                        'description': 'Premium fitness equipment and accessories for your healthy lifestyle journey. From yoga essentials to professional workout gear.',
                        'category': 'Sports & Outdoors',
                        'website': 'https://fitnessgearplus.com',
                        'logo_url': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=200&h=200&fit=crop',
                        'banner_url': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=300&fit=crop'
                    },
                    'contact_info': {
                        'email': 'support@fitnessgearplus.com',
                        'phone': '+1-555-1003',
                        'address': {
                            'street': '789 Fitness Blvd',
                            'city': 'Health City',
                            'state': 'TX',
                            'zip_code': '75001',
                            'country': 'USA'
                        }
                    },
                    'verification': {
                        'is_verified': True,
                        'verification_date': datetime.utcnow() - timedelta(days=30),
                        'documents': ['business_license.pdf', 'tax_certificate.pdf']
                    },
                    'performance': {
                        'rating': 4.9,
                        'total_reviews': 203,
                        'total_sales': 156000.00,
                        'total_orders': 1234,
                        'response_rate': 99.1,
                        'response_time': 1
                    },
                    'settings': {
                        'commission_rate': 4.5,
                        'auto_approve_orders': True,
                        'vacation_mode': False
                    }
                }
            }
        ]
        
        vendor_ids = []
        for vendor_data in sample_vendors_data:
            # Create vendor user
            if not mongo.db.users.find_one({'username': vendor_data['user']['username']}):
                user_doc = vendor_data['user'].copy()
                user_doc.update({
                    'addresses': [],
                    'preferences': {
                        'language': 'en',
                        'currency': 'USD',
                        'notifications': {
                            'email': True,
                            'sms': True,
                            'push': True
                        }
                    },
                    'created_at': datetime.utcnow() - timedelta(days=60),
                    'updated_at': datetime.utcnow(),
                    'last_login': datetime.utcnow() - timedelta(hours=6),
                    'is_active': True,
                    'email_verified': True
                })
                
                user_result = mongo.db.users.insert_one(user_doc)
                
                # Create vendor profile
                vendor_doc = vendor_data['vendor'].copy()
                vendor_doc.update({
                    'user_id': user_result.inserted_id,
                    'created_at': datetime.utcnow() - timedelta(days=60),
                    'updated_at': datetime.utcnow()
                })
                
                vendor_result = mongo.db.vendors.insert_one(vendor_doc)
                vendor_ids.append(vendor_result.inserted_id)
                
                print(f"✅ Created vendor: {vendor_data['vendor']['business_info']['name']}")
        
        # Create sample products
        sample_products = [
            # TechStore Pro products
            {
                'vendor_index': 0,
                'basic_info': {
                    'name': 'Wireless Bluetooth Headphones Pro Max',
                    'description': 'Premium wireless headphones with active noise cancellation, 40-hour battery life, and crystal-clear audio quality. Perfect for music lovers, professionals, and gamers.',
                    'short_description': 'Premium wireless headphones with ANC and 40-hour battery',
                    'category': 'Electronics',
                    'subcategory': 'Audio',
                    'brand': 'AudioTech',
                    'model': 'AT-WH-Pro-Max',
                    'sku': f'SKU-{uuid.uuid4().hex[:8].upper()}'
                },
                'pricing': {
                    'price': 199.99,
                    'compare_price': 249.99,
                    'cost_price': 120.00,
                    'discount_percentage': 20.0,
                    'bulk_pricing': []
                },
                'inventory': {
                    'stock': 50,
                    'low_stock_threshold': 10,
                    'track_inventory': True,
                    'allow_backorders': False
                },
                'media': {
                    'main_image': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&h=600&fit=crop',
                    'images': [
                        'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&h=600&fit=crop',
                        'https://images.unsplash.com/photo-1484704849700-f032a568e944?w=600&h=600&fit=crop',
                        'https://images.unsplash.com/photo-1583394838336-acd977736f90?w=600&h=600&fit=crop'
                    ],
                    'videos': []
                },
                'attributes': {
                    'weight': 0.3,
                    'dimensions': {'length': 20, 'width': 18, 'height': 8},
                    'color': 'Midnight Black',
                    'size': 'One Size',
                    'material': 'Premium Plastic & Metal',
                    'custom_attributes': {
                        'battery_life': '40 hours',
                        'connectivity': 'Bluetooth 5.2',
                        'noise_cancellation': 'Active ANC'
                    }
                },
                'seo': {
                    'meta_title': 'Wireless Bluetooth Headphones Pro Max - Premium Audio',
                    'meta_description': 'Experience premium audio with our Wireless Bluetooth Headphones Pro Max featuring ANC and 40-hour battery life.',
                    'tags': ['wireless', 'bluetooth', 'headphones', 'noise-cancelling', 'premium', 'audio'],
                    'slug': 'wireless-bluetooth-headphones-pro-max'
                },
                'shipping': {
                    'free_shipping': True,
                    'shipping_cost': 0.00,
                    'processing_time': 1,
                    'shipping_from': 'California, USA'
                },
                'status': 'active',
                'is_featured': True,
                'views': 1250,
                'favorites': 89
            },
            {
                'vendor_index': 0,
                'basic_info': {
                    'name': 'Smartphone Protective Case Ultra Shield',
                    'description': 'Military-grade protection with wireless charging compatibility. Drop-tested from 10 feet, scratch-resistant design with premium materials.',
                    'short_description': 'Military-grade phone protection with wireless charging',
                    'category': 'Electronics',
                    'subcategory': 'Accessories',
                    'brand': 'ShieldTech',
                    'model': 'ST-Ultra-Shield',
                    'sku': f'SKU-{uuid.uuid4().hex[:8].upper()}'
                },
                'pricing': {
                    'price': 34.99,
                    'compare_price': 49.99,
                    'cost_price': 18.00,
                    'discount_percentage': 30.0,
                    'bulk_pricing': []
                },
                'inventory': {
                    'stock': 100,
                    'low_stock_threshold': 20,
                    'track_inventory': True,
                    'allow_backorders': True
                },
                'media': {
                    'main_image': 'https://images.unsplash.com/photo-1556656793-08538906a9f8?w=600&h=600&fit=crop',
                    'images': [
                        'https://images.unsplash.com/photo-1556656793-08538906a9f8?w=600&h=600&fit=crop',
                        'https://images.unsplash.com/photo-1574944985070-8f3ebc6b79d2?w=600&h=600&fit=crop'
                    ],
                    'videos': []
                },
                'attributes': {
                    'weight': 0.1,
                    'dimensions': {'length': 16, 'width': 8, 'height': 1},
                    'color': 'Clear Black',
                    'size': 'iPhone 14 Pro',
                    'material': 'TPU + PC',
                    'custom_attributes': {
                        'drop_protection': '10 feet',
                        'wireless_charging': 'Compatible',
                        'screen_protection': 'Raised edges'
                    }
                },
                'seo': {
                    'meta_title': 'Smartphone Protective Case Ultra Shield - Military Grade',
                    'meta_description': 'Protect your phone with our military-grade Ultra Shield case featuring wireless charging compatibility.',
                    'tags': ['phone case', 'protection', 'wireless charging', 'military grade', 'drop proof'],
                    'slug': 'smartphone-protective-case-ultra-shield'
                },
                'shipping': {
                    'free_shipping': False,
                    'shipping_cost': 4.99,
                    'processing_time': 1,
                    'shipping_from': 'California, USA'
                },
                'status': 'active',
                'is_featured': False,
                'views': 890,
                'favorites': 45
            },
            # HomeStyle Living products
            {
                'vendor_index': 1,
                'basic_info': {
                    'name': 'Premium Ceramic Coffee Mug Set - Artisan Collection',
                    'description': 'Set of 4 handcrafted ceramic mugs with ergonomic handles and beautiful glazed finish. Microwave and dishwasher safe. Perfect for your morning coffee ritual.',
                    'short_description': 'Set of 4 handcrafted ceramic mugs with ergonomic design',
                    'category': 'Home & Garden',
                    'subcategory': 'Kitchen',
                    'brand': 'CeramicCraft',
                    'model': 'CC-Artisan-Set',
                    'sku': f'SKU-{uuid.uuid4().hex[:8].upper()}'
                },
                'pricing': {
                    'price': 39.99,
                    'compare_price': 59.99,
                    'cost_price': 22.00,
                    'discount_percentage': 33.0,
                    'bulk_pricing': []
                },
                'inventory': {
                    'stock': 75,
                    'low_stock_threshold': 15,
                    'track_inventory': True,
                    'allow_backorders': False
                },
                'media': {
                    'main_image': 'https://images.unsplash.com/photo-1514228742587-6b1558fcf93a?w=600&h=600&fit=crop',
                    'images': [
                        'https://images.unsplash.com/photo-1514228742587-6b1558fcf93a?w=600&h=600&fit=crop',
                        'https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=600&h=600&fit=crop'
                    ],
                    'videos': []
                },
                'attributes': {
                    'weight': 1.5,
                    'dimensions': {'length': 10, 'width': 10, 'height': 12},
                    'color': 'Glazed White',
                    'size': '12 oz',
                    'material': 'Premium Ceramic',
                    'custom_attributes': {
                        'capacity': '12 oz each',
                        'dishwasher_safe': True,
                        'microwave_safe': True,
                        'set_size': '4 pieces'
                    }
                },
                'seo': {
                    'meta_title': 'Premium Ceramic Coffee Mug Set - Artisan Collection',
                    'meta_description': 'Beautiful handcrafted ceramic coffee mug set perfect for your daily coffee ritual. Dishwasher and microwave safe.',
                    'tags': ['coffee mugs', 'ceramic', 'handcrafted', 'kitchen', 'dishwasher safe', 'set'],
                    'slug': 'premium-ceramic-coffee-mug-set-artisan'
                },
                'shipping': {
                    'free_shipping': False,
                    'shipping_cost': 7.99,
                    'processing_time': 2,
                    'shipping_from': 'New York, USA'
                },
                'status': 'active',
                'is_featured': True,
                'views': 567,
                'favorites': 78
            },
            # FitnessGear Plus products
            {
                'vendor_index': 2,
                'basic_info': {
                    'name': 'Premium Yoga Mat Pro - Eco-Friendly Non-Slip',
                    'description': 'Extra-thick non-slip yoga mat made from eco-friendly TPE material. Perfect grip for all yoga styles and fitness routines. Includes carrying strap.',
                    'short_description': 'Extra-thick eco-friendly yoga mat with perfect grip',
                    'category': 'Sports & Outdoors',
                    'subcategory': 'Fitness',
                    'brand': 'YogaPro',
                    'model': 'YP-Premium-Mat',
                    'sku': f'SKU-{uuid.uuid4().hex[:8].upper()}'
                },
                'pricing': {
                    'price': 49.99,
                    'compare_price': 79.99,
                    'cost_price': 25.00,
                    'discount_percentage': 37.5,
                    'bulk_pricing': []
                },
                'inventory': {
                    'stock': 40,
                    'low_stock_threshold': 8,
                    'track_inventory': True,
                    'allow_backorders': True
                },
                'media': {
                    'main_image': 'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=600&h=600&fit=crop',
                    'images': [
                        'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=600&h=600&fit=crop',
                        'https://images.unsplash.com/photo-1506629905607-d9b1b2e3d3b1?w=600&h=600&fit=crop'
                    ],
                    'videos': []
                },
                'attributes': {
                    'weight': 1.8,
                    'dimensions': {'length': 183, 'width': 61, 'height': 0.6},
                    'color': 'Deep Purple',
                    'size': '6mm thick',
                    'material': 'Eco-friendly TPE',
                    'custom_attributes': {
                        'thickness': '6mm',
                        'eco_friendly': True,
                        'non_slip': True,
                        'includes_strap': True
                    }
                },
                'seo': {
                    'meta_title': 'Premium Yoga Mat Pro - Eco-Friendly Non-Slip 6mm',
                    'meta_description': 'Professional yoga mat with perfect grip and eco-friendly materials. Extra thick 6mm for ultimate comfort.',
                    'tags': ['yoga mat', 'eco-friendly', 'non-slip', 'fitness', 'exercise', 'premium'],
                    'slug': 'premium-yoga-mat-pro-eco-friendly'
                },
                'shipping': {
                    'free_shipping': True,
                    'shipping_cost': 0.00,
                    'processing_time': 1,
                    'shipping_from': 'Texas, USA'
                },
                'status': 'active',
                'is_featured': True,
                'views': 2340,
                'favorites': 156
            }
        ]
        
        # Insert products
        for product_data in sample_products:
            vendor_id = vendor_ids[product_data['vendor_index']] if product_data['vendor_index'] < len(vendor_ids) else None
            
            product_doc = product_data.copy()
            del product_doc['vendor_index']
            product_doc.update({
                'vendor_id': vendor_id,
                'created_at': datetime.utcnow() - timedelta(days=30),
                'updated_at': datetime.utcnow()
            })
            
            mongo.db.products.insert_one(product_doc)
            print(f"✅ Created product: {product_data['basic_info']['name']}")
        
        # Create indexes for better performance
        print("🔧 Creating database indexes...")
        mongo.db.users.create_index('username', unique=True)
        mongo.db.users.create_index('email', unique=True)
        mongo.db.products.create_index([('basic_info.name', 'text'), ('basic_info.description', 'text')])
        mongo.db.products.create_index('basic_info.category')
        mongo.db.products.create_index('pricing.price')
        mongo.db.products.create_index('status')
        mongo.db.products.create_index('is_featured')
        mongo.db.vendors.create_index('user_id')
        mongo.db.vendors.create_index('verification.is_verified')
        
        print("✅ Database indexes created")
        print("\n🎉 MongoDB initialization completed!")
        print("\nYou can now run the application with: python app_mongo.py")
        print("\n🔑 Default login credentials:")
        print("Admin - Username: admin, Password: admin123")
        print("Users - Username: john_doe/jane_smith, Password: user123")
        print("\n🏪 Vendor accounts:")
        print("TechStore Pro - Username: techstore_pro, Password: vendor123")
        print("HomeStyle Living - Username: homestyle_living, Password: vendor123")
        print("FitnessGear Plus - Username: fitness_gear_plus, Password: vendor123")

if __name__ == '__main__':
    init_sample_data()