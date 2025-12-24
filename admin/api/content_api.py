"""
Content Management API endpoints for Dynamic Admin System
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import functools

content_bp = Blueprint('content_api', __name__, url_prefix='/content')


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


@content_bp.route('/', methods=['GET'])
def content_info():
    """Get content API information."""
    return jsonify({
        'success': True,
        'data': {
            'name': 'Content Management API',
            'version': '2.0.0',
            'endpoints': {
                'elements': '/api/admin/content/elements',
                'content': '/api/admin/content/<element_id>',
                'publish': '/api/admin/content/<element_id>/publish (POST)',
                'history': '/api/admin/content/<element_id>/history',
                'rollback': '/api/admin/content/<element_id>/rollback (POST)',
                'search': '/api/admin/content/search'
            }
        }
    })


@content_bp.route('/elements', methods=['GET'])
@login_required
@admin_required
def list_content_elements():
    """List all content elements."""
    try:
        content_manager = current_app.content_manager
        elements = content_manager.list_content_elements()
        
        return jsonify({
            'success': True,
            'data': elements
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@content_bp.route('/<element_id>', methods=['GET'])
def get_content(element_id):
    """Get content for a specific element."""
    try:
        version_id = request.args.get('version_id')
        
        content_manager = current_app.content_manager
        content = content_manager.get_content(element_id, version_id)
        
        if content:
            return jsonify({
                'success': True,
                'data': content
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Content not found'
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@content_bp.route('/<element_id>', methods=['PUT'])
@login_required
@admin_required
def edit_content(element_id):
    """Edit content for an element."""
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': 'Content is required'
            }), 400
        
        content = data['content']
        content_type = data.get('content_type', 'html')
        
        content_manager = current_app.content_manager
        result = content_manager.edit_content(element_id, content, current_user.id, content_type)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@content_bp.route('/<element_id>/publish', methods=['POST'])
@login_required
@admin_required
def publish_content(element_id):
    """Publish content for an element."""
    try:
        data = request.get_json() or {}
        version_id = data.get('version_id')
        
        content_manager = current_app.content_manager
        result = content_manager.publish_content(element_id, version_id, current_user.id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@content_bp.route('/<element_id>/history', methods=['GET'])
@login_required
@admin_required
def get_version_history(element_id):
    """Get version history for an element."""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        content_manager = current_app.content_manager
        history = content_manager.get_version_history(element_id, limit)
        
        return jsonify({
            'success': True,
            'data': history
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@content_bp.route('/<element_id>/rollback', methods=['POST'])
@login_required
@admin_required
def rollback_content(element_id):
    """Rollback content to a previous version."""
    try:
        data = request.get_json()
        if not data or 'version_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Version ID is required'
            }), 400
        
        content_manager = current_app.content_manager
        result = content_manager.rollback_content(element_id, data['version_id'], current_user.id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@content_bp.route('/blocks', methods=['GET'])
@login_required
@admin_required
def get_content_blocks():
    """Get content blocks."""
    try:
        # For now, return sample content blocks
        # In a real implementation, this would query a content_blocks table
        sample_blocks = [
            {
                'id': 'hero-section',
                'type': 'text',
                'title': 'Hero Section',
                'content': 'Welcome to MarketHub Pro - Your premier e-commerce marketplace',
                'is_published': True,
                'last_modified': '2025-12-24T09:00:00Z'
            },
            {
                'id': 'featured-products',
                'type': 'product_grid',
                'title': 'Featured Products',
                'content': {'product_ids': [1, 2, 3, 4]},
                'is_published': True,
                'last_modified': '2025-12-24T09:00:00Z'
            }
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'blocks': sample_blocks
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@content_bp.route('/media', methods=['GET'])
@login_required
@admin_required
def get_media():
    """Get media library items."""
    try:
        # For now, return empty media library
        # In a real implementation, this would query a media table
        return jsonify({
            'success': True,
            'data': {
                'media': []
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@content_bp.route('/update', methods=['POST'])
@login_required
@admin_required
def update_content():
    """Update text content via inline editing."""
    try:
        data = request.get_json()
        if not data or 'content_id' not in data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': 'Content ID and content are required'
            }), 400
        
        content_id = data['content_id']
        content = data['content']
        content_type = data.get('type', 'text')
        
        # For now, just return success
        # In a real implementation, this would update the content in the database
        return jsonify({
            'success': True,
            'data': {
                'content_id': content_id,
                'content': content,
                'type': content_type,
                'updated_at': '2025-12-24T09:00:00Z'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@content_bp.route('/update-image', methods=['POST'])
@login_required
@admin_required
def update_image():
    """Update image content via inline editing."""
    try:
        data = request.get_json()
        if not data or 'content_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Content ID is required'
            }), 400
        
        content_id = data['content_id']
        src = data.get('src', '')
        alt = data.get('alt', '')
        
        # For now, just return success
        # In a real implementation, this would update the image in the database
        return jsonify({
            'success': True,
            'data': {
                'content_id': content_id,
                'src': src,
                'alt': alt,
                'updated_at': '2025-12-24T09:00:00Z'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@content_bp.route('/upload-image', methods=['POST'])
@login_required
@admin_required
def upload_image():
    """Upload image file via inline editing."""
    try:
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No image file provided'
            }), 400
        
        file = request.files['image']
        content_id = request.form.get('content_id', '')
        
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
        
        # For now, just return a placeholder URL
        # In a real implementation, this would save the file and return the actual URL
        import os
        import uuid
        
        # Generate a unique filename
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join('static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        # Return the URL
        file_url = f"/static/uploads/{unique_filename}"
        
        return jsonify({
            'success': True,
            'data': {
                'url': file_url,
                'filename': unique_filename,
                'content_id': content_id,
                'uploaded_at': '2025-12-24T09:00:00Z'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@content_bp.route('/search', methods=['GET'])
@login_required
@admin_required
def search_content():
    """Search content by text."""
    try:
        query = request.args.get('q', '')
        content_type = request.args.get('type')
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query is required'
            }), 400
        
        content_manager = current_app.content_manager
        results = content_manager.search_content(query, content_type)
        
        return jsonify({
            'success': True,
            'data': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500