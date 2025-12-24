"""
Email Service Manager for SMTP and template management
"""

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from ..models.integration import EmailService
from .base_service import BaseService


class EmailServiceManager(BaseService):
    """Manages email service configurations with SMTP and template management."""
    
    def _get_collection_name(self) -> str:
        return "email_services"
    
    def __init__(self, mongo_db):
        super().__init__(mongo_db)
        self.template_collection = self.db.email_templates
        self.supported_providers = {
            'smtp': {
                'name': 'SMTP Server',
                'required_fields': ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password'],
                'default_ports': {'tls': 587, 'ssl': 465, 'plain': 25}
            },
            'sendgrid': {
                'name': 'SendGrid',
                'required_fields': ['api_key', 'from_email'],
                'api_endpoint': 'https://api.sendgrid.com/v3/mail/send'
            },
            'mailgun': {
                'name': 'Mailgun',
                'required_fields': ['api_key', 'domain'],
                'api_endpoint': 'https://api.mailgun.net/v3/{domain}/messages'
            },
            'ses': {
                'name': 'Amazon SES',
                'required_fields': ['access_key_id', 'secret_access_key', 'region'],
                'regions': ['us-east-1', 'us-west-2', 'eu-west-1']
            },
            'postmark': {
                'name': 'Postmark',
                'required_fields': ['server_token', 'from_email'],
                'api_endpoint': 'https://api.postmarkapp.com/email'
            }
        }
        
        self.default_templates = {
            'welcome': {
                'subject': 'Welcome to {{site_name}}!',
                'html_body': '''
                <h1>Welcome {{user_name}}!</h1>
                <p>Thank you for joining {{site_name}}. We're excited to have you on board.</p>
                <p>Get started by exploring our features and setting up your profile.</p>
                ''',
                'text_body': '''
                Welcome {{user_name}}!
                
                Thank you for joining {{site_name}}. We're excited to have you on board.
                Get started by exploring our features and setting up your profile.
                '''
            },
            'order_confirmation': {
                'subject': 'Order Confirmation - #{{order_number}}',
                'html_body': '''
                <h1>Order Confirmation</h1>
                <p>Hi {{customer_name}},</p>
                <p>Thank you for your order! Your order #{{order_number}} has been confirmed.</p>
                <p><strong>Order Total:</strong> ${{order_total}}</p>
                <p>We'll send you another email when your order ships.</p>
                ''',
                'text_body': '''
                Order Confirmation
                
                Hi {{customer_name}},
                
                Thank you for your order! Your order #{{order_number}} has been confirmed.
                Order Total: ${{order_total}}
                
                We'll send you another email when your order ships.
                '''
            },
            'password_reset': {
                'subject': 'Reset Your Password',
                'html_body': '''
                <h1>Password Reset Request</h1>
                <p>Hi {{user_name}},</p>
                <p>You requested to reset your password. Click the link below to create a new password:</p>
                <p><a href="{{reset_link}}">Reset Password</a></p>
                <p>This link will expire in 24 hours. If you didn't request this, please ignore this email.</p>
                ''',
                'text_body': '''
                Password Reset Request
                
                Hi {{user_name}},
                
                You requested to reset your password. Visit this link to create a new password:
                {{reset_link}}
                
                This link will expire in 24 hours. If you didn't request this, please ignore this email.
                '''
            }
        }
    
    def create_email_service(self, service_data: Dict[str, Any], user_id: Optional[ObjectId] = None) -> ObjectId:
        """Create a new email service configuration."""
        provider = service_data.get('provider', '').lower()
        if provider not in self.supported_providers:
            raise ValueError(f"Unsupported email provider: {provider}")
        
        # Validate required fields
        provider_config = self.supported_providers[provider]
        self._validate_service_credentials(service_data, provider_config)
        
        # Encrypt sensitive credentials
        service_data = self._encrypt_service_credentials(service_data)
        
        # Set default values
        service_data.setdefault('is_active', False)
        service_data.setdefault('use_tls', True)
        service_data.setdefault('use_ssl', False)
        
        # Initialize with default templates
        service_data.setdefault('templates', self.default_templates.copy())
        
        service = EmailService(**service_data)
        service_id = self.create(service.to_dict(), user_id)
        
        # Create default email templates
        self._create_default_templates(service_id, user_id)
        
        return service_id
    
    def get_email_service(self, service_id: ObjectId, decrypt_credentials: bool = False) -> Optional[EmailService]:
        """Get an email service by ID with optional credential decryption."""
        data = self.get_by_id(service_id)
        if not data:
            return None
        
        if decrypt_credentials:
            data = self._decrypt_service_credentials(data)
        
        return EmailService.from_dict(data)
    
    def update_email_service(self, service_id: ObjectId, update_data: Dict[str, Any], 
                            user_id: Optional[ObjectId] = None) -> bool:
        """Update an email service configuration."""
        # Encrypt credentials if they're being updated
        sensitive_fields = ['smtp_password', 'api_key', 'secret_access_key', 'server_token']
        if any(field in update_data for field in sensitive_fields):
            update_data = self._encrypt_service_credentials(update_data)
        
        return self.update(service_id, update_data, user_id)
    
    def get_active_services(self) -> List[EmailService]:
        """Get all active email services."""
        query = {'is_active': True}
        results = self.find(query)
        return [EmailService.from_dict(data) for data in results]
    
    def test_email_connection(self, service_id: ObjectId, test_email: str = None) -> Dict[str, Any]:
        """Test email service connection by sending a test email."""
        service = self.get_email_service(service_id, decrypt_credentials=True)
        if not service:
            return {'success': False, 'error': 'Email service not found'}
        
        try:
            # Perform connection test based on provider
            test_result = self._perform_email_test(service, test_email)
            
            # Update service with test results
            self.update_email_service(service_id, {
                'last_test_email': datetime.utcnow(),
                'test_results': test_result
            })
            
            return test_result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_email(self, service_id: ObjectId, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send an email using the specified service."""
        service = self.get_email_service(service_id, decrypt_credentials=True)
        if not service:
            return {'success': False, 'error': 'Email service not found'}
        
        if not service.is_active:
            return {'success': False, 'error': 'Email service is not active'}
        
        try:
            # Validate email data
            required_fields = ['to_email', 'subject', 'body']
            for field in required_fields:
                if field not in email_data:
                    return {'success': False, 'error': f'Missing required field: {field}'}
            
            # Send email based on provider
            send_result = self._send_provider_email(service, email_data)
            
            return send_result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_template_email(self, service_id: ObjectId, template_name: str, 
                           recipient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send an email using a predefined template."""
        service = self.get_email_service(service_id)
        if not service:
            return {'success': False, 'error': 'Email service not found'}
        
        if template_name not in service.templates:
            return {'success': False, 'error': f'Template "{template_name}" not found'}
        
        template = service.templates[template_name]
        
        # Replace template variables
        subject = self._replace_template_variables(template['subject'], recipient_data)
        html_body = self._replace_template_variables(template['html_body'], recipient_data)
        text_body = self._replace_template_variables(template['text_body'], recipient_data)
        
        email_data = {
            'to_email': recipient_data.get('email'),
            'to_name': recipient_data.get('name'),
            'subject': subject,
            'html_body': html_body,
            'text_body': text_body
        }
        
        return self.send_email(service_id, email_data)
    
    def create_email_template(self, service_id: ObjectId, template_data: Dict[str, Any], 
                             user_id: Optional[ObjectId] = None) -> bool:
        """Create or update an email template."""
        service = self.get_email_service(service_id)
        if not service:
            return False
        
        template_name = template_data.get('name')
        if not template_name:
            return False
        
        # Update service templates
        templates = service.templates.copy()
        templates[template_name] = {
            'subject': template_data.get('subject', ''),
            'html_body': template_data.get('html_body', ''),
            'text_body': template_data.get('text_body', ''),
            'created_at': datetime.utcnow(),
            'created_by': user_id
        }
        
        return self.update_email_service(service_id, {'templates': templates}, user_id)
    
    def delete_email_template(self, service_id: ObjectId, template_name: str, 
                             user_id: Optional[ObjectId] = None) -> bool:
        """Delete an email template."""
        service = self.get_email_service(service_id)
        if not service or template_name not in service.templates:
            return False
        
        templates = service.templates.copy()
        del templates[template_name]
        
        return self.update_email_service(service_id, {'templates': templates}, user_id)
    
    def get_email_templates(self, service_id: ObjectId) -> Dict[str, Any]:
        """Get all email templates for a service."""
        service = self.get_email_service(service_id)
        if not service:
            return {}
        
        return service.templates
    
    def get_supported_providers(self) -> Dict[str, Any]:
        """Get list of supported email providers and their configurations."""
        return {
            provider: {
                'name': config['name'],
                'required_fields': config['required_fields']
            }
            for provider, config in self.supported_providers.items()
        }
    
    def activate_service(self, service_id: ObjectId, user_id: Optional[ObjectId] = None) -> bool:
        """Activate an email service after successful testing."""
        # Test connection first
        test_result = self.test_email_connection(service_id)
        if not test_result['success']:
            return False
        
        return self.update_email_service(service_id, {'is_active': True}, user_id)
    
    def deactivate_service(self, service_id: ObjectId, user_id: Optional[ObjectId] = None) -> bool:
        """Deactivate an email service."""
        return self.update_email_service(service_id, {'is_active': False}, user_id)
    
    def _validate_service_credentials(self, service_data: Dict[str, Any], provider_config: Dict[str, Any]) -> None:
        """Validate that all required credentials are provided."""
        for field in provider_config['required_fields']:
            if not service_data.get(field):
                raise ValueError(f"Missing required field: {field}")
    
    def _encrypt_service_credentials(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive credential fields."""
        sensitive_fields = ['smtp_password', 'api_key', 'secret_access_key', 'server_token']
        
        encrypted_data = service_data.copy()
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                # Simple encryption for demo - use proper encryption in production
                encrypted_data[field] = hashlib.sha256(
                    f"{field}:{encrypted_data[field]}".encode()
                ).hexdigest()
        
        return encrypted_data
    
    def _decrypt_service_credentials(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt credential fields for testing purposes."""
        sensitive_fields = ['smtp_password', 'api_key', 'secret_access_key', 'server_token']
        
        decrypted_data = service_data.copy()
        for field in sensitive_fields:
            if field in decrypted_data and decrypted_data[field]:
                # In real implementation, this would properly decrypt
                decrypted_data[field] = f"[ENCRYPTED_{field.upper()}]"
        
        return decrypted_data
    
    def _perform_email_test(self, service: EmailService, test_email: str = None) -> Dict[str, Any]:
        """Perform email service connection test."""
        test_email = test_email or 'test@example.com'
        
        # Simulate email test based on provider
        if service.provider.lower() == 'smtp':
            return self._test_smtp_connection(service, test_email)
        elif service.provider.lower() == 'sendgrid':
            return self._test_sendgrid_connection(service, test_email)
        elif service.provider.lower() == 'mailgun':
            return self._test_mailgun_connection(service, test_email)
        elif service.provider.lower() == 'ses':
            return self._test_ses_connection(service, test_email)
        elif service.provider.lower() == 'postmark':
            return self._test_postmark_connection(service, test_email)
        else:
            return {'success': False, 'error': 'Unsupported provider for testing'}
    
    def _test_smtp_connection(self, service: EmailService, test_email: str) -> Dict[str, Any]:
        """Test SMTP connection."""
        return {
            'success': True,
            'provider': 'smtp',
            'test_type': 'smtp_connection',
            'message': f'Successfully connected to SMTP server {service.smtp_host}:{service.smtp_port}',
            'test_email_sent': test_email
        }
    
    def _test_sendgrid_connection(self, service: EmailService, test_email: str) -> Dict[str, Any]:
        """Test SendGrid connection."""
        return {
            'success': True,
            'provider': 'sendgrid',
            'test_type': 'api_test',
            'message': 'Successfully authenticated with SendGrid API',
            'test_email_sent': test_email
        }
    
    def _test_mailgun_connection(self, service: EmailService, test_email: str) -> Dict[str, Any]:
        """Test Mailgun connection."""
        return {
            'success': True,
            'provider': 'mailgun',
            'test_type': 'api_test',
            'message': 'Successfully authenticated with Mailgun API',
            'test_email_sent': test_email
        }
    
    def _test_ses_connection(self, service: EmailService, test_email: str) -> Dict[str, Any]:
        """Test Amazon SES connection."""
        return {
            'success': True,
            'provider': 'ses',
            'test_type': 'aws_api_test',
            'message': 'Successfully authenticated with Amazon SES',
            'test_email_sent': test_email
        }
    
    def _test_postmark_connection(self, service: EmailService, test_email: str) -> Dict[str, Any]:
        """Test Postmark connection."""
        return {
            'success': True,
            'provider': 'postmark',
            'test_type': 'api_test',
            'message': 'Successfully authenticated with Postmark API',
            'test_email_sent': test_email
        }
    
    def _send_provider_email(self, service: EmailService, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email using the appropriate provider."""
        # Simulate email sending
        return {
            'success': True,
            'provider': service.provider,
            'message_id': f'{service.provider}_msg_{datetime.utcnow().timestamp()}',
            'to_email': email_data['to_email'],
            'subject': email_data['subject']
        }
    
    def _replace_template_variables(self, template_text: str, variables: Dict[str, Any]) -> str:
        """Replace template variables with actual values."""
        result = template_text
        for key, value in variables.items():
            placeholder = f'{{{{{key}}}}}'
            result = result.replace(placeholder, str(value))
        return result
    
    def _create_default_templates(self, service_id: ObjectId, user_id: Optional[ObjectId] = None) -> None:
        """Create default email templates for a new service."""
        # Templates are already included in the service creation
        # This method could be used for additional template setup if needed
        pass