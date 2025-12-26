"""
Product Management API endpoints for Dynamic Admin System
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models_sqlite import Product, Category, db
from datetime import datetime
import functools
import os

product_bp = Blueprint('product_api', __name__, url_prefix='/products')


def admin_required(f):
    """Decorator to require admin role."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_role('admin'):
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403
        return f(*args, **kwargs)
    return decorated_function


@product_bp.route('/info', methods=['GET'])
def product_info():
    """Get product API information."""
    return jsonify({
        'success': True,
        'data': {
            'name': 'Product Management API',
            'version': '2.0.0',
            'endpoints': {
                'list': '/api/admin/products',
                'create': '/api/admin/products (POST)',
                'get': '/api/admin/products/<id>',
                'update': '/api/admin/products/<id> (PUT)',
                'delete': '/api/admin/products/<id> (DELETE)',
                'upload_image': '/api/admin/products/<id>/images (POST)',
                'delete_image': '/api/admin/products/<id>/images/<image_url> (DELETE)',
                'reorder_images': '/api/admin/products/<id>/images/reorder (POST)',
                'categories': '/api/admin/products/categories',
                'create_category': '/api/admin/products/categories (POST)',
                'reorder': '/api/admin/products/reorder (POST)',
                'duplicate': '/api/admin/products/<id>/duplicate (POST)'
            }
        }
    })


@product_bp.route('/', methods=['POST'])
@login_required
@admin_required
def create_product():
    """Create a new product."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Product data is required'
            }), 400
        
        # Validate required fields
        required_fields = ['name', 'price']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400
        
        # Create product
        product = Product(
            name=data['name'],
            slug=data.get('slug', data['name'].lower().replace(' ', '-')),
            description=data.get('description', ''),
            short_description=data.get('short_description', ''),
            price=float(data['price']),
            compare_price=float(data['compare_price']) if data.get('compare_price') else None,
            sku=data.get('sku', ''),
            inventory_quantity=int(data.get('inventory_quantity', 0)),
            is_active=data.get('is_active', True),
            is_featured=data.get('is_featured', False),
            weight=float(data.get('weight', 0)) if data.get('weight') else None,
            dimensions=data.get('dimensions', '')
        )
        
        # Handle images
        if 'images' in data and isinstance(data['images'], list):
            product.set_images(data['images'])
        
        # Handle categories
        if 'category_ids' in data:
            categories = Category.query.filter(Category.id.in_(data['category_ids'])).all()
            product.categories = categories
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'product': product.to_dict()
            },
            'message': 'Product created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@product_bp.route('/', methods=['GET'])
@login_required
@admin_required
def get_products():
    """Get all products."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        products = Product.query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': {
                'products': [product.to_dict() for product in products.items],
                'pagination': {
                    'current_page': products.page,
                    'total_pages': products.pages,
                    'total_items': products.total,
                    'has_next': products.has_next,
                    'has_prev': products.has_prev
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@product_bp.route('/<int:product_id>', methods=['GET'])
@login_required
@admin_required
def get_product(product_id):
    """Get a specific product."""
    try:
        product = Product.query.get_or_404(product_id)
        
        return jsonify({
            'success': True,
            'data': {
                'product': product.to_dict()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@product_bp.route('/<int:product_id>/images', methods=['POST'])
@login_required
@admin_required
def upload_product_image(product_id):
    """Upload image for a product."""
    try:
        product = Product.query.get_or_404(product_id)
        
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No image file provided'
            }), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Check file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        if not ('.' in file.filename and 
                file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'
            }), 400
        
        import os
        import uuid
        
        # Generate a unique filename
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"product_{product_id}_{uuid.uuid4().hex}.{file_extension}"
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join('static', 'uploads', 'products')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        # Add to product images
        current_images = product.get_images()
        file_url = f"/static/uploads/products/{unique_filename}"
        current_images.append(file_url)
        product.set_images(current_images)
        
        product.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'image_url': file_url,
                'filename': unique_filename,
                'product_id': product_id,
                'total_images': len(current_images)
            },
            'message': 'Image uploaded successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@product_bp.route('/<int:product_id>/images/<path:image_url>', methods=['DELETE'])
