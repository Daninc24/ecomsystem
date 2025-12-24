"""
Social Media Integrator with OAuth and content sync
"""

import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from bson import ObjectId
from ..models.integration import SocialMediaAccount
from .base_service import BaseService


class SocialMediaIntegrator(BaseService):
    """Manages social media integrations with OAuth and content synchronization."""
    
    def _get_collection_name(self) -> str:
        return "social_media_accounts"
    
    def __init__(self, mongo_db):
        super().__init__(mongo_db)
        self.supported_platforms = {
            'facebook': {
                'name': 'Facebook',
                'oauth_url': 'https://www.facebook.com/v18.0/dialog/oauth',
                'token_url': 'https://graph.facebook.com/v18.0/oauth/access_token',
                'api_base': 'https://graph.facebook.com/v18.0',
                'required_permissions': ['pages_manage_posts', 'pages_read_engagement'],
                'post_types': ['text', 'image', 'video', 'link'],
                'max_post_length': 63206
            },
            'twitter': {
                'name': 'Twitter/X',
                'oauth_url': 'https://twitter.com/i/oauth2/authorize',
                'token_url': 'https://api.twitter.com/2/oauth2/token',
                'api_base': 'https://api.twitter.com/2',
                'required_permissions': ['tweet.read', 'tweet.write', 'users.read'],
                'post_types': ['text', 'image', 'video'],
                'max_post_length': 280
            },
            'instagram': {
                'name': 'Instagram',
                'oauth_url': 'https://api.instagram.com/oauth/authorize',
                'token_url': 'https://api.instagram.com/oauth/access_token',
                'api_base': 'https://graph.instagram.com',
                'required_permissions': ['instagram_basic', 'instagram_content_publish'],
                'post_types': ['image', 'video', 'carousel'],
                'max_post_length': 2200
            },
            'linkedin': {
                'name': 'LinkedIn',
                'oauth_url': 'https://www.linkedin.com/oauth/v2/authorization',
                'token_url': 'https://www.linkedin.com/oauth/v2/accessToken',
                'api_base': 'https://api.linkedin.com/v2',
                'required_permissions': ['w_member_social', 'r_liteprofile'],
                'post_types': ['text', 'image', 'video', 'article'],
                'max_post_length': 3000
            },
            'youtube': {
                'name': 'YouTube',
                'oauth_url': 'https://accounts.google.com/o/oauth2/auth',
                'token_url': 'https://oauth2.googleapis.com/token',
                'api_base': 'https://www.googleapis.com/youtube/v3',
                'required_permissions': ['https://www.googleapis.com/auth/youtube.upload'],
                'post_types': ['video'],
                'max_post_length': 5000
            }
        }
    
    def create_social_account(self, account_data: Dict[str, Any], user_id: Optional[ObjectId] = None) -> ObjectId:
        """Create a new social media account integration."""
        platform = account_data.get('platform', '').lower()
        if platform not in self.supported_platforms:
            raise ValueError(f"Unsupported social media platform: {platform}")
        
        # Encrypt sensitive tokens
        account_data = self._encrypt_account_tokens(account_data)
        
        # Set default values
        account_data.setdefault('is_active', False)
        account_data.setdefault('auto_post_enabled', False)
        account_data.setdefault('sync_enabled', False)
        
        account = SocialMediaAccount(**account_data)
        return self.create(account.to_dict(), user_id)
    
    def get_social_account(self, account_id: ObjectId, decrypt_tokens: bool = False) -> Optional[SocialMediaAccount]:
        """Get a social media account by ID with optional token decryption."""
        data = self.get_by_id(account_id)
        if not data:
            return None
        
        if decrypt_tokens:
            data = self._decrypt_account_tokens(data)
        
        return SocialMediaAccount.from_dict(data)
    
    def update_social_account(self, account_id: ObjectId, update_data: Dict[str, Any], 
                             user_id: Optional[ObjectId] = None) -> bool:
        """Update a social media account configuration."""
        # Encrypt tokens if they're being updated
        if any(field in update_data for field in ['access_token', 'refresh_token']):
            update_data = self._encrypt_account_tokens(update_data)
        
        return self.update(account_id, update_data, user_id)
    
    def get_active_accounts(self) -> List[SocialMediaAccount]:
        """Get all active social media accounts."""
        query = {'is_active': True}
        results = self.find(query)
        return [SocialMediaAccount.from_dict(data) for data in results]
    
    def get_accounts_by_platform(self, platform: str) -> List[SocialMediaAccount]:
        """Get all accounts for a specific platform."""
        query = {'platform': platform.lower()}
        results = self.find(query)
        return [SocialMediaAccount.from_dict(data) for data in results]
    
    def initiate_oauth_flow(self, platform: str, redirect_uri: str, client_id: str) -> Dict[str, Any]:
        """Initiate OAuth flow for a social media platform."""
        if platform.lower() not in self.supported_platforms:
            return {'success': False, 'error': f'Unsupported platform: {platform}'}
        
        platform_config = self.supported_platforms[platform.lower()]
        
        # Generate OAuth URL
        oauth_params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(platform_config['required_permissions']),
            'state': self._generate_oauth_state()
        }
        
        oauth_url = platform_config['oauth_url'] + '?' + '&'.join([
            f"{key}={value}" for key, value in oauth_params.items()
        ])
        
        return {
            'success': True,
            'oauth_url': oauth_url,
            'state': oauth_params['state'],
            'platform': platform
        }
    
    def complete_oauth_flow(self, platform: str, auth_code: str, client_id: str, 
                           client_secret: str, redirect_uri: str) -> Dict[str, Any]:
        """Complete OAuth flow and obtain access tokens."""
        if platform.lower() not in self.supported_platforms:
            return {'success': False, 'error': f'Unsupported platform: {platform}'}
        
        try:
            # Simulate token exchange
            token_data = self._exchange_auth_code_for_tokens(platform, auth_code, client_id, client_secret, redirect_uri)
            
            return {
                'success': True,
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token'),
                'expires_at': token_data.get('expires_at'),
                'permissions': token_data.get('permissions', []),
                'account_info': token_data.get('account_info', {})
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def refresh_access_token(self, account_id: ObjectId) -> Dict[str, Any]:
        """Refresh an expired access token."""
        account = self.get_social_account(account_id, decrypt_tokens=True)
        if not account:
            return {'success': False, 'error': 'Account not found'}
        
        if not account.refresh_token:
            return {'success': False, 'error': 'No refresh token available'}
        
        try:
            # Simulate token refresh
            new_token_data = self._refresh_platform_token(account)
            
            # Update account with new tokens
            update_data = {
                'access_token': new_token_data['access_token'],
                'token_expires_at': new_token_data.get('expires_at')
            }
            
            if 'refresh_token' in new_token_data:
                update_data['refresh_token'] = new_token_data['refresh_token']
            
            self.update_social_account(account_id, update_data)
            
            return {'success': True, 'message': 'Token refreshed successfully'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def post_content(self, account_id: ObjectId, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Post content to a social media platform."""
        account = self.get_social_account(account_id, decrypt_tokens=True)
        if not account:
            return {'success': False, 'error': 'Account not found'}
        
        if not account.is_active:
            return {'success': False, 'error': 'Account is not active'}
        
        # Check if token is expired
        if account.token_expires_at and account.token_expires_at < datetime.utcnow():
            refresh_result = self.refresh_access_token(account_id)
            if not refresh_result['success']:
                return {'success': False, 'error': 'Token expired and refresh failed'}
        
        try:
            # Validate content for platform
            validation_result = self._validate_content_for_platform(account.platform, content_data)
            if not validation_result['valid']:
                return {'success': False, 'error': validation_result['error']}
            
            # Post content to platform
            post_result = self._post_to_platform(account, content_data)
            
            return post_result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def sync_account_data(self, account_id: ObjectId) -> Dict[str, Any]:
        """Sync data from social media platform."""
        account = self.get_social_account(account_id, decrypt_tokens=True)
        if not account:
            return {'success': False, 'error': 'Account not found'}
        
        if not account.sync_enabled:
            return {'success': False, 'error': 'Sync not enabled for this account'}
        
        try:
            # Sync data from platform
            sync_data = self._sync_platform_data(account)
            
            # Update account with sync results
            self.update_social_account(account_id, {
                'last_sync': datetime.utcnow(),
                'sync_results': sync_data
            })
            
            return {
                'success': True,
                'synced_data': sync_data,
                'last_sync': datetime.utcnow()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_account_analytics(self, account_id: ObjectId, date_range: Dict[str, datetime] = None) -> Dict[str, Any]:
        """Get analytics data for a social media account."""
        account = self.get_social_account(account_id, decrypt_tokens=True)
        if not account:
            return {'success': False, 'error': 'Account not found'}
        
        try:
            # Get analytics from platform
            analytics_data = self._get_platform_analytics(account, date_range)
            
            return {
                'success': True,
                'platform': account.platform,
                'account_name': account.account_name,
                'analytics': analytics_data
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_supported_platforms(self) -> Dict[str, Any]:
        """Get list of supported social media platforms and their configurations."""
        return {
            platform: {
                'name': config['name'],
                'post_types': config['post_types'],
                'max_post_length': config['max_post_length'],
                'required_permissions': config['required_permissions']
            }
            for platform, config in self.supported_platforms.items()
        }
    
    def activate_account(self, account_id: ObjectId, user_id: Optional[ObjectId] = None) -> bool:
        """Activate a social media account."""
        return self.update_social_account(account_id, {'is_active': True}, user_id)
    
    def deactivate_account(self, account_id: ObjectId, user_id: Optional[ObjectId] = None) -> bool:
        """Deactivate a social media account."""
        return self.update_social_account(account_id, {'is_active': False}, user_id)
    
    def _encrypt_account_tokens(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive token fields."""
        sensitive_fields = ['access_token', 'refresh_token']
        
        encrypted_data = account_data.copy()
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                # Simple encryption for demo - use proper encryption in production
                encrypted_data[field] = hashlib.sha256(
                    f"{field}:{encrypted_data[field]}".encode()
                ).hexdigest()
        
        return encrypted_data
    
    def _decrypt_account_tokens(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt token fields for API calls."""
        sensitive_fields = ['access_token', 'refresh_token']
        
        decrypted_data = account_data.copy()
        for field in sensitive_fields:
            if field in decrypted_data and decrypted_data[field]:
                # In real implementation, this would properly decrypt
                decrypted_data[field] = f"[ENCRYPTED_{field.upper()}]"
        
        return decrypted_data
    
    def _generate_oauth_state(self) -> str:
        """Generate a secure state parameter for OAuth flow."""
        import secrets
        return secrets.token_urlsafe(32)
    
    def _exchange_auth_code_for_tokens(self, platform: str, auth_code: str, client_id: str, 
                                      client_secret: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens."""
        # Simulate token exchange
        expires_at = datetime.utcnow() + timedelta(hours=2)
        
        return {
            'access_token': f'{platform}_access_token_12345',
            'refresh_token': f'{platform}_refresh_token_67890',
            'expires_at': expires_at,
            'permissions': self.supported_platforms[platform]['required_permissions'],
            'account_info': {
                'id': f'{platform}_account_123',
                'name': f'Test {platform.title()} Account',
                'username': f'test_{platform}_user'
            }
        }
    
    def _refresh_platform_token(self, account: SocialMediaAccount) -> Dict[str, Any]:
        """Refresh access token for a platform."""
        # Simulate token refresh
        expires_at = datetime.utcnow() + timedelta(hours=2)
        
        return {
            'access_token': f'{account.platform}_new_access_token_12345',
            'expires_at': expires_at
        }
    
    def _validate_content_for_platform(self, platform: str, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate content against platform requirements."""
        platform_config = self.supported_platforms.get(platform.lower())
        if not platform_config:
            return {'valid': False, 'error': f'Unsupported platform: {platform}'}
        
        # Check content type
        content_type = content_data.get('type', 'text')
        if content_type not in platform_config['post_types']:
            return {'valid': False, 'error': f'Content type "{content_type}" not supported on {platform}'}
        
        # Check content length
        content_text = content_data.get('text', '')
        if len(content_text) > platform_config['max_post_length']:
            return {'valid': False, 'error': f'Content exceeds maximum length of {platform_config["max_post_length"]} characters'}
        
        return {'valid': True}
    
    def _post_to_platform(self, account: SocialMediaAccount, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Post content to the social media platform."""
        # Simulate posting to platform
        post_id = f'{account.platform}_post_{datetime.utcnow().timestamp()}'
        
        return {
            'success': True,
            'platform': account.platform,
            'post_id': post_id,
            'post_url': f'https://{account.platform}.com/post/{post_id}',
            'posted_at': datetime.utcnow()
        }
    
    def _sync_platform_data(self, account: SocialMediaAccount) -> Dict[str, Any]:
        """Sync data from social media platform."""
        # Simulate data sync
        return {
            'followers_count': 1250,
            'following_count': 180,
            'posts_count': 45,
            'engagement_rate': 3.2,
            'recent_posts': [
                {
                    'id': f'{account.platform}_post_1',
                    'text': 'Sample post content',
                    'likes': 25,
                    'shares': 5,
                    'comments': 3,
                    'posted_at': datetime.utcnow() - timedelta(days=1)
                }
            ]
        }
    
    def _get_platform_analytics(self, account: SocialMediaAccount, date_range: Dict[str, datetime] = None) -> Dict[str, Any]:
        """Get analytics data from social media platform."""
        # Simulate analytics data
        return {
            'impressions': 5420,
            'reach': 3210,
            'engagement': 156,
            'clicks': 89,
            'followers_gained': 12,
            'top_posts': [
                {
                    'id': f'{account.platform}_post_top1',
                    'text': 'Top performing post',
                    'impressions': 1200,
                    'engagement': 45
                }
            ],
            'demographics': {
                'age_groups': {'18-24': 25, '25-34': 40, '35-44': 20, '45+': 15},
                'gender': {'male': 45, 'female': 55},
                'top_locations': ['New York', 'Los Angeles', 'Chicago']
            }
        }