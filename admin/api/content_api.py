"""
Content Management API endpoints for Dynamic Admin System
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import functools
import json

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
        current_app.logger.info(f"Content update request data: {data}")
        
        if not data or 'content_id' not in data or 'content' not in data:
            current_app.logger.error("Missing required fields in content update request")
            return jsonify({
                'success': False,
                'error': 'Content ID and content are required'
            }), 400
        
        content_id = data['content_id']
        content = data['content']
        content_type = data.get('type', 'text')
        
        current_app.logger.info(f"Updating content_id: {content_id}, type: {content_type}, content length: {len(content)}")
        
        # Save directly to admin_settings table for reliability
        from models_sqlite import AdminSetting, db
        from datetime import datetime
        
        setting_key = f'text_content_{content_id}'
        setting = AdminSetting.query.filter_by(key=setting_key).first()
        
        content_data = {
            'content_id': content_id,
            'content': content,
            'type': content_type,
            'updated_at': datetime.utcnow().isoformat(),
            'updated_by': current_user.id
        }
        
        if setting:
            setting.set_value(json.dumps(content_data))
            setting.updated_at = datetime.utcnow()
            setting.updated_by = current_user.id
        else:
            setting = AdminSetting(
                key=setting_key,
                category='content',
                description=f'Text content for element: {content_id}',
                data_type='json',
                updated_by=current_user.id
            )
            setting.set_value(json.dumps(content_data))
            db.session.add(setting)
        
        db.session.commit()
        current_app.logger.info(f"Text content saved successfully for {content_id}")
        
        return jsonify({
            'success': True,
            'data': {
                'content_id': content_id,
                'content': content,
                'type': content_type,
                'updated_at': content_data['updated_at']
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Exception in update_content: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@content_bp.route('/test-update', methods=['POST'])
@login_required
@admin_required
def test_update():
    """Test endpoint for debugging content updates."""
    try:
        data = request.get_json()
        current_app.logger.info(f"Test update request data: {data}")
        
        # Just return success without doing anything
        return jsonify({
            'success': True,
            'data': {
                'message': 'Test endpoint working',
                'received_data': data,
                'user_id': current_user.id,
                'user_email': current_user.email
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Exception in test_update: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@content_bp.route('/update-image-simple', methods=['POST'])
@login_required
@admin_required
def update_image_simple():
    """Simple image update without content manager for testing."""
    try:
        data = request.get_json()
        current_app.logger.info(f"Simple image update request data: {data}")
        
        if not data or 'content_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Content ID is required'
            }), 400
        
        content_id = data['content_id']
        src = data.get('src', '')
        alt = data.get('alt', '')
        
        # Just save directly to admin_settings without content manager
        from models_sqlite import AdminSetting, db
        from datetime import datetime
        
        setting_key = f'simple_content_{content_id}'
        setting = AdminSetting.query.filter_by(key=setting_key).first()
        
        content_data = {
            'src': src,
            'alt': alt,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if setting:
            setting.set_value(json.dumps(content_data))
        else:
            setting = AdminSetting(
                key=setting_key,
                category='content',
                description=f'Simple content for {content_id}',
                data_type='json'
            )
            setting.set_value(json.dumps(content_data))
            db.session.add(setting)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'content_id': content_id,
                'src': src,
                'alt': alt,
                'updated_at': content_data['updated_at']
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Exception in update_image_simple: {str(e)}", exc_info=True)
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
        current_app.logger.info(f"Image update request data: {data}")
        
        if not data or 'content_id' not in data:
            current_app.logger.error("Missing content_id in image update request")
            return jsonify({
                'success': False,
                'error': 'Content ID is required'
            }), 400
        
        content_id = data['content_id']
        src = data.get('src', '')
        alt = data.get('alt', '')
        
        current_app.logger.info(f"Updating image content_id: {content_id}, src: {src}, alt: {alt}")
        
        # Save directly to admin_settings table (bypass content manager for now)
        from models_sqlite import AdminSetting, db
        from datetime import datetime
        
        setting_key = f'image_content_{content_id}'
        setting = AdminSetting.query.filter_by(key=setting_key).first()
        
        image_data = {
            'content_id': content_id,
            'src': src,
            'alt': alt,
            'type': 'image',
            'updated_at': datetime.utcnow().isoformat(),
            'updated_by': current_user.id
        }
        
        if setting:
            setting.set_value(json.dumps(image_data))
            setting.updated_at = datetime.utcnow()
            setting.updated_by = current_user.id
        else:
            setting = AdminSetting(
                key=setting_key,
                category='content',
                description=f'Image content for element: {content_id}',
                data_type='json',
                updated_by=current_user.id
            )
            setting.set_value(json.dumps(image_data))
            db.session.add(setting)
        
        db.session.commit()
        current_app.logger.info(f"Image content saved successfully for {content_id}")
        
        return jsonify({
            'success': True,
            'data': {
                'content_id': content_id,
                'src': src,
                'alt': alt,
                'updated_at': image_data['updated_at']
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Exception in update_image: {str(e)}", exc_info=True)
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