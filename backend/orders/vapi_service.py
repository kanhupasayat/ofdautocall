import requests
import os
from django.conf import settings


class VAPIService:
    """
    Service class for VAPI AI integration
    """

    VAPI_API_URL = "https://api.vapi.ai/call/phone"

    @staticmethod
    def make_call(phone_number, assistant_id, metadata=None):
        """
        Make a phone call using VAPI AI

        Args:
            phone_number: Phone number to call (with country code)
            assistant_id: VAPI Assistant ID
            metadata: Additional data to pass to the assistant

        Returns:
            dict: API response
        """
        # Use private key for authorization
        private_key = os.getenv('VAPI_PRIVATE_KEY')

        if not private_key:
            return {'error': 'VAPI private key not configured'}

        # Prepare phone number with country code if not present
        if not phone_number.startswith('+'):
            phone_number = '+91' + phone_number  # Default to India

        headers = {
            'Authorization': f'Bearer {private_key}',
            'Content-Type': 'application/json'
        }

        # Get phone number ID from environment
        phone_number_id = os.getenv('VAPI_PHONE_NUMBER_ID')

        payload = {
            'assistantId': assistant_id,
            'customer': {
                'number': phone_number
            },
            'phoneNumberId': phone_number_id
        }

        # Add metadata if provided
        if metadata:
            payload['assistantOverrides'] = {
                'variableValues': metadata
            }

        try:
            response = requests.post(
                VAPIService.VAPI_API_URL,
                json=payload,
                headers=headers,
                timeout=30
            )

            # Check response status
            if response.status_code != 201 and response.status_code != 200:
                return {
                    'error': f'VAPI API error: {response.status_code}',
                    'details': response.text
                }

            # Try to parse JSON response
            try:
                return response.json()
            except:
                # If JSON parsing fails, return raw text
                return {
                    'status': 'success',
                    'message': 'Call initiated',
                    'raw_response': response.text
                }

        except requests.exceptions.Timeout:
            return {'error': 'Request timeout - VAPI API took too long to respond'}
        except requests.exceptions.RequestException as e:
            return {'error': f'Request failed: {str(e)}'}
        except Exception as e:
            return {'error': f'Unexpected error: {str(e)}'}

    @staticmethod
    def make_ofd_call(phone_number, order_data):
        """
        Make a call for OFD/Undelivered order

        Args:
            phone_number: Customer phone number
            order_data: Order details dict

        Returns:
            dict: API response
        """
        assistant_id = os.getenv('VAPI_ASSISTANT_ID', 'cb33dec1-c4ac-490f-a25b-2789483a7f94')

        # Prepare metadata for the call
        metadata = {
            'awb': order_data.get('awb', 'N/A'),
            'customer_name': order_data.get('customer_name', 'Customer'),
            'order_type': order_data.get('order_type', 'OFD'),
            'current_status': order_data.get('current_status', 'Out for delivery'),
            'customer_address': order_data.get('customer_address', 'N/A'),
            'customer_pincode': order_data.get('customer_pincode', 'N/A'),
            'cod_amount': str(order_data.get('cod_amount', '0'))
        }

        return VAPIService.make_call(phone_number, assistant_id, metadata)

    @staticmethod
    def get_call_details(call_id):
        """
        Get call details from VAPI API

        Args:
            call_id: VAPI call ID

        Returns:
            dict: Call details including status, ended_reason, analysis
        """
        private_key = os.getenv('VAPI_PRIVATE_KEY')

        if not private_key:
            return {'error': 'VAPI private key not configured'}

        headers = {
            'Authorization': f'Bearer {private_key}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.get(
                f'https://api.vapi.ai/call/{call_id}',
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                return {
                    'error': f'VAPI API error: {response.status_code}',
                    'details': response.text
                }

            return response.json()

        except requests.exceptions.Timeout:
            return {'error': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            return {'error': f'Request failed: {str(e)}'}
        except Exception as e:
            return {'error': f'Unexpected error: {str(e)}'}

    @staticmethod
    def list_calls(limit=100, created_at_gt=None):
        """
        Get list of calls from VAPI API (batch fetch)

        Args:
            limit: Number of calls to fetch (max 100)
            created_at_gt: ISO timestamp to filter calls created after

        Returns:
            list: List of call objects
        """
        private_key = os.getenv('VAPI_PRIVATE_KEY')

        if not private_key:
            return {'error': 'VAPI private key not configured'}

        headers = {
            'Authorization': f'Bearer {private_key}',
            'Content-Type': 'application/json'
        }

        params = {
            'limit': min(limit, 100)  # VAPI max is 100
        }

        if created_at_gt:
            params['createdAtGt'] = created_at_gt

        try:
            response = requests.get(
                'https://api.vapi.ai/call',
                headers=headers,
                params=params,
                timeout=30
            )

            if response.status_code != 200:
                return {
                    'error': f'VAPI API error: {response.status_code}',
                    'details': response.text
                }

            return response.json()

        except requests.exceptions.Timeout:
            return {'error': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            return {'error': f'Request failed: {str(e)}'}
        except Exception as e:
            return {'error': f'Unexpected error: {str(e)}'}
