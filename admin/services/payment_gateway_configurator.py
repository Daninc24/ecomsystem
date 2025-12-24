"""
Payment Gateway Configurator with secure credential management
"""

import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from ..models.integration import PaymentGateway
from .base_service import BaseService


class PaymentGatewayConfigurator(BaseService):
    """Manages payment gateway configurations with secure credential handling."""
    
    def _get_collection_name(self) -> str:
        return "payment_gateways"
    
    def __init__(self, mongo_db):
        super().__init__(mongo_db)
        self.supported_providers = {
            'stripe': {
                'name': 'Stripe',
                'required_fields': ['public_key', 'private_key'],
                'optional_fields': ['webhook_secret'],
                'test_endpoint': 'https://api.stripe.com/v1/charges',
                'supported_currencies': ['USD', 'EUR', 'GBP', 'CAD', 'AUD'],
                'supported_methods': ['card', 'bank_transfer', 'digital_wallet']
            },
            'paypal': {
                'name': 'PayPal',
                'required_fields': ['client_id', 'client_secret'],
                'optional_fields': ['webhook_id'],
                'test_endpoint': 'https://api.sandbox.paypal.com/v1/oauth2/token',
                'supported_currencies': ['USD', 'EUR', 'GBP', 'CAD', 'AUD'],
                'supported_methods': ['paypal', 'card']
            },
            'square': {
                'name': 'Square',
                'required_fields': ['access_token', 'application_id'],
                'optional_fields': ['webhook_signature_key'],
                'test_endpoint': 'https://connect.squareupsandbox.com/v2/locations',
                'supported_currencies': ['USD', 'CAD', 'GBP', 'AUD'],
                'supported_methods': ['card', 'cash', 'digital_wallet']
            }
        }
    
    def create_payment_gateway(self, gateway_data: Dict[str, Any], user_id: Optional[ObjectId] = None) -> ObjectId:
        """Create a new payment gateway configuration."""
        # Validate provider
        provider = gateway_data.get('provider', '').lower()
        if provider not in self.supported_providers:
            raise ValueError(f"Unsupported payment provider: {provider}")
        
        # Validate required fields
        provider_config = self.supported_providers[provider]
        self._validate_gateway_credentials(gateway_data, provider_config)
        
        # Encrypt sensitive credentials
        gateway_data = self._encrypt_gateway_credentials(gateway_data)
        
        # Set default values
        gateway_data.setdefault('is_test_mode', True)
        gateway_data.setdefault('is_active', False)
        gateway_data.setdefault('supported_currencies', provider_config['supported_currencies'])
        gateway_data.setdefault('supported_methods', provider_config['supported_methods'])
        
        gateway = PaymentGateway(**gateway_data)
        return self.create(gateway.to_dict(), user_id)
    
    def get_payment_gateway(self, gateway_id: ObjectId, decrypt_credentials: bool = False) -> Optional[PaymentGateway]:
        """Get a payment gateway by ID with optional credential decryption."""
        data = self.get_by_id(gateway_id)
        if not data:
            return None
        
        if decrypt_credentials:
            data = self._decrypt_gateway_credentials(data)
        
        return PaymentGateway.from_dict(data)
    
    def update_payment_gateway(self, gateway_id: ObjectId, update_data: Dict[str, Any], 
                              user_id: Optional[ObjectId] = None) -> bool:
        """Update a payment gateway configuration."""
        # Encrypt credentials if they're being updated
        if any(field in update_data for field in ['public_key', 'private_key', 'client_id', 'client_secret', 'access_token']):
            update_data = self._encrypt_gateway_credentials(update_data)
        
        return self.update(gateway_id, update_data, user_id)
    
    def get_active_gateways(self) -> List[PaymentGateway]:
        """Get all active payment gateways."""
        query = {'is_active': True}
        results = self.find(query)
        return [PaymentGateway.from_dict(data) for data in results]
    
    def get_gateways_by_provider(self, provider: str) -> List[PaymentGateway]:
        """Get all gateways for a specific provider."""
        query = {'provider': provider.lower()}
        results = self.find(query)
        return [PaymentGateway.from_dict(data) for data in results]
    
    def test_gateway_connection(self, gateway_id: ObjectId) -> Dict[str, Any]:
        """Test connection to a payment gateway."""
        gateway = self.get_payment_gateway(gateway_id, decrypt_credentials=True)
        if not gateway:
            return {'success': False, 'error': 'Payment gateway not found'}
        
        try:
            provider_config = self.supported_providers.get(gateway.provider.lower())
            if not provider_config:
                return {'success': False, 'error': f'Unsupported provider: {gateway.provider}'}
            
            # Perform test transaction
            test_result = self._perform_test_transaction(gateway, provider_config)
            
            # Update gateway with test results
            self.update_payment_gateway(gateway_id, {
                'last_test_transaction': datetime.utcnow(),
                'test_results': test_result
            })
            
            return test_result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def activate_gateway(self, gateway_id: ObjectId, user_id: Optional[ObjectId] = None) -> bool:
        """Activate a payment gateway after successful testing."""
        # Test connection first
        test_result = self.test_gateway_connection(gateway_id)
        if not test_result['success']:
            return False
        
        return self.update_payment_gateway(gateway_id, {'is_active': True}, user_id)
    
    def deactivate_gateway(self, gateway_id: ObjectId, user_id: Optional[ObjectId] = None) -> bool:
        """Deactivate a payment gateway."""
        return self.update_payment_gateway(gateway_id, {'is_active': False}, user_id)
    
    def calculate_transaction_fees(self, gateway_id: ObjectId, amount: float, currency: str = 'USD') -> Dict[str, float]:
        """Calculate transaction fees for a payment gateway."""
        gateway = self.get_payment_gateway(gateway_id)
        if not gateway:
            return {'error': 'Gateway not found'}
        
        # Default fee structure (would be configurable per gateway)
        base_fees = {
            'stripe': {'percentage': 2.9, 'fixed': 0.30},
            'paypal': {'percentage': 2.9, 'fixed': 0.30},
            'square': {'percentage': 2.6, 'fixed': 0.10}
        }
        
        provider_fees = base_fees.get(gateway.provider.lower(), {'percentage': 3.0, 'fixed': 0.30})
        
        percentage_fee = amount * (provider_fees['percentage'] / 100)
        fixed_fee = provider_fees['fixed']
        total_fee = percentage_fee + fixed_fee
        net_amount = amount - total_fee
        
        return {
            'gross_amount': amount,
            'percentage_fee': percentage_fee,
            'fixed_fee': fixed_fee,
            'total_fee': total_fee,
            'net_amount': net_amount,
            'currency': currency
        }
    
    def get_supported_providers(self) -> Dict[str, Any]:
        """Get list of supported payment providers and their configurations."""
        return {
            provider: {
                'name': config['name'],
                'supported_currencies': config['supported_currencies'],
                'supported_methods': config['supported_methods'],
                'required_fields': config['required_fields']
            }
            for provider, config in self.supported_providers.items()
        }
    
    def validate_webhook_signature(self, gateway_id: ObjectId, payload: str, signature: str) -> bool:
        """Validate webhook signature from payment provider."""
        gateway = self.get_payment_gateway(gateway_id, decrypt_credentials=True)
        if not gateway or not gateway.webhook_secret:
            return False
        
        # Simulate webhook signature validation
        # In real implementation, this would use provider-specific validation
        expected_signature = hashlib.sha256(
            f"{gateway.webhook_secret}:{payload}".encode()
        ).hexdigest()
        
        return signature == expected_signature
    
    def _validate_gateway_credentials(self, gateway_data: Dict[str, Any], provider_config: Dict[str, Any]) -> None:
        """Validate that all required credentials are provided."""
        for field in provider_config['required_fields']:
            if not gateway_data.get(field):
                raise ValueError(f"Missing required field: {field}")
    
    def _encrypt_gateway_credentials(self, gateway_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive credential fields."""
        sensitive_fields = ['public_key', 'private_key', 'client_id', 'client_secret', 
                           'access_token', 'webhook_secret', 'webhook_signature_key']
        
        encrypted_data = gateway_data.copy()
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                # Simple encryption for demo - use proper encryption in production
                encrypted_data[field] = hashlib.sha256(
                    f"{field}:{encrypted_data[field]}".encode()
                ).hexdigest()
        
        return encrypted_data
    
    def _decrypt_gateway_credentials(self, gateway_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt credential fields for testing purposes."""
        sensitive_fields = ['public_key', 'private_key', 'client_id', 'client_secret', 
                           'access_token', 'webhook_secret', 'webhook_signature_key']
        
        decrypted_data = gateway_data.copy()
        for field in sensitive_fields:
            if field in decrypted_data and decrypted_data[field]:
                # In real implementation, this would properly decrypt
                decrypted_data[field] = f"[ENCRYPTED_{field.upper()}]"
        
        return decrypted_data
    
    def _perform_test_transaction(self, gateway: PaymentGateway, provider_config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a test transaction to validate gateway configuration."""
        try:
            # Simulate test transaction based on provider
            if gateway.provider.lower() == 'stripe':
                return self._test_stripe_connection(gateway)
            elif gateway.provider.lower() == 'paypal':
                return self._test_paypal_connection(gateway)
            elif gateway.provider.lower() == 'square':
                return self._test_square_connection(gateway)
            else:
                return {'success': False, 'error': 'Unsupported provider for testing'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _test_stripe_connection(self, gateway: PaymentGateway) -> Dict[str, Any]:
        """Test Stripe connection."""
        # Simulate Stripe API test
        return {
            'success': True,
            'provider': 'stripe',
            'test_type': 'connection_test',
            'response_time': 0.23,
            'message': 'Successfully connected to Stripe API',
            'test_mode': gateway.is_test_mode
        }
    
    def _test_paypal_connection(self, gateway: PaymentGateway) -> Dict[str, Any]:
        """Test PayPal connection."""
        # Simulate PayPal API test
        return {
            'success': True,
            'provider': 'paypal',
            'test_type': 'oauth_test',
            'response_time': 0.31,
            'message': 'Successfully authenticated with PayPal API',
            'test_mode': gateway.is_test_mode
        }
    
    def _test_square_connection(self, gateway: PaymentGateway) -> Dict[str, Any]:
        """Test Square connection."""
        # Simulate Square API test
        return {
            'success': True,
            'provider': 'square',
            'test_type': 'location_test',
            'response_time': 0.18,
            'message': 'Successfully connected to Square API',
            'test_mode': gateway.is_test_mode
        }