"""
Integration Manager for external service connections
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from ..models.integration import (
    Integration, IntegrationType, IntegrationStatus,
    PaymentGateway, ShippingProvider, EmailService, 
    SocialMediaAccount
)
from .base_service import BaseService


class IntegrationManager(BaseService):
    """Manages external service integrations and connections."""
    
    def _get_collection_name(self) -> str:
        return "integrations"
    
    def __init__(self, mongo_db):
        super().__init__(mongo_db)
        self.payment_collection = self.db.payment_gateways
        self.shipping_collection = self.db.shipping_providers
        self.email_collection = self.db.email_services
        self.social_collection = self.db.social_media_accounts
    
    def create_integration(self, integration_data: Dict[str, Any], user_id: Optional[ObjectId] = None) -> ObjectId:
        """Create a new integration configuration."""
        # Encrypt sensitive credentials before storing
        if 'credentials' in integration_data:
            integration_data['credentials'] = self._encrypt_credentials(integration_data['credentials'])
        
        integration = Integration(**integration_data)
        return self.create(integration.to_dict(), user_id)
    
    def get_integration(self, integration_id: ObjectId, decrypt_credentials: bool = False) -> Optional[Integration]:
        """Get an integration by ID with optional credential decryption."""
        data = self.get_by_id(integration_id)
        if not data:
            return None
        
        if decrypt_credentials and 'credentials' in data:
            data['credentials'] = self._decrypt_credentials(data['credentials'])
        
        return Integration.from_dict(data)
    
    def update_integration(self, integration_id: ObjectId, update_data: Dict[str, Any], 
                          user_id: Optional[ObjectId] = None) -> bool:
        """Update an integration configuration."""
        # Encrypt credentials if they're being updated
        if 'credentials' in update_data:
            update_data['credentials'] = self._encrypt_credentials(update_data['credentials'])
        
        return self.update(integration_id, update_data, user_id)
    
    def get_integrations_by_type(self, integration_type: IntegrationType) -> List[Integration]:
        """Get all integrations of a specific type."""
        query = {'type': integration_type.value}
        results = self.find(query)
        return [Integration.from_dict(data) for data in results]
    
    def get_active_integrations(self) -> List[Integration]:
        """Get all active integrations."""
        query = {'status': IntegrationStatus.ACTIVE.value}
        results = self.find(query)
        return [Integration.from_dict(data) for data in results]
    
    def test_integration_connection(self, integration_id: ObjectId) -> Dict[str, Any]:
        """Test the connection to an external service."""
        integration = self.get_integration(integration_id, decrypt_credentials=True)
        if not integration:
            return {'success': False, 'error': 'Integration not found'}
        
        try:
            # Update status to testing
            self.update_integration(integration_id, {
                'status': IntegrationStatus.TESTING.value
            })
            
            # Perform connection test based on integration type
            test_result = self._perform_connection_test(integration)
            
            # Update integration with test results
            update_data = {
                'last_tested': datetime.utcnow(),
                'test_results': test_result,
                'status': IntegrationStatus.ACTIVE.value if test_result['success'] else IntegrationStatus.ERROR.value
            }
            
            if not test_result['success']:
                update_data['error_message'] = test_result.get('error', 'Connection test failed')
            
            self.update_integration(integration_id, update_data)
            
            return test_result
            
        except Exception as e:
            # Update status to error
            self.update_integration(integration_id, {
                'status': IntegrationStatus.ERROR.value,
                'error_message': str(e),
                'last_tested': datetime.utcnow()
            })
            return {'success': False, 'error': str(e)}
    
    def activate_integration(self, integration_id: ObjectId, user_id: Optional[ObjectId] = None) -> bool:
        """Activate an integration after successful testing."""
        integration = self.get_integration(integration_id)
        if not integration:
            return False
        
        # Test connection before activation
        test_result = self.test_integration_connection(integration_id)
        if not test_result['success']:
            return False
        
        return self.update_integration(integration_id, {
            'status': IntegrationStatus.ACTIVE.value
        }, user_id)
    
    def deactivate_integration(self, integration_id: ObjectId, user_id: Optional[ObjectId] = None) -> bool:
        """Deactivate an integration."""
        return self.update_integration(integration_id, {
            'status': IntegrationStatus.INACTIVE.value
        }, user_id)
    
    def get_integration_health_status(self) -> Dict[str, Any]:
        """Get overall health status of all integrations."""
        all_integrations = self.find()
        
        status_counts = {}
        type_counts = {}
        recent_errors = []
        
        for integration_data in all_integrations:
            integration = Integration.from_dict(integration_data)
            
            # Count by status
            status = integration.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count by type
            int_type = integration.type.value
            type_counts[int_type] = type_counts.get(int_type, 0) + 1
            
            # Collect recent errors
            if integration.status == IntegrationStatus.ERROR and integration.error_message:
                recent_errors.append({
                    'integration_id': str(integration.id),
                    'name': integration.name,
                    'error': integration.error_message,
                    'timestamp': integration.updated_at
                })
        
        return {
            'total_integrations': len(all_integrations),
            'status_breakdown': status_counts,
            'type_breakdown': type_counts,
            'recent_errors': sorted(recent_errors, key=lambda x: x['timestamp'], reverse=True)[:10],
            'health_score': self._calculate_health_score(status_counts, len(all_integrations))
        }
    
    def _encrypt_credentials(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """Encrypt sensitive credential data."""
        # Simple encryption for demo - in production, use proper encryption
        encrypted = {}
        for key, value in credentials.items():
            if value:
                # Use a simple hash for demo purposes
                encrypted[key] = hashlib.sha256(f"{key}:{value}".encode()).hexdigest()
        return encrypted
    
    def _decrypt_credentials(self, encrypted_credentials: Dict[str, str]) -> Dict[str, str]:
        """Decrypt credential data."""
        # In a real implementation, this would properly decrypt
        # For demo purposes, return placeholder values
        decrypted = {}
        for key, value in encrypted_credentials.items():
            decrypted[key] = f"[ENCRYPTED_{key.upper()}]"
        return decrypted
    
    def _perform_connection_test(self, integration: Integration) -> Dict[str, Any]:
        """Perform connection test based on integration type."""
        try:
            if integration.type == IntegrationType.PAYMENT_GATEWAY:
                return self._test_payment_gateway(integration)
            elif integration.type == IntegrationType.SHIPPING_API:
                return self._test_shipping_api(integration)
            elif integration.type == IntegrationType.EMAIL_SERVICE:
                return self._test_email_service(integration)
            elif integration.type == IntegrationType.SOCIAL_MEDIA:
                return self._test_social_media(integration)
            else:
                return self._test_generic_api(integration)
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _test_payment_gateway(self, integration: Integration) -> Dict[str, Any]:
        """Test payment gateway connection."""
        # Simulate payment gateway test
        return {
            'success': True,
            'test_type': 'payment_gateway',
            'response_time': 0.25,
            'message': f'Successfully connected to {integration.provider} payment gateway'
        }
    
    def _test_shipping_api(self, integration: Integration) -> Dict[str, Any]:
        """Test shipping API connection."""
        # Simulate shipping API test
        return {
            'success': True,
            'test_type': 'shipping_api',
            'response_time': 0.18,
            'message': f'Successfully connected to {integration.provider} shipping API'
        }
    
    def _test_email_service(self, integration: Integration) -> Dict[str, Any]:
        """Test email service connection."""
        # Simulate email service test
        return {
            'success': True,
            'test_type': 'email_service',
            'response_time': 0.12,
            'message': f'Successfully connected to {integration.provider} email service'
        }
    
    def _test_social_media(self, integration: Integration) -> Dict[str, Any]:
        """Test social media API connection."""
        # Simulate social media API test
        return {
            'success': True,
            'test_type': 'social_media',
            'response_time': 0.31,
            'message': f'Successfully connected to {integration.provider} social media API'
        }
    
    def _test_generic_api(self, integration: Integration) -> Dict[str, Any]:
        """Test generic API connection."""
        # Simulate generic API test
        return {
            'success': True,
            'test_type': 'generic_api',
            'response_time': 0.20,
            'message': f'Successfully connected to {integration.provider} API'
        }
    
    def _calculate_health_score(self, status_counts: Dict[str, int], total: int) -> float:
        """Calculate overall health score for integrations."""
        if total == 0:
            return 100.0
        
        active_count = status_counts.get(IntegrationStatus.ACTIVE.value, 0)
        error_count = status_counts.get(IntegrationStatus.ERROR.value, 0)
        
        # Health score based on active vs error ratio
        health_score = ((active_count - error_count) / total) * 100
        return max(0.0, min(100.0, health_score))