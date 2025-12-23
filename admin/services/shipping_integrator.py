"""
Shipping integration service for managing shipping providers and tracking
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId

from ..models.order import ShippingIntegration, ShippingStatus
from .base_service import BaseService


class ShippingIntegrator(BaseService):
    """Service for integrating with shipping providers."""
    
    def __init__(self, db_client):
        super().__init__(db_client)
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'shipping_integrations'
    
    def create_integration(self, integration_data: Dict[str, Any], user_id: ObjectId) -> ShippingIntegration:
        """Create a new shipping integration."""
        integration = ShippingIntegration(**integration_data)
        integration.created_by = user_id
        
        # Insert into database
        result = self.db.shipping_integrations.insert_one(integration.to_dict())
        integration.id = result.inserted_id
        
        return integration
    
    def get_integration(self, integration_id: ObjectId) -> Optional[ShippingIntegration]:
        """Get shipping integration by ID."""
        integration_data = self.db.shipping_integrations.find_one({'_id': integration_id})
        if integration_data:
            return ShippingIntegration.from_dict(integration_data)
        return None
    
    def get_integration_by_provider(self, provider_code: str) -> Optional[ShippingIntegration]:
        """Get shipping integration by provider code."""
        integration_data = self.db.shipping_integrations.find_one({'provider_code': provider_code})
        if integration_data:
            return ShippingIntegration.from_dict(integration_data)
        return None
    
    def get_active_integrations(self) -> List[ShippingIntegration]:
        """Get all active shipping integrations."""
        integrations_data = self.db.shipping_integrations.find({'is_active': True})
        return [ShippingIntegration.from_dict(data) for data in integrations_data]
    
    def update_integration(self, integration_id: ObjectId, update_data: Dict[str, Any], 
                          user_id: ObjectId) -> bool:
        """Update shipping integration."""
        update_data['updated_at'] = datetime.utcnow()
        update_data['updated_by'] = user_id
        
        result = self.db.shipping_integrations.update_one(
            {'_id': integration_id},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    def test_integration(self, integration_id: ObjectId) -> Dict[str, Any]:
        """Test shipping integration connectivity."""
        integration = self.get_integration(integration_id)
        if not integration:
            return {'success': False, 'error': 'Integration not found'}
        
        try:
            # Test API connectivity
            test_result = self._test_api_connection(integration)
            
            if test_result['success']:
                # Test rate calculation if enabled
                if integration.rate_calculation_enabled:
                    rate_test = self._test_rate_calculation(integration)
                    test_result['rate_calculation'] = rate_test
                
                # Test tracking if enabled
                if integration.tracking_enabled:
                    tracking_test = self._test_tracking(integration)
                    test_result['tracking'] = tracking_test
            
            return test_result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def calculate_shipping_rates(self, integration_id: ObjectId, shipment_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate shipping rates for a shipment."""
        integration = self.get_integration(integration_id)
        if not integration or not integration.rate_calculation_enabled:
            return []
        
        try:
            return self._calculate_rates(integration, shipment_data)
        except Exception:
            return []
    
    def create_shipping_label(self, integration_id: ObjectId, order_id: ObjectId, 
                            service_code: str) -> Dict[str, Any]:
        """Create shipping label for an order."""
        integration = self.get_integration(integration_id)
        if not integration:
            return {'success': False, 'error': 'Integration not found'}
        
        # Get order details
        order_data = self.db.orders.find_one({'_id': order_id})
        if not order_data:
            return {'success': False, 'error': 'Order not found'}
        
        try:
            label_result = self._create_label(integration, order_data, service_code)
            
            if label_result['success']:
                # Update order with tracking information
                self.db.orders.update_one(
                    {'_id': order_id},
                    {
                        '$set': {
                            'tracking_number': label_result['tracking_number'],
                            'carrier': integration.provider_name,
                            'shipping_status': ShippingStatus.LABEL_CREATED.value,
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
            
            return label_result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def track_shipment(self, integration_id: ObjectId, tracking_number: str) -> Dict[str, Any]:
        """Track a shipment using the shipping provider's API."""
        integration = self.get_integration(integration_id)
        if not integration or not integration.tracking_enabled:
            return {'success': False, 'error': 'Tracking not available'}
        
        try:
            return self._track_shipment(integration, tracking_number)
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_tracking_status(self, order_id: ObjectId, tracking_data: Dict[str, Any]) -> bool:
        """Update order tracking status based on carrier data."""
        try:
            status_mapping = {
                'in_transit': ShippingStatus.IN_TRANSIT,
                'out_for_delivery': ShippingStatus.OUT_FOR_DELIVERY,
                'delivered': ShippingStatus.DELIVERED,
                'exception': ShippingStatus.EXCEPTION,
                'returned': ShippingStatus.RETURNED
            }
            
            carrier_status = tracking_data.get('status', '').lower()
            shipping_status = status_mapping.get(carrier_status, ShippingStatus.IN_TRANSIT)
            
            update_data = {
                'shipping_status': shipping_status.value,
                'updated_at': datetime.utcnow()
            }
            
            # Add delivery date if delivered
            if shipping_status == ShippingStatus.DELIVERED:
                update_data['delivered_date'] = tracking_data.get('delivered_date', datetime.utcnow())
            
            result = self.db.orders.update_one(
                {'_id': order_id},
                {'$set': update_data}
            )
            
            return result.modified_count > 0
            
        except Exception:
            return False
    
    def get_supported_services(self, integration_id: ObjectId) -> List[Dict[str, Any]]:
        """Get supported shipping services for an integration."""
        integration = self.get_integration(integration_id)
        if not integration:
            return []
        
        try:
            return self._get_services(integration)
        except Exception:
            return []
    
    def _test_api_connection(self, integration: ShippingIntegration) -> Dict[str, Any]:
        """Test API connection to shipping provider."""
        # Simulate API connection test
        # In real implementation, this would make actual API calls
        return {
            'success': True,
            'provider': integration.provider_name,
            'response_time': 150,  # ms
            'message': 'Connection successful'
        }
    
    def _test_rate_calculation(self, integration: ShippingIntegration) -> Dict[str, Any]:
        """Test rate calculation functionality."""
        # Simulate rate calculation test
        test_shipment = {
            'origin': {'zip': '10001', 'country': 'US'},
            'destination': {'zip': '90210', 'country': 'US'},
            'packages': [{'weight': 1.0, 'length': 10, 'width': 8, 'height': 6}]
        }
        
        try:
            rates = self._calculate_rates(integration, test_shipment)
            return {
                'success': len(rates) > 0,
                'rates_found': len(rates),
                'sample_rate': rates[0] if rates else None
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _test_tracking(self, integration: ShippingIntegration) -> Dict[str, Any]:
        """Test tracking functionality."""
        # Simulate tracking test with a test tracking number
        return {
            'success': True,
            'message': 'Tracking API accessible'
        }
    
    def _calculate_rates(self, integration: ShippingIntegration, shipment_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate shipping rates using provider API."""
        # Simulate rate calculation
        # In real implementation, this would call the actual shipping API
        base_rates = {
            'ground': 8.99,
            'express': 24.99,
            'overnight': 49.99
        }
        
        rates = []
        for service in integration.supported_services:
            if service.lower() in base_rates:
                rates.append({
                    'service_code': service,
                    'service_name': service.title(),
                    'rate': base_rates[service.lower()],
                    'currency': 'USD',
                    'delivery_days': 3 if service == 'ground' else 1,
                    'guaranteed': service != 'ground'
                })
        
        return rates
    
    def _create_label(self, integration: ShippingIntegration, order_data: Dict[str, Any], 
                     service_code: str) -> Dict[str, Any]:
        """Create shipping label using provider API."""
        # Simulate label creation
        # In real implementation, this would call the actual shipping API
        tracking_number = f"{integration.provider_code.upper()}{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        return {
            'success': True,
            'tracking_number': tracking_number,
            'label_url': f"https://api.{integration.provider_code}.com/labels/{tracking_number}.pdf",
            'service_used': service_code,
            'cost': 12.99
        }
    
    def _track_shipment(self, integration: ShippingIntegration, tracking_number: str) -> Dict[str, Any]:
        """Track shipment using provider API."""
        # Simulate tracking response
        # In real implementation, this would call the actual tracking API
        return {
            'success': True,
            'tracking_number': tracking_number,
            'status': 'in_transit',
            'status_description': 'Package is in transit',
            'estimated_delivery': datetime.utcnow().strftime('%Y-%m-%d'),
            'tracking_events': [
                {
                    'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'picked_up',
                    'description': 'Package picked up',
                    'location': 'Origin facility'
                },
                {
                    'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'in_transit',
                    'description': 'Package in transit',
                    'location': 'Sorting facility'
                }
            ]
        }
    
    def _get_services(self, integration: ShippingIntegration) -> List[Dict[str, Any]]:
        """Get available services from provider."""
        # Return configured services
        services = []
        for service_code in integration.supported_services:
            services.append({
                'code': service_code,
                'name': service_code.replace('_', ' ').title(),
                'description': f"{integration.provider_name} {service_code.replace('_', ' ').title()} service"
            })
        
        return services