from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .services import IThinkService
from .vapi_service import VAPIService
from .models import CallHistory, Order
from .scheduler import auto_call_scheduler
from .demo_data import get_demo_ready_to_dispatch, get_demo_in_transit
from datetime import datetime, timedelta
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.db.models import Q


class TodayOrdersView(APIView):
    """
    API endpoint to get today's orders automatically
    GET request - no parameters needed
    """

    def get(self, request):
        result = IThinkService.get_today_orders()

        if "error" in result:
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(result, status=status.HTTP_200_OK)


class ReadyToDispatchView(APIView):
    """
    API endpoint to get Ready To Dispatch orders with progressive loading
    GET request with optional ?verified=true for filtered data
    """

    def get(self, request):
        # Get last 5 days orders only
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')

        # Check if user wants verified (filtered) data
        verified = request.GET.get('verified', 'false').lower() == 'true'

        orders_result = IThinkService.get_orders_by_date_range(start_date, end_date)

        if "error" in orders_result:
            return Response(get_demo_ready_to_dispatch(), status=status.HTTP_200_OK)

        # Order Details API returns data as dict with AWB as keys
        if orders_result.get('status') != 'success' or 'data' not in orders_result:
            return Response(get_demo_ready_to_dispatch(), status=status.HTTP_200_OK)

        orders_data = orders_result['data']

        # Collect only Manifested orders (not all forward orders)
        manifested_orders = []

        for awb, order in orders_data.items():
            # Get order date and check if within last 5 days
            order_date_str = order.get('order_date', '')
            if order_date_str:
                try:
                    order_date = datetime.strptime(order_date_str[:10], '%Y-%m-%d').date()
                    days_old = (datetime.now().date() - order_date).days

                    # Skip if older than 5 days
                    if days_old > 5:
                        continue
                except ValueError as e:
                    print(f"Date parsing error for AWB {awb}: {e}")
                    continue

            # Only include forward orders (exclude RTO, reverse, etc.)
            if order.get('pickup_type') == 'forward':
                manifested_orders.append({
                    'awb': awb,
                    'tracking_url': f'https://www.ithinklogistics.co.in/postship/tracking/{awb}',
                    'status': 'Manifested',
                    'customer_name': order.get('customer_name', 'N/A'),
                    'customer_mobile': order.get('customer_phone', 'N/A'),
                    'customer_address': order.get('customer_address', 'N/A'),
                    'customer_pincode': order.get('customer_pincode', 'N/A'),
                    'order_date': order.get('order_date', 'N/A'),
                    'weight': order.get('phy_weight', 'N/A'),
                    'cod_amount': order.get('total_amount', 'N/A'),
                    'last_scan': {}
                })

        # Track orders to filter only Manifested status
        if verified and manifested_orders:
            manifested_only = []
            batch_size = 30  # Increased from 10 to 30 for fewer API calls

            for i in range(0, len(manifested_orders), batch_size):
                batch = manifested_orders[i:i + batch_size]
                awb_numbers = [order['awb'] for order in batch]

                track_result = IThinkService.track_orders(awb_numbers)

                if track_result.get('status') == 'success' and 'data' in track_result:
                    tracking_data = track_result['data']

                    for order in batch:
                        awb = order['awb']
                        if awb in tracking_data:
                            track_info = tracking_data[awb]
                            current_status = track_info.get('current_status', '').lower()

                            # Debug: Print actual status from tracking API
                            print(f"AWB: {awb} | Status: {track_info.get('current_status')}")

                            # Only include if status is strictly "manifested" - not in transit, not out for delivery, not delivered
                            # Status should only contain "manifest" keyword, nothing else like "transit", "delivery", "pickup", etc.
                            is_manifested = (
                                'manifest' in current_status and
                                'transit' not in current_status and
                                'delivery' not in current_status and
                                'delivered' not in current_status and
                                'pickup' not in current_status and
                                'ofd' not in current_status and
                                'rto' not in current_status
                            )

                            if is_manifested:
                                order['current_status'] = track_info.get('current_status')
                                order['last_scan'] = track_info.get('last_scan_details', {})
                                manifested_only.append(order)
                            else:
                                print(f"  [X] Rejected - is_manifested = False")

            result = {
                'count': len(manifested_only),
                'orders': manifested_only,
                'verified': True
            }
        else:
            result = {
                'count': len(manifested_orders),
                'orders': manifested_orders,
                'verified': False
            }

        # If no orders, show demo data
        if result['count'] == 0:
            return Response(get_demo_ready_to_dispatch(), status=status.HTTP_200_OK)

        return Response(result, status=status.HTTP_200_OK)


class InTransitView(APIView):
    """
    API endpoint to get In Transit orders with progressive loading
    GET request with optional ?verified=true for filtered data
    """

    def get(self, request):
        # Get last 10 days orders
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        today = datetime.now().date()

        # Check if user wants verified (filtered) data
        verified = request.GET.get('verified', 'false').lower() == 'true'

        orders_result = IThinkService.get_orders_by_date_range(start_date, end_date)

        if "error" in orders_result:
            return Response(get_demo_in_transit(), status=status.HTTP_200_OK)

        # Order Details API returns data as dict with AWB as keys
        if orders_result.get('status') != 'success' or 'data' not in orders_result:
            return Response(get_demo_in_transit(), status=status.HTTP_200_OK)

        orders_data = orders_result['data']

        # Process all orders and show them as "In Transit"
        transit_orders = []

        for awb, order in orders_data.items():  # Process all orders
            # Calculate estimated delivery
            is_delayed = False
            estimated_delivery = 'N/A'

            # Try to parse awb_created_date as estimated delivery (assume 3 days)
            if order.get('awb_created_date'):
                try:
                    created = datetime.strptime(order['awb_created_date'][:10], '%Y-%m-%d')
                    estimated = created + timedelta(days=3)
                    estimated_delivery = estimated.strftime('%Y-%m-%d')
                    if estimated.date() < today:
                        is_delayed = True
                except ValueError:
                    pass

            transit_orders.append({
                'awb': awb,
                'tracking_url': f'https://www.ithinklogistics.co.in/postship/tracking/{awb}',
                'status': 'In Transit',
                'customer_name': order.get('customer_name', 'N/A'),
                'customer_mobile': order.get('customer_phone', 'N/A'),
                'customer_address': order.get('customer_address', 'N/A'),
                'customer_pincode': order.get('customer_pincode', 'N/A'),
                'order_date': order.get('order_date', 'N/A'),
                'estimated_delivery_date': estimated_delivery,
                'is_delayed': is_delayed,
                'weight': order.get('phy_weight', 'N/A'),
                'cod_amount': order.get('total_amount', 'N/A'),
                'last_scan': {},
                'scan_history': []
            })

        # If verified=false, return quick unfiltered data
        if not verified:
            # Only show delayed orders (but not verified for delivery status yet)
            delayed_orders = [order for order in transit_orders if order.get('is_delayed', False)]
            result = {
                'count': len(delayed_orders),
                'delayed_count': len(delayed_orders),
                'orders': delayed_orders,  # Return all orders
                'verified': False
            }
            return Response(result, status=status.HTTP_200_OK)

        # If verified=true, filter out delivered orders using Track API
        undelivered_orders = IThinkService.filter_undelivered_orders(transit_orders, batch_size=30)

        # Only keep delayed orders (estimated delivery passed but not delivered)
        delayed_undelivered = [
            order for order in undelivered_orders
            if order.get('is_delayed', False)
        ]

        result = {
            'count': len(delayed_undelivered),
            'delayed_count': len(delayed_undelivered),
            'orders': delayed_undelivered,  # Return all orders
            'verified': True
        }

        # If no delayed undelivered orders, show demo data
        if result['count'] == 0:
            return Response(get_demo_in_transit(), status=status.HTTP_200_OK)

        return Response(result, status=status.HTTP_200_OK)


class OFDOrdersView(APIView):
    """
    API endpoint to get Out For Delivery (OFD) and Undelivered orders
    GET request - automatically fetches last 10 days orders
    """

    def get(self, request):
        # OPTION 1: Check if user wants to bypass cache with ?refresh=true
        bypass_cache = request.GET.get('refresh', 'false').lower() == 'true'

        # Check cache first (30 minutes cache - increased from 5)
        cache_key = 'ofd_orders_data'

        if not bypass_cache:
            cached_data = cache.get(cache_key)
            if cached_data:
                print("[OFD] Returning cached data")
                return Response(cached_data, status=status.HTTP_200_OK)

        print(f"[OFD] {'Cache bypassed - ' if bypass_cache else ''}Fetching fresh data from database...")

        # STEP 1: First, try to get from DATABASE (saved by scheduler)
        db_orders = Order.objects.filter(Q(order_type='OFD') | Q(order_type='Undelivered'))

        if db_orders.exists():
            print(f"[OFD] Found {db_orders.count()} orders in database")
            # Use database orders (already filtered and saved by scheduler)
            ofd_undelivered_orders = []
            ofd_count = 0
            undelivered_count = 0

            for db_order in db_orders:
                order_dict = {
                    'awb': db_order.awb,
                    'customer_name': db_order.customer_name,
                    'customer_mobile': db_order.customer_mobile,
                    'customer_address': db_order.customer_address,
                    'customer_pincode': db_order.customer_pincode,
                    'cod_amount': db_order.cod_amount,
                    'weight': db_order.weight,
                    'order_date': db_order.order_date,
                    'tracking_url': db_order.tracking_url,
                    'current_status': db_order.current_status,
                    'order_type': db_order.order_type,
                    'last_scan': db_order.last_scan or {}
                }

                ofd_undelivered_orders.append(order_dict)

                if db_order.order_type == 'OFD':
                    ofd_count += 1
                else:
                    undelivered_count += 1

            # Add call history (keep existing logic)
            all_awbs = [order['awb'] for order in ofd_undelivered_orders]
            all_call_histories = CallHistory.objects.filter(awb__in=all_awbs).order_by('awb', '-created_at')

            # Group call histories by AWB
            call_history_map = {}
            for call in all_call_histories:
                if call.awb not in call_history_map:
                    call_history_map[call.awb] = {'latest': call, 'count': 0}
                call_history_map[call.awb]['count'] += 1

            # Add call history for each order
            for order in ofd_undelivered_orders:
                awb = order['awb']
                call_data = call_history_map.get(awb)
                call_history = call_data['latest'] if call_data else None
                call_count = call_data['count'] if call_data else 0

                if call_history:
                    # Extract data from VAPI response
                    success_evaluation = None
                    recording_url = None
                    transcript = None
                    summary = None

                    if call_history.vapi_response and isinstance(call_history.vapi_response, dict):
                        vapi_resp = call_history.vapi_response

                        # Extract success evaluation
                        analysis = vapi_resp.get('analysis', {})
                        if analysis and isinstance(analysis, dict):
                            success_evaluation = analysis.get('successEvaluation')
                            summary = analysis.get('summary')

                        # Extract recording URL
                        recording_url = (
                            vapi_resp.get('recordingUrl') or
                            vapi_resp.get('stereoRecordingUrl') or
                            vapi_resp.get('artifact', {}).get('recordingUrl') or
                            vapi_resp.get('artifact', {}).get('stereoRecordingUrl') or
                            vapi_resp.get('artifact', {}).get('recording', {}).get('combinedUrl')
                        )

                        # Extract transcript
                        transcript = (
                            vapi_resp.get('transcript') or
                            vapi_resp.get('artifact', {}).get('transcript')
                        )

                    # Format last call time
                    from django.utils.timezone import localtime
                    last_call_time = localtime(call_history.created_at).strftime('%b %d, %I:%M %p') if call_history.created_at else None

                    # Convert success_evaluation to pass/fail format
                    success_eval_formatted = None
                    if success_evaluation is not None:
                        eval_str = str(success_evaluation).lower()
                        if eval_str == 'true':
                            success_eval_formatted = 'pass'
                        elif eval_str == 'false':
                            success_eval_formatted = 'fail'
                        else:
                            success_eval_formatted = eval_str

                    order['call_history'] = {
                        'has_been_called': True,
                        'call_count': call_count,
                        'last_call_time': last_call_time,
                        'call_id': call_history.call_id,
                        'status': call_history.status,
                        'duration': call_history.duration,
                        'cost': call_history.cost,
                        'ended_reason': call_history.ended_reason,
                        'success_evaluation': success_eval_formatted,
                        'recording_url': recording_url,
                        'transcript': transcript,
                        'summary': summary,
                        'call_started_at': call_history.call_started_at,
                        'call_ended_at': call_history.call_ended_at,
                        'retry_count': call_history.retry_count,
                        'is_successful': call_history.is_successful,
                        'needs_retry': call_history.needs_retry,
                        'created_at': call_history.created_at
                    }
                else:
                    order['call_history'] = {
                        'has_been_called': False,
                        'call_count': 0,
                        'last_call_time': None,
                        'call_id': None,
                        'status': None,
                        'duration': None,
                        'cost': 0.0,
                        'ended_reason': None,
                        'success_evaluation': None,
                        'recording_url': None,
                        'transcript': None,
                        'summary': None,
                        'call_started_at': None,
                        'call_ended_at': None,
                        'retry_count': 0,
                        'is_successful': False,
                        'needs_retry': False,
                        'created_at': None
                    }

            result = {
                'total_count': len(ofd_undelivered_orders),
                'ofd_count': ofd_count,
                'undelivered_count': undelivered_count,
                'orders': ofd_undelivered_orders,
                'source': 'database'  # Indicate data source
            }

            # Cache for 30 minutes
            cache.set(cache_key, result, 1800)
            print(f"[OFD] Returning {len(ofd_undelivered_orders)} orders from database (cached)")

            return Response(result, status=status.HTTP_200_OK)

        # STEP 2: If database is empty, fall back to API (old logic)
        print(f"[OFD] Database empty - fetching from iThink API...")

        # Get last 10 days orders
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

        print(f"[OFD] Fetching orders from {start_date} to {end_date}")
        orders_result = IThinkService.get_orders_by_date_range(start_date, end_date)

        if "error" in orders_result:
            error_msg = orders_result.get('error')
            print(f"[OFD ERROR] iThink API Error: {error_msg}")
            return Response({
                'error': f'Failed to fetch orders from iThink API: {error_msg}',
                'total_count': 0,
                'ofd_count': 0,
                'undelivered_count': 0,
                'orders': []


            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if orders_result.get('status') != 'success' or 'data' not in orders_result:
            print(f"[OFD ERROR] Invalid response structure: {orders_result}")
            return Response({
                'error': 'Invalid response from iThink API',
                'total_count': 0,
                'ofd_count': 0,
                'undelivered_count': 0,
                'orders': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        orders_data = orders_result['data']
        print(f"[OFD] Found {len(orders_data)} total orders in date range")

        # Collect all AWBs
        all_orders = []
        for awb, order in orders_data.items():
            all_orders.append({
                'awb': awb,
                'customer_name': order.get('customer_name', 'N/A'),
                'customer_mobile': order.get('customer_phone', 'N/A'),
                'customer_address': order.get('customer_address', 'N/A'),
                'customer_pincode': order.get('customer_pincode', 'N/A'),
                'cod_amount': order.get('total_amount', 'N/A'),
                'weight': order.get('phy_weight', 'N/A'),
                'order_date': order.get('order_date', 'N/A'),
                'tracking_url': f'https://www.ithinklogistics.co.in/postship/tracking/{awb}'
            })

        # Track orders in batches to get OFD and Undelivered status
        ofd_undelivered_orders = []
        ofd_count = 0
        undelivered_count = 0
        batch_size = 25  # Increased from 10 to 25 for fewer API calls

        print(f"[OFD] Starting to track {len(all_orders)} orders in batches of {batch_size}")

        for i in range(0, len(all_orders), batch_size):
            batch = all_orders[i:i + batch_size]
            awb_numbers = [order['awb'] for order in batch]

            print(f"[OFD] Tracking batch {i//batch_size + 1}: {len(awb_numbers)} AWBs")
            track_result = IThinkService.track_orders(awb_numbers)

            if track_result.get('status') == 'success' and 'data' in track_result:
                tracking_data = track_result['data']
                print(f"[OFD] Batch {i//batch_size + 1} tracking successful, got {len(tracking_data)} results")

                for order in batch:
                    awb = order['awb']
                    if awb in tracking_data:
                        track_info = tracking_data[awb]
                        current_status = track_info.get('current_status', '').lower()

                        # Skip RTO orders
                        if 'rto' in current_status:
                            print(f"[OFD] Skipping RTO order: {awb}")
                            continue

                        # Check if OFD or Undelivered (but not RTO)
                        if 'out for delivery' in current_status:
                            order['current_status'] = track_info.get('current_status')
                            order['last_scan'] = track_info.get('last_scan_details', {})
                            order['order_type'] = 'OFD'
                            ofd_undelivered_orders.append(order)
                            ofd_count += 1
                            print(f"[OFD] Found OFD order: {awb} - {track_info.get('current_status')}")
                        elif 'undelivered' in current_status:
                            order['current_status'] = track_info.get('current_status')
                            order['last_scan'] = track_info.get('last_scan_details', {})
                            order['order_type'] = 'Undelivered'
                            ofd_undelivered_orders.append(order)
                            undelivered_count += 1
                            print(f"[OFD] Found Undelivered order: {awb} - {track_info.get('current_status')}")
                    else:
                        print(f"[OFD] No tracking data for AWB: {awb}")
            else:
                error_msg = track_result.get('error', 'Unknown error')
                status_code = track_result.get('status_code', 'N/A')
                print(f"[OFD] Batch {i//batch_size + 1} tracking failed:")
                print(f"[OFD]   Error: {error_msg}")
                print(f"[OFD]   Status Code: {status_code}")
                print(f"[OFD]   Full Response: {track_result}")

        print(f"[OFD] Final results: Total={len(ofd_undelivered_orders)}, OFD={ofd_count}, Undelivered={undelivered_count}")

        # ✅ OPTIMIZED: Bulk save/update OFD/Undelivered orders to database
        saved_count = 0
        updated_count = 0

        # Fetch all existing orders in one query
        existing_awbs = [order['awb'] for order in ofd_undelivered_orders]
        existing_orders = {order.awb: order for order in Order.objects.filter(awb__in=existing_awbs)}

        orders_to_create = []
        orders_to_update = []

        for order in ofd_undelivered_orders:
            awb = order['awb']
            order_type = order.get('order_type', 'OFD')
            current_status = order.get('current_status', 'N/A')

            if awb in existing_orders:
                # Update existing order if status changed
                existing_order = existing_orders[awb]
                if existing_order.order_type != order_type or existing_order.current_status != current_status:
                    existing_order.order_type = order_type
                    existing_order.current_status = current_status
                    existing_order.customer_mobile = order.get('customer_mobile', existing_order.customer_mobile)
                    orders_to_update.append(existing_order)
            else:
                # Prepare new order for bulk create
                orders_to_create.append(Order(
                    awb=awb,
                    order_type=order_type,
                    customer_name=order.get('customer_name', 'N/A'),
                    customer_mobile=order.get('customer_mobile', 'N/A'),
                    customer_address=order.get('customer_address', 'N/A'),
                    customer_pincode=order.get('customer_pincode', 'N/A'),
                    cod_amount=str(order.get('cod_amount', 'N/A')),
                    weight=str(order.get('weight', 'N/A')),
                    order_date=order.get('order_date', 'N/A'),
                    tracking_url=order.get('tracking_url', ''),
                    current_status=current_status,
                    last_scan=order.get('last_scan', {})
                ))

        # Bulk create new orders
        if orders_to_create:
            Order.objects.bulk_create(orders_to_create)
            saved_count = len(orders_to_create)

        # Bulk update existing orders
        if orders_to_update:
            Order.objects.bulk_update(orders_to_update, ['order_type', 'current_status', 'customer_mobile'])
            updated_count = len(orders_to_update)

        if saved_count > 0 or updated_count > 0:
            print(f"[DB] Database sync complete: {saved_count} new, {updated_count} updated")

        # ✅ OPTIMIZED: Fetch all call histories in one query instead of per-order queries
        all_awbs = [order['awb'] for order in ofd_undelivered_orders]
        all_call_histories = CallHistory.objects.filter(awb__in=all_awbs).order_by('awb', '-created_at')

        # Group call histories by AWB
        call_history_map = {}
        for call in all_call_histories:
            if call.awb not in call_history_map:
                call_history_map[call.awb] = {'latest': call, 'count': 0}
            call_history_map[call.awb]['count'] += 1

        # Add call history for each order
        for order in ofd_undelivered_orders:
            awb = order['awb']

            call_data = call_history_map.get(awb)
            call_history = call_data['latest'] if call_data else None
            call_count = call_data['count'] if call_data else 0

            if call_history:
                # Extract data from VAPI response
                success_evaluation = None
                recording_url = None
                transcript = None
                summary = None

                if call_history.vapi_response and isinstance(call_history.vapi_response, dict):
                    vapi_resp = call_history.vapi_response

                    # Extract success evaluation
                    analysis = vapi_resp.get('analysis', {})
                    if analysis and isinstance(analysis, dict):
                        success_evaluation = analysis.get('successEvaluation')
                        summary = analysis.get('summary')

                    # Extract recording URL (multiple possible locations)
                    recording_url = (
                        vapi_resp.get('recordingUrl') or
                        vapi_resp.get('stereoRecordingUrl') or
                        vapi_resp.get('artifact', {}).get('recordingUrl') or
                        vapi_resp.get('artifact', {}).get('stereoRecordingUrl') or
                        vapi_resp.get('artifact', {}).get('recording', {}).get('combinedUrl')
                    )

                    # Extract transcript
                    transcript = (
                        vapi_resp.get('transcript') or
                        vapi_resp.get('artifact', {}).get('transcript')
                    )

                # Format last call time
                from django.utils.timezone import localtime
                last_call_time = localtime(call_history.created_at).strftime('%b %d, %I:%M %p') if call_history.created_at else None

                # Convert success_evaluation to pass/fail format
                success_eval_formatted = None
                if success_evaluation is not None:
                    eval_str = str(success_evaluation).lower()
                    if eval_str == 'true':
                        success_eval_formatted = 'pass'
                    elif eval_str == 'false':
                        success_eval_formatted = 'fail'
                    else:
                        success_eval_formatted = eval_str

                order['call_history'] = {
                    'has_been_called': True,
                    'call_count': call_count,
                    'last_call_time': last_call_time,
                    'call_id': call_history.call_id,
                    'status': call_history.status,
                    'duration': call_history.duration,
                    'cost': call_history.cost,
                    'ended_reason': call_history.ended_reason,
                    'success_evaluation': success_eval_formatted,
                    'recording_url': recording_url,
                    'transcript': transcript,
                    'summary': summary,
                    'call_started_at': call_history.call_started_at,
                    'call_ended_at': call_history.call_ended_at,
                    'retry_count': call_history.retry_count,
                    'is_successful': call_history.is_successful,
                    'needs_retry': call_history.needs_retry,
                    'created_at': call_history.created_at
                }
            else:
                order['call_history'] = {
                    'has_been_called': False,
                    'call_count': 0,
                    'last_call_time': None,
                    'call_id': None,
                    'status': None,
                    'duration': None,
                    'cost': 0.0,
                    'ended_reason': None,
                    'success_evaluation': None,
                    'recording_url': None,
                    'transcript': None,
                    'summary': None,
                    'call_started_at': None,
                    'call_ended_at': None,
                    'retry_count': 0,
                    'is_successful': False,
                    'needs_retry': False,
                    'created_at': None
                }

        result = {
            'total_count': len(ofd_undelivered_orders),
            'ofd_count': ofd_count,
            'undelivered_count': undelivered_count,
            'orders': ofd_undelivered_orders
        }

        # Cache for 30 minutes (1800 seconds) - increased from 5 minutes
        cache.set(cache_key, result, 1800)
        print(f"[OFD] Cached data for 30 minutes")

        return Response(result, status=status.HTTP_200_OK)


class TrackOrderView(APIView):
    """
    Generic order tracking endpoint
    POST request with AWB numbers
    """

    def post(self, request):
        awb_numbers = request.data.get('awb_numbers', [])

        if not awb_numbers:
            return Response(
                {'error': 'awb_numbers field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = IThinkService.track_orders(awb_numbers)

        if "error" in result:
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(result, status=status.HTTP_200_OK)


class MakeCallView(APIView):
    """
    API endpoint to make VAPI call to customer
    POST request with phone number and order data
    """

    def post(self, request):
        phone_number = request.data.get('phone_number')
        order_data = request.data.get('order_data', {})

        if not phone_number:
            return Response(
                {'error': 'phone_number field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate phone number
        if not phone_number or len(str(phone_number).strip()) < 10:
            return Response(
                {'error': 'Invalid phone number. Must be at least 10 digits'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Make call using VAPI service
        result = VAPIService.make_ofd_call(phone_number, order_data)

        if "error" in result:
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save call history to database
        try:
            call_history = CallHistory.objects.create(
                call_id=result.get('id'),
                awb=order_data.get('awb', 'N/A'),
                customer_name=order_data.get('customer_name', 'N/A'),
                customer_phone=phone_number,
                order_type=order_data.get('order_type', 'OFD'),
                assistant_id=result.get('assistantId'),
                phone_number_id=result.get('phoneNumberId'),
                status=result.get('status'),
                call_type=result.get('type'),
                cost=result.get('cost', 0),
                call_started_at=parse_datetime(result.get('createdAt')) if result.get('createdAt') else None,
                vapi_response=result
            )
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error saving call history: {str(e)}")

        return Response(result, status=status.HTTP_200_OK)


class CallHistoryView(APIView):
    """
    API endpoint to get call history
    GET request - returns all call history
    """

    def get(self, request):
        # Check cache first (cache for 2 minutes - increased from 30 seconds)
        cache_key = 'call_history_data'
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        # Delete old call history (older than today) - keep only today's calls
        from datetime import datetime, time
        today_start = datetime.combine(datetime.now().date(), time.min)

        # Delete all calls before today
        deleted_count = CallHistory.objects.filter(created_at__lt=today_start).delete()[0]
        if deleted_count > 0:
            print(f"Deleted {deleted_count} old call history records")

        # Get today's call history ordered by most recent first
        today_end = datetime.combine(datetime.now().date(), time.max)
        call_history = CallHistory.objects.filter(
            created_at__range=(today_start, today_end)
        ).order_by('-created_at')

        history_data = []
        for call in call_history:
            # Extract success evaluation from VAPI response
            success_evaluation = None
            if call.vapi_response and isinstance(call.vapi_response, dict):
                analysis = call.vapi_response.get('analysis', {})
                if analysis and isinstance(analysis, dict):
                    success_evaluation = analysis.get('successEvaluation')

            history_data.append({
                'id': call.id,
                'call_id': call.call_id,
                'awb': call.awb,
                'customer_name': call.customer_name,
                'customer_phone': call.customer_phone,
                'order_type': call.order_type,
                'assistant_id': call.assistant_id,
                'phone_number_id': call.phone_number_id,
                'status': call.status,
                'call_type': call.call_type,
                'duration': call.duration,
                'cost': call.cost,
                'ended_reason': call.ended_reason,
                'success_evaluation': success_evaluation,
                'created_at': call.created_at,
                'updated_at': call.updated_at,
                'call_started_at': call.call_started_at,
                'call_ended_at': call.call_ended_at,
            })

        response_data = {
            'count': len(history_data),
            'calls': history_data
        }

        # Cache for 2 minutes (120 seconds) - increased from 30 seconds
        cache.set(cache_key, response_data, 120)

        return Response(response_data, status=status.HTTP_200_OK)


class SchedulerControlView(APIView):
    """
    API endpoint to control auto call scheduler
    """

    def post(self, request):
        """Start/Stop scheduler or trigger manual run"""
        action = request.data.get('action')  # 'start', 'stop', 'run_now'
        scheduled_time = request.data.get('time')  # Format: "HH:MM"

        if action == 'start':
            if not scheduled_time:
                return Response(
                    {'error': 'time field is required for start action'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            auto_call_scheduler.start(scheduled_time)
            return Response({
                'message': f'Scheduler started. Calls will be made daily at {scheduled_time}',
                'status': auto_call_scheduler.get_status()
            }, status=status.HTTP_200_OK)

        elif action == 'stop':
            auto_call_scheduler.stop()
            return Response({
                'message': 'Scheduler stopped',
                'status': auto_call_scheduler.get_status()
            }, status=status.HTTP_200_OK)

        elif action == 'run_now':
            # Run immediately
            auto_call_scheduler.make_calls_to_all_orders()
            return Response({
                'message': 'Manual call run completed',
                'status': auto_call_scheduler.get_status()
            }, status=status.HTTP_200_OK)

        else:
            return Response(
                {'error': 'Invalid action. Use: start, stop, or run_now'},
                status=status.HTTP_400_BAD_REQUEST
            )

    def get(self, request):
        """Get scheduler status"""
        scheduler_status = auto_call_scheduler.get_status()
        return Response(scheduler_status, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class VAPIWebhookView(APIView):
    """
    VAPI Webhook endpoint to receive call status updates
    This endpoint is called by VAPI when call status changes
    """
    permission_classes = [AllowAny]  # Allow VAPI to call without auth

    def post(self, request):
        """Handle VAPI webhook events"""
        try:
            webhook_data = request.data
            message_type = webhook_data.get('message', {}).get('type')

            # Handle call status update
            if message_type == 'status-update':
                call_data = webhook_data.get('message', {}).get('call', {})
                call_id = call_data.get('id')

                if not call_id:
                    return Response({'status': 'ok'}, status=status.HTTP_200_OK)

                # Find and update call history
                try:
                    call_history = CallHistory.objects.get(call_id=call_id)

                    # Update call details
                    call_history.status = call_data.get('status')
                    call_history.duration = call_data.get('duration')
                    call_history.cost = call_data.get('cost', 0)
                    call_history.ended_reason = call_data.get('endedReason')

                    # Parse timestamps
                    if call_data.get('startedAt'):
                        call_history.call_started_at = parse_datetime(call_data.get('startedAt'))
                    if call_data.get('endedAt'):
                        call_history.call_ended_at = parse_datetime(call_data.get('endedAt'))

                    # Update full VAPI response
                    call_history.vapi_response = call_data

                    call_history.save()

                    print(f"Updated call history for call_id: {call_id}, status: {call_data.get('status')}")

                except CallHistory.DoesNotExist:
                    print(f"Call history not found for call_id: {call_id}")

            # Handle end-of-call-report (contains analysis)
            elif message_type == 'end-of-call-report':
                call_data = webhook_data.get('message', {})
                call_id = call_data.get('call', {}).get('id')

                if not call_id:
                    return Response({'status': 'ok'}, status=status.HTTP_200_OK)

                # Find and update call history with analysis data
                try:
                    call_history = CallHistory.objects.get(call_id=call_id)

                    # Update with full call data including analysis
                    full_call_data = call_data.get('call', {})
                    call_history.status = full_call_data.get('status', call_history.status)
                    call_history.duration = full_call_data.get('duration', call_history.duration)
                    call_history.cost = full_call_data.get('cost', call_history.cost)
                    call_history.ended_reason = full_call_data.get('endedReason', call_history.ended_reason)

                    # Parse timestamps
                    if full_call_data.get('startedAt'):
                        call_history.call_started_at = parse_datetime(full_call_data.get('startedAt'))
                    if full_call_data.get('endedAt'):
                        call_history.call_ended_at = parse_datetime(full_call_data.get('endedAt'))

                    # Update full VAPI response with analysis
                    call_history.vapi_response = full_call_data

                    call_history.save()

                    success_eval = full_call_data.get('analysis', {}).get('successEvaluation')
                    print(f"Updated call history with analysis for call_id: {call_id}, success: {success_eval}")

                except CallHistory.DoesNotExist:
                    print(f"Call history not found for call_id: {call_id}")

            return Response({'status': 'ok'}, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Webhook error: {str(e)}")
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CleanupDeliveredView(APIView):
    """
    API endpoint to cleanup delivered/RTO orders from database
    Deletes orders with statuses: delivered, rto, cancelled, lost, damaged, returned
    """
    def post(self, request):
        try:
            # Get all OFD/Undelivered orders
            all_orders = Order.objects.filter(Q(order_type='OFD') | Q(order_type='Undelivered'))
            total_before = all_orders.count()

            # Define cleanup statuses
            cleanup_statuses = ['delivered', 'rto', 'cancelled', 'lost', 'damaged', 'returned']

            # Find and delete orders
            deleted_count = 0
            for order in all_orders:
                if order.current_status:
                    status_lower = order.current_status.lower()
                    if any(cleanup_status in status_lower for cleanup_status in cleanup_statuses):
                        order.delete()
                        deleted_count += 1

            # Count remaining orders
            remaining_orders = Order.objects.filter(Q(order_type='OFD') | Q(order_type='Undelivered'))
            kept_count = remaining_orders.count()

            return Response({
                'status': 'success',
                'deleted_count': deleted_count,
                'kept_count': kept_count,
                'message': f'Deleted {deleted_count} delivered/RTO orders, kept {kept_count} active orders'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PollCallStatusView(APIView):
    """
    API endpoint to poll call status from VAPI and update database
    Used for refreshing call details after a call is made
    """
    def post(self, request):
        """Poll call status for given call IDs"""
        call_ids = request.data.get('call_ids', [])

        if not call_ids:
            return Response({
                'error': 'call_ids field is required (array of call IDs)'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(call_ids, list):
            return Response({
                'error': 'call_ids must be an array'
            }, status=status.HTTP_400_BAD_REQUEST)

        updated_calls = []
        failed_calls = []

        for call_id in call_ids:
            try:
                # Get call details from VAPI
                call_details = VAPIService.get_call_details(call_id)

                # DEBUG: Log what VAPI returned
                print(f"[VAPI DEBUG] Call ID: {call_id}")
                print(f"[VAPI DEBUG] Status: {call_details.get('status')}")
                print(f"[VAPI DEBUG] endedReason: {call_details.get('endedReason')}")
                print(f"[VAPI DEBUG] Has error: {'error' in call_details}")

                if 'error' in call_details:
                    print(f"[VAPI ERROR] {call_details['error']}")
                    failed_calls.append({
                        'call_id': call_id,
                        'error': call_details['error']
                    })
                    continue

                # Update database
                try:
                    call_history = CallHistory.objects.get(call_id=call_id)

                    # Update fields
                    call_history.status = call_details.get('status', call_history.status)
                    call_history.duration = call_details.get('duration', call_history.duration)
                    call_history.cost = call_details.get('cost', call_history.cost)
                    call_history.ended_reason = call_details.get('endedReason', call_history.ended_reason)

                    # DEBUG: Log what we're saving
                    print(f"[DB UPDATE] Saving ended_reason: {call_history.ended_reason}")

                    # Parse timestamps
                    if call_details.get('startedAt'):
                        call_history.call_started_at = parse_datetime(call_details.get('startedAt'))
                    if call_details.get('endedAt'):
                        call_history.call_ended_at = parse_datetime(call_details.get('endedAt'))

                    # Update full VAPI response
                    call_history.vapi_response = call_details

                    # Update retry status
                    call_history.update_retry_status()

                    call_history.save()

                    # Extract success evaluation
                    success_evaluation = None
                    if call_details.get('analysis'):
                        success_evaluation = call_details['analysis'].get('successEvaluation')

                    updated_calls.append({
                        'call_id': call_id,
                        'status': call_history.status,
                        'duration': call_history.duration,
                        'cost': call_history.cost,
                        'ended_reason': call_history.ended_reason,
                        'success_evaluation': success_evaluation,
                        'is_successful': call_history.is_successful,
                        'needs_retry': call_history.needs_retry
                    })

                except CallHistory.DoesNotExist:
                    failed_calls.append({
                        'call_id': call_id,
                        'error': 'Call history not found in database'
                    })

            except Exception as e:
                failed_calls.append({
                    'call_id': call_id,
                    'error': str(e)
                })

        return Response({
            'updated_count': len(updated_calls),
            'failed_count': len(failed_calls),
            'updated_calls': updated_calls,
            'failed_calls': failed_calls
        }, status=status.HTTP_200_OK)

    def get(self, request):
        """Get call status for a single call ID via query param"""
        call_id = request.GET.get('call_id')

        if not call_id:
            return Response({
                'error': 'call_id query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get from VAPI
        call_details = VAPIService.get_call_details(call_id)

        if 'error' in call_details:
            return Response(call_details, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Get from database
        try:
            call_history = CallHistory.objects.get(call_id=call_id)

            return Response({
                'call_id': call_id,
                'vapi_data': call_details,
                'database_data': {
                    'awb': call_history.awb,
                    'customer_name': call_history.customer_name,
                    'customer_phone': call_history.customer_phone,
                    'status': call_history.status,
                    'duration': call_history.duration,
                    'cost': call_history.cost,
                    'ended_reason': call_history.ended_reason,
                    'is_successful': call_history.is_successful,
                    'needs_retry': call_history.needs_retry
                }
            }, status=status.HTTP_200_OK)

        except CallHistory.DoesNotExist:
            return Response({
                'call_id': call_id,
                'vapi_data': call_details,
                'database_data': None,
                'message': 'Call not found in local database'
            }, status=status.HTTP_200_OK)