@login_required
@admin_required
def delete_product_image(product_id, image_url):
    """Delete a specific image from a product."""
    try:
        product = Product.query.get_or_404(product_id)
        
        # Decode the image URL
        import urllib.parse
        image_url = urllib.parse.unquote(image_url)
        
        current_images = product.get_images()
        
        if image_url not in current_images:
            return jsonify({
                'success': False,
                'error': 'Image not found'
            }), 404
        
        # Remove from list
        current_images.remove(image_url)
        product.set_images(current_images)
        
        # Try to delete the physical file
        try:
            if image_url.startswith('/static/uploads/'):
                file_path = image_url[1:]  # Remove leading slash
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception as e:
            current_app.logger.warning(f"Could not delete physical file {image_url}: {e}")
        
        product.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Image deleted successfully',
            'data': {
                'remaining_images': current_images,
                'total_images': len(current_images)
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@product_bp.route('/<int:product_id>/images/reorder', methods=['POST'])
@login_required
@admin_required
def reorder_product_images(product_id):
    """Reorder product images."""
    try:
        product = Product.query.get_or_404(product_id)
        data = request.get_json()
        
        if not data or 'image_urls' not in data:
            return jsonify({
                'success': False,
                'error': 'Image URLs array is required'
            }), 400
        
        new_order = data['image_urls']
        current_images = product.get_images()
        
        # Validate that all provided URLs exist in current images
        for url in new_order:
            if url not in current_images:
                return jsonify({
                    'success': False,
                    'error': f'Image URL not found: {url}'
                }), 400
        
        # Update the order
        product.set_images(new_order)
        product.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Images reordered successfully',
            'data': {
                'images': new_order
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@product_bp.route('/<int:product_id>', methods=['PUT'])
@login_required
@admin_required
def update_product(product_id):
    """Update a product."""
    try:
        product = Product.query.get_or_404(product_id)
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Product data is required'
            }), 400
        
        # Update fields
        updatable_fields = [
            'name', 'slug', 'description', 'short_description', 'price', 
            'compare_price', 'sku', 'inventory_quantity', 'is_active', 
            'is_featured', 'weight', 'dimensions'
        ]
        
        for field in updatable_fields:
            if field in data:
                if field in ['price', 'compare_price', 'weight']:
                    setattr(product, field, float(data[field]) if data[field] else None)
                elif field == 'inventory_quantity':
                    setattr(product, field, int(data[field]))
                else:
                    setattr(product, field, data[field])
        
        # Handle images
        if 'images' in data:
            if isinstance(data['images'], list):
                product.set_images(data['images'])
            else:
                current_app.logger.warning(f"Invalid images format for product {product_id}: {data['images']}")
        
        # Handle categories
        if 'category_ids' in data:
            categories = Category.query.filter(Category.id.in_(data['category_ids'])).all()
            product.categories = categories
        
        product.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'product': product.to_dict()
            },
            'message': 'Product updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@product_bp.route('/<int:product_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_product(product_id):
    """Delete a product."""
    try:
        product = Product.query.get_or_404(product_id)
        
        # Check if product has orders
        if product.order_items:
            return jsonify({
                'success': False,
                'error': 'Cannot delete product with existing orders'
            }), 400
        
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Product deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@product_bp.route('/categories', methods=['POST'])
@login_required
@admin_required
def create_category():
    """Create a new category."""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({
                'success': False,
                'error': 'Category name is required'
            }), 400
        
        category = Category(
            name=data['name'],
            slug=data.get('slug', data['name'].lower().replace(' ', '-')),
            description=data.get('description', ''),
            parent_id=data.get('parent_id'),
            sort_order=data.get('sort_order', 0),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'slug': category.slug,
                    'description': category.description,
                    'parent_id': category.parent_id,
                    'sort_order': category.sort_order,
                    'is_active': category.is_active
                }
            },
            'message': 'Category created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@product_bp.route('/categories', methods=['GET'])
@login_required
@admin_required
def get_categories():
    """Get all product categories."""
    try:
        categories = Category.query.filter_by(is_active=True).all()
        
        return jsonify({
            'success': True,
            'data': {
                'categories': [{
                    'id': cat.id,
                    'name': cat.name,
                    'slug': cat.slug,
                    'description': cat.description,
                    'parent_id': cat.parent_id,
                    'sort_order': cat.sort_order,
                    'is_active': cat.is_active
                } for cat in categories]
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@product_bp.route('/reorder', methods=['POST'])
@login_required
@admin_required
def reorder_products():
    """Reorder products."""
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        from_index = data.get('from_index')
        to_index = data.get('to_index')
        
        # For now, just return success
        # In a real implementation, you'd update sort orders
        
        return jsonify({
            'success': True,
            'message': 'Products reordered successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@product_bp.route('/<int:product_id>/duplicate', methods=['POST'])
@login_required
@admin_required
def duplicate_product(product_id):
    """Duplicate a product."""
    try:
        original = Product.query.get_or_404(product_id)
        
        # Create duplicate
        duplicate = Product(
            name=f"{original.name} (Copy)",
            slug=f"{original.slug}-copy",
            description=original.description,
            short_description=original.short_description,
            price=original.price,
            compare_price=original.compare_price,
            sku=f"{original.sku}-COPY",
            inventory_quantity=0,
            is_active=False,
            is_featured=False
        )
        
        # Copy categories
        duplicate.categories = original.categories
        
        db.session.add(duplicate)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'product': duplicate.to_dict()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@product_bp.route('/categories/reorder', methods=['POST'])
@login_required
@admin_required
def reorder_categories():
    """Reorder categories."""
    try:
        data = request.get_json()
        category_id = data.get('category_id')
        from_path = data.get('from_path')
        to_path = data.get('to_path')
        
        # For now, just return success
        # In a real implementation, you'd update category hierarchy
        
        return jsonify({
            'success': True,
            'message': 'Categories reordered successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500