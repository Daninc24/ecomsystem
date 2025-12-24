"""
Shipping API Manager with rate calculation testing
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from ..models.integration import ShippingProvider
from .base_service import BaseService


class ShippingAPIManager(BaseService):
    """Manages shipping provider integrations with rate calculation and testing."""
    
    def _get_collection_name(self) -> str:
        return "shipping_providers"
    
    def __init__(self, mongo_db):
        super().__init__(mongo_db)
        self.supported_providers = {
            'fedex': {
                'name': 'FedEx',
                'required_fields': ['api_key', 'api_secret', 'account_number'],
                'services': ['FEDEX_GROUND', 'FEDEX_EXPRESS_SAVER', 'FEDEX_2_DAY', 'PRIORITY_OVERNIGHT'],
                'tracking_url': 'https://www.fedex.com/fedextrack/?trknbr={tracking_number}',
                'rate_endpoint': 'https://apis.fedex.com/rate/v1/rates/quotes'
            },
            'ups': {
                'name': 'UPS',
                'required_fields': ['api_key', 'username', 'password'],
                'services': ['UPS_GROUND', 'UPS_3_DAY_SELECT', 'UPS_2ND_DAY_AIR', 'UPS_NEXT_DAY_AIR'],
                'tracking_url': 'https://www.ups.com/track?tracknum={tracking_number}',
                'rate_endpoint': 'https://onlinetools.ups.com/rest/Rate'
            },
            'usps': {
                'name': 'USPS',
                'required_fields': ['api_key'],
                'services': ['USPS_GROUND_ADVANTAGE', 'USPS_PRIORITY', 'USPS_EXPRESS', 'USPS_FIRST_CLASS'],
                'tracking_url': 'https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1={tracking_number}',
                'rate_endpoint': 'https://secure.shippingapis.com/ShippingAPI.dll'
            },
            'dhl': {
                'name': 'DHL',
                'required_fields': ['api_key', 'api_secret'],
                'services': ['DHL_EXPRESS_WORLDWIDE', 'DHL_EXPRESS_12:00', 'DHL_EXPRESS_10:30', 'DHL_EXPRESS_9:00'],
                'tracking_url': 'https://www.dhl.com/us-en/home/tracking/tracking-express.html?submit=1&tracking-id={tracking_number}',
                'rate_endpoint': 'https://express.api.dhl.com/mydhlapi/rates'
            }
        }
    
    def create_shipping_provider(self, provider_data: Dict[str, Any], user_id: Optional[ObjectId] = None) -> ObjectId:
        """Create a new shipping provider configuration."""
        provider_name = provider_data.get('provider', '').lower()
        if provider_name not in self.supported_providers:
            raise ValueError(f"Unsupported shipping provider: {provider_name}")
        
        # Validate required fields
        provider_config = self.supported_providers[provider_name]
        self._validate_provider_credentials(provider_data, provider_config)
        
        # Encrypt sensitive credentials
        provider_data = self._encrypt_provider_credentials(provider_data)
        
        # Set default values
        provider_data.setdefault('test_mode', True)
        provider_data.setdefault('is_active', False)
        provider_data.setdefault('supported_services', provider_config['services'])
        provider_data.setdefault('rate_calculation_enabled', True)
        provider_data.setdefault('tracking_enabled', True)
        
        provider = ShippingProvider(**provider_data)
        return self.create(provider.to_dict(), user_id)
    
    def get_shipping_provider(self, provider_id: ObjectId, decrypt_credentials: bool = False) -> Optional[ShippingProvider]:
        """Get a shipping provider by ID with optional credential decryption."""
        data = self.get_by_id(provider_id)
        if not data:
            return None
        
        if decrypt_credentials:
            data = self._decrypt_provider_credentials(data)
        
        return ShippingProvider.from_dict(data)
    
    def update_shipping_provider(self, provider_id: ObjectId, update_data: Dict[str, Any], 
                                user_id: Optional[ObjectId] = None) -> bool:
        """Update a shipping provider configuration."""
        # Encrypt credentials if they're being updated
        if any(field in update_data for field in ['api_key', 'api_secret', 'username', 'password']):
            update_data = self._encrypt_provider_credentials(update_data)
        
        return self.update(provider_id, update_data, user_id)
    
    def get_active_providers(self) -> List[ShippingProvider]:
        """Get all active shipping providers."""
        query = {'is_active': True}
        results = self.find(query)
        return [ShippingProvider.from_dict(data) for data in results]
    
    def calculate_shipping_rates(self, provider_id: ObjectId, shipment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate shipping rates for a given shipment."""
        provider = self.get_shipping_provider(provider_id, decrypt_credentials=True)
        if not provider:
            return {'success': False, 'error': 'Shipping provider not found'}
        
        if not provider.rate_calculation_enabled:
            return {'success': False, 'error': 'Rate calculation not enabled for this provider'}
        
        try:
            # Validate shipment data
            required_fields = ['origin_zip', 'destination_zip', 'weight', 'dimensions']
            for field in required_fields:
                if field not in shipment_data:
                    return {'success': False, 'error': f'Missing required field: {field}'}
            
            # Calculate rates based on provider
            rates = self._calculate_provider_rates(provider, shipment_data)
            
            # Update last rate test timestamp
            self.update_shipping_provider(provider_id, {
                'last_rate_test': datetime.utcnow(),
                'test_results': {'success': True, 'rates_calculated': len(rates)}
            })
            
            return {
                'success': True,
                'provider': provider.provider,
                'rates': rates,
                'currency': 'USD'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_rate_calculation(self, provider_id: ObjectId) -> Dict[str, Any]:
        """Test rate calculation with sample shipment data."""
        sample_shipment = {
            'origin_zip': '10001',
            'destination_zip': '90210',
            'weight': 2.5,  # pounds
            'dimensions': {'length': 12, 'width': 8, 'height': 6},  # inches
            'declared_value': 100.00
        }
        
        return self.calculate_shipping_rates(provider_id, sample_shipment)
    
    def get_tracking_info(self, provider_id: ObjectId, tracking_number: str) -> Dict[str, Any]:
        """Get tracking information for a shipment."""
        provider = self.get_shipping_provider(provider_id)
        if not provider:
            return {'success': False, 'error': 'Shipping provider not found'}
        
        if not provider.tracking_enabled:
            return {'success': False, 'error': 'Tracking not enabled for this provider'}
        
        try:
            # Simulate tracking lookup
            tracking_info = self._get_provider_tracking(provider, tracking_number)
            return {
                'success': True,
                'tracking_number': tracking_number,
                'provider': provider.provider,
                'tracking_info': tracking_info
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def generate_shipping_label(self, provider_id: ObjectId, shipment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a shipping label for a shipment."""
        provider = self.get_shipping_provider(provider_id, decrypt_credentials=True)
        if not provider:
            return {'success': False, 'error': 'Shipping provider not found'}
        
        if not provider.label_printing_enabled:
            return {'success': False, 'error': 'Label printing not enabled for this provider'}
        
        try:
            # Validate shipment data for label generation
            required_fields = ['origin_address', 'destination_address', 'service_type', 'weight']
            for field in required_fields:
                if field not in shipment_data:
                    return {'success': False, 'error': f'Missing required field: {field}'}
            
            # Generate label
            label_data = self._generate_provider_label(provider, shipment_data)
            
            return {
                'success': True,
                'provider': provider.provider,
                'label_data': label_data
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_supported_providers(self) -> Dict[str, Any]:
        """Get list of supported shipping providers and their configurations."""
        return {
            provider: {
                'name': config['name'],
                'services': config['services'],
                'required_fields': config['required_fields']
            }
            for provider, config in self.supported_providers.items()
        }
    
    def activate_provider(self, provider_id: ObjectId, user_id: Optional[ObjectId] = None) -> bool:
        """Activate a shipping provider after successful testing."""
        # Test rate calculation first
        test_result = self.test_rate_calculation(provider_id)
        if not test_result['success']:
            return False
        
        return self.update_shipping_provider(provider_id, {'is_active': True}, user_id)
    
    def deactivate_provider(self, provider_id: ObjectId, user_id: Optional[ObjectId] = None) -> bool:
        """Deactivate a shipping provider."""
        return self.update_shipping_provider(provider_id, {'is_active': False}, user_id)
    
    def _validate_provider_credentials(self, provider_data: Dict[str, Any], provider_config: Dict[str, Any]) -> None:
        """Validate that all required credentials are provided."""
        for field in provider_config['required_fields']:
            if not provider_data.get(field):
                raise ValueError(f"Missing required field: {field}")
    
    def _encrypt_provider_credentials(self, provider_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive credential fields."""
        import hashlib
        sensitive_fields = ['api_key', 'api_secret', 'username', 'password', 'account_number']
        
        encrypted_data = provider_data.copy()
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                # Simple encryption for demo - use proper encryption in production
                encrypted_data[field] = hashlib.sha256(
                    f"{field}:{encrypted_data[field]}".encode()
                ).hexdigest()
        
        return encrypted_data
    
    def _decrypt_provider_credentials(self, provider_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt credential fields for testing purposes."""
        sensitive_fields = ['api_key', 'api_secret', 'username', 'password', 'account_number']
        
        decrypted_data = provider_data.copy()
        for field in sensitive_fields:
            if field in decrypted_data and decrypted_data[field]:
                # In real implementation, this would properly decrypt
                decrypted_data[field] = f"[ENCRYPTED_{field.upper()}]"
        
        return decrypted_data
    
    def _calculate_provider_rates(self, provider: ShippingProvider, shipment_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate shipping rates for a specific provider."""
        # Simulate rate calculation based on provider
        base_rates = {
            'fedex': {'ground': 8.50, 'express': 15.75, '2day': 12.25, 'overnight': 25.00},
            'ups': {'ground': 8.25, '3day': 11.50, '2day': 13.75, 'nextday': 24.50},
            'usps': {'ground': 6.75, 'priority': 9.25, 'express': 18.50, 'firstclass': 4.25},
            'dhl': {'worldwide': 22.00, 'express12': 28.50, 'express1030': 32.75, 'express900': 38.00}
        }
        
        provider_rates = base_rates.get(provider.provider.lower(), {})
        weight = shipment_data.get('weight', 1.0)
        
        rates = []
        for service in provider.supported_services:
            service_key = service.lower().split('_')[-1]  # Get last part of service name
            base_rate = provider_rates.get(service_key, 10.00)
            
            # Calculate rate based on weight (simple linear calculation)
            calculated_rate = base_rate + (weight * 1.5)
            
            rates.append({
                'service_type': service,
                'service_name': service.replace('_', ' ').title(),
                'rate': round(calculated_rate, 2),
                'estimated_days': self._get_estimated_delivery_days(service),
                'currency': 'USD'
            })
        
        return rates
    
    def _get_estimated_delivery_days(self, service_type: str) -> int:
        """Get estimated delivery days for a service type."""
        delivery_days = {
            'ground': 5,
            'express': 2,
            '2day': 2,
            '3day': 3,
            'overnight': 1,
            'nextday': 1,
            'priority': 3,
            'firstclass': 7,
            'worldwide': 3,
            'express12': 1,
            'express1030': 1,
            'express900': 1
        }
        
        for key in delivery_days:
            if key in service_type.lower():
                return delivery_days[key]
        
        return 5  # Default to 5 days
    
    def _get_provider_tracking(self, provider: ShippingProvider, tracking_number: str) -> Dict[str, Any]:
        """Get tracking information from provider."""
        # Simulate tracking information
        return {
            'status': 'In Transit',
            'location': 'Distribution Center - Chicago, IL',
            'estimated_delivery': '2024-01-15',
            'tracking_events': [
                {
                    'timestamp': '2024-01-12 10:30:00',
                    'status': 'Package picked up',
                    'location': 'New York, NY'
                },
                {
                    'timestamp': '2024-01-13 08:15:00',
                    'status': 'In transit',
                    'location': 'Chicago, IL'
                }
            ]
        }
    
    def _generate_provider_label(self, provider: ShippingProvider, shipment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate shipping label data."""
        # Simulate label generation
        return {
            'label_url': f'https://labels.{provider.provider}.com/label_12345.pdf',
            'tracking_number': f'{provider.provider.upper()}123456789',
            'label_format': 'PDF',
            'label_size': '4x6',
            'postage_cost': 8.50
        }