"""
Payment gateway integration services for Stripe, PayPal, and M-Pesa.
"""

import stripe
import paypalrestsdk
import requests
import base64
import json
from datetime import datetime
from flask import current_app
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StripePaymentService:
    """Stripe payment processing service."""
    
    def __init__(self):
        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
    
    def create_payment_intent(self, amount, currency='usd', metadata=None):
        """Create a Stripe payment intent."""
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Stripe uses cents
                currency=currency,
                metadata=metadata or {},
                automatic_payment_methods={'enabled': True}
            )
            return {
                'success': True,
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return {'success': False, 'error': str(e)}
    
    def confirm_payment(self, payment_intent_id):
        """Confirm a Stripe payment."""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                'success': True,
                'status': intent.status,
                'amount': intent.amount / 100,
                'currency': intent.currency
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe confirmation error: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_refund(self, payment_intent_id, amount=None):
        """Create a refund for a Stripe payment."""
        try:
            refund_data = {'payment_intent': payment_intent_id}
            if amount:
                refund_data['amount'] = int(amount * 100)
            
            refund = stripe.Refund.create(**refund_data)
            return {
                'success': True,
                'refund_id': refund.id,
                'status': refund.status,
                'amount': refund.amount / 100
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund error: {e}")
            return {'success': False, 'error': str(e)}

class PayPalPaymentService:
    """PayPal payment processing service."""
    
    def __init__(self):
        paypalrestsdk.configure({
            "mode": current_app.config.get('PAYPAL_MODE', 'sandbox'),
            "client_id": current_app.config.get('PAYPAL_CLIENT_ID'),
            "client_secret": current_app.config.get('PAYPAL_CLIENT_SECRET')
        })
    
    def create_payment(self, amount, currency='USD', return_url=None, cancel_url=None):
        """Create a PayPal payment."""
        try:
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": return_url or "http://localhost:5000/payment/paypal/success",
                    "cancel_url": cancel_url or "http://localhost:5000/payment/paypal/cancel"
                },
                "transactions": [{
                    "item_list": {
                        "items": [{
                            "name": "Order Payment",
                            "sku": "order",
                            "price": str(amount),
                            "currency": currency,
                            "quantity": 1
                        }]
                    },
                    "amount": {
                        "total": str(amount),
                        "currency": currency
                    },
                    "description": "E-commerce order payment"
                }]
            })
            
            if payment.create():
                approval_url = next(
                    (link.href for link in payment.links if link.rel == "approval_url"),
                    None
                )
                return {
                    'success': True,
                    'payment_id': payment.id,
                    'approval_url': approval_url
                }
            else:
                logger.error(f"PayPal payment creation error: {payment.error}")
                return {'success': False, 'error': payment.error}
                
        except Exception as e:
            logger.error(f"PayPal error: {e}")
            return {'success': False, 'error': str(e)}
    
    def execute_payment(self, payment_id, payer_id):
        """Execute a PayPal payment."""
        try:
            payment = paypalrestsdk.Payment.find(payment_id)
            
            if payment.execute({"payer_id": payer_id}):
                return {
                    'success': True,
                    'payment_id': payment.id,
                    'state': payment.state,
                    'amount': payment.transactions[0].amount.total
                }
            else:
                logger.error(f"PayPal execution error: {payment.error}")
                return {'success': False, 'error': payment.error}
                
        except Exception as e:
            logger.error(f"PayPal execution error: {e}")
            return {'success': False, 'error': str(e)}

class MPesaPaymentService:
    """M-Pesa payment processing service (Safaricom Kenya)."""
    
    def __init__(self):
        self.consumer_key = current_app.config.get('MPESA_CONSUMER_KEY')
        self.consumer_secret = current_app.config.get('MPESA_CONSUMER_SECRET')
        self.shortcode = current_app.config.get('MPESA_SHORTCODE')
        self.passkey = current_app.config.get('MPESA_PASSKEY')
        self.environment = current_app.config.get('MPESA_ENVIRONMENT', 'sandbox')
        
        # Set API URLs based on environment
        if self.environment == 'production':
            self.base_url = 'https://api.safaricom.co.ke'
        else:
            self.base_url = 'https://sandbox.safaricom.co.ke'
    
    def get_access_token(self):
        """Get M-Pesa access token."""
        try:
            url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
            
            # Create basic auth header
            credentials = base64.b64encode(
                f"{self.consumer_key}:{self.consumer_secret}".encode()
            ).decode()
            
            headers = {
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.json().get('access_token')
            else:
                logger.error(f"M-Pesa token error: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"M-Pesa token error: {e}")
            return None
    
    def stk_push(self, phone_number, amount, account_reference, transaction_desc, callback_url):
        """Initiate M-Pesa STK Push payment."""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return {'success': False, 'error': 'Failed to get access token'}
            
            # Generate timestamp and password
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = base64.b64encode(
                f"{self.shortcode}{self.passkey}{timestamp}".encode()
            ).decode()
            
            url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'BusinessShortCode': self.shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': int(amount),
                'PartyA': phone_number,
                'PartyB': self.shortcode,
                'PhoneNumber': phone_number,
                'CallBackURL': callback_url,
                'AccountReference': account_reference,
                'TransactionDesc': transaction_desc
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ResponseCode') == '0':
                    return {
                        'success': True,
                        'checkout_request_id': result.get('CheckoutRequestID'),
                        'merchant_request_id': result.get('MerchantRequestID'),
                        'response_description': result.get('ResponseDescription')
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('ResponseDescription', 'Unknown error')
                    }
            else:
                logger.error(f"M-Pesa STK Push error: {response.text}")
                return {'success': False, 'error': 'STK Push request failed'}
                
        except Exception as e:
            logger.error(f"M-Pesa STK Push error: {e}")
            return {'success': False, 'error': str(e)}
    
    def query_transaction_status(self, checkout_request_id):
        """Query M-Pesa transaction status."""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return {'success': False, 'error': 'Failed to get access token'}
            
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = base64.b64encode(
                f"{self.shortcode}{self.passkey}{timestamp}".encode()
            ).decode()
            
            url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'BusinessShortCode': self.shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'CheckoutRequestID': checkout_request_id
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'result_code': result.get('ResultCode'),
                    'result_desc': result.get('ResultDesc'),
                    'data': result
                }
            else:
                logger.error(f"M-Pesa query error: {response.text}")
                return {'success': False, 'error': 'Query request failed'}
                
        except Exception as e:
            logger.error(f"M-Pesa query error: {e}")
            return {'success': False, 'error': str(e)}

# Payment service factory
class PaymentServiceFactory:
    """Factory class to get payment service instances."""
    
    @staticmethod
    def get_service(payment_method):
        """Get payment service instance based on method."""
        if payment_method == 'stripe':
            return StripePaymentService()
        elif payment_method == 'paypal':
            return PayPalPaymentService()
        elif payment_method == 'mpesa':
            return MPesaPaymentService()
        else:
            raise ValueError(f"Unsupported payment method: {payment_method}")