import requests
from django.conf import settings
from datetime import datetime, date


class IThinkService:
    """Service to interact with iThink Logistics API"""

    @staticmethod
    def get_orders_by_date_range(start_date, end_date):
        """
        Get orders for a date range from iThink Order Details API
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        Returns:
            dict: API response data with order details
        """
        payload = {
            "data": {
                "start_date": start_date,
                "end_date": end_date,
                "access_token": settings.ITHINK_ACCESS_TOKEN,
                "secret_key": settings.ITHINK_SECRET_KEY
            }
        }

        try:
            response = requests.post(settings.ITHINK_ORDER_LIST_URL, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status_code": 500}

    @staticmethod
    def get_today_orders():
        """
        Get all orders for today's date from iThink Store Order List API
        Returns:
            dict: API response data with today's orders
        """
        today = date.today().strftime('%Y-%m-%d')

        payload = {
            "data": {
                "platform_id": settings.ITHINK_PLATFORM_ID,
                "start_date": today,
                "end_date": today,
                "access_token": settings.ITHINK_ACCESS_TOKEN,
                "secret_key": settings.ITHINK_SECRET_KEY
            }
        }

        try:
            response = requests.post(settings.ITHINK_ORDER_LIST_URL, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status_code": 500}

    @staticmethod
    def track_orders(awb_numbers):
        """
        Track orders using iThink API
        Args:
            awb_numbers: List of AWB numbers or comma-separated string
        Returns:
            dict: API response data
        """
        if isinstance(awb_numbers, list):
            awb_numbers = ','.join(awb_numbers)

        payload = {
            "data": {
                "awb_number_list": awb_numbers,
                "access_token": settings.ITHINK_ACCESS_TOKEN,
                "secret_key": settings.ITHINK_SECRET_KEY
            }
        }

        try:
            response = requests.post(settings.ITHINK_API_URL, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # HTTP error (4xx, 5xx)
            error_detail = {
                "error": f"HTTP {e.response.status_code}: {e.response.reason}",
                "status_code": e.response.status_code,
                "response_text": e.response.text[:500] if hasattr(e.response, 'text') else "No response text"
            }
            print(f"[IThink API] HTTP Error: {error_detail}")
            return error_detail
        except requests.exceptions.Timeout as e:
            error_detail = {"error": "Request timeout - API took too long to respond", "status_code": 408}
            print(f"[IThink API] Timeout Error: {error_detail}")
            return error_detail
        except requests.exceptions.ConnectionError as e:
            error_detail = {"error": f"Connection error - Could not reach API: {str(e)}", "status_code": 503}
            print(f"[IThink API] Connection Error: {error_detail}")
            return error_detail
        except requests.exceptions.RequestException as e:
            error_detail = {"error": f"Request failed: {str(e)}", "status_code": 500}
            print(f"[IThink API] General Error: {error_detail}")
            return error_detail

    @staticmethod
    def get_ready_to_dispatch_orders(awb_numbers):
        """
        Get orders that are ready to dispatch
        Returns orders with status like 'Manifested', 'Not Picked', etc.
        """
        result = IThinkService.track_orders(awb_numbers)

        if "error" in result:
            return result

        ready_to_dispatch_statuses = [
            'Manifested',
            'Not Picked',
            'REV Manifest',
            'REV Out for Pick Up'
        ]

        ready_orders = []
        if result.get('status_code') == 200 and 'data' in result:
            for awb, order_data in result['data'].items():
                if order_data.get('current_status') in ready_to_dispatch_statuses:
                    ready_orders.append({
                        'awb': awb,
                        'status': order_data.get('current_status'),
                        'customer_name': order_data.get('customer_name'),
                        'customer_mobile': order_data.get('customer_mobile'),
                        'customer_address': order_data.get('customer_address'),
                        'customer_pincode': order_data.get('customer_pincode'),
                        'order_date': order_data.get('order_date'),
                        'weight': order_data.get('weight'),
                        'cod_amount': order_data.get('cod_amount'),
                        'last_scan': order_data.get('last_scan', [{}])[0] if order_data.get('last_scan') else {}
                    })

        return {
            'count': len(ready_orders),
            'orders': ready_orders
        }

    @staticmethod
    def get_in_transit_orders(awb_numbers):
        """
        Get orders that are in transit with delivery date information
        Highlight orders where delivery date has passed
        """
        result = IThinkService.track_orders(awb_numbers)

        if "error" in result:
            return result

        in_transit_statuses = [
            'Picked Up',
            'In Transit',
            'Reached At Destination',
            'Out For Delivery',
            'REV Picked Up',
            'REV In Transit',
            'REV Out For Delivery'
        ]

        transit_orders = []
        today = date.today()

        if result.get('status_code') == 200 and 'data' in result:
            for awb, order_data in result['data'].items():
                if order_data.get('current_status') in in_transit_statuses:
                    # Get estimated delivery date
                    estimated_delivery = order_data.get('estimated_delivery_date')
                    is_delayed = False

                    if estimated_delivery:
                        try:
                            # Parse delivery date (format: YYYY-MM-DD or DD-MM-YYYY)
                            if '-' in estimated_delivery:
                                parts = estimated_delivery.split('-')
                                if len(parts[0]) == 4:  # YYYY-MM-DD
                                    delivery_date = datetime.strptime(estimated_delivery, '%Y-%m-%d').date()
                                else:  # DD-MM-YYYY
                                    delivery_date = datetime.strptime(estimated_delivery, '%d-%m-%Y').date()

                                is_delayed = delivery_date < today
                        except ValueError:
                            pass

                    transit_orders.append({
                        'awb': awb,
                        'status': order_data.get('current_status'),
                        'customer_name': order_data.get('customer_name'),
                        'customer_mobile': order_data.get('customer_mobile'),
                        'customer_address': order_data.get('customer_address'),
                        'customer_pincode': order_data.get('customer_pincode'),
                        'order_date': order_data.get('order_date'),
                        'estimated_delivery_date': estimated_delivery,
                        'is_delayed': is_delayed,
                        'weight': order_data.get('weight'),
                        'cod_amount': order_data.get('cod_amount'),
                        'last_scan': order_data.get('last_scan', [{}])[0] if order_data.get('last_scan') else {},
                        'scan_history': order_data.get('scans', [])
                    })

        return {
            'count': len(transit_orders),
            'delayed_count': sum(1 for order in transit_orders if order['is_delayed']),
            'orders': transit_orders
        }

    @staticmethod
    def filter_undelivered_orders(orders_list, batch_size=10):
        """
        Filter out delivered orders by checking their status via Track API
        Process in batches for efficiency
        Returns only undelivered orders
        """
        undelivered_orders = []

        # Process in batches
        for i in range(0, len(orders_list), batch_size):
            batch = orders_list[i:i + batch_size]
            awb_numbers = [order['awb'] for order in batch]

            # Track this batch
            track_result = IThinkService.track_orders(awb_numbers)

            if "error" in track_result or track_result.get('status') != 'success':
                # If tracking fails, include all orders in batch (safer to show than hide)
                undelivered_orders.extend(batch)
                continue

            # Get tracking data
            tracking_data = track_result.get('data', {})

            # Check each order in the batch
            for order in batch:
                awb = order['awb']
                track_info = tracking_data.get(awb, {})

                # Get current status
                current_status = track_info.get('current_status', '').lower().strip()

                # Statuses to filter out (Delivered, RTO, Lost, Damaged, Cancelled)
                # Check if status starts with rto or contains rto, or is delivered
                is_rto = 'rto' in current_status
                is_delivered = 'delivered' in current_status
                is_lost = 'lost' in current_status
                is_damaged = 'damaged' in current_status
                is_cancelled = 'cancel' in current_status
                is_destroyed = 'destroyed' in current_status or 'disposed' in current_status

                # Only include if NOT in any ignore category
                should_ignore = is_rto or is_delivered or is_lost or is_damaged or is_cancelled or is_destroyed

                if not should_ignore:
                    # Add tracking info to order
                    order['current_status'] = track_info.get('current_status', 'Unknown')

                    # Add scan history if available
                    if 'track_history' in track_info:
                        order['scan_history'] = track_info['track_history']
                        if track_info['track_history']:
                            order['last_scan'] = track_info['track_history'][0]

                    undelivered_orders.append(order)

        return undelivered_orders
