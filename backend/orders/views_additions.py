# Additional view for bulk calling all pending OFD/Undelivered orders

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CallHistory, Order
from .vapi_service import VAPIService
from django.utils.dateparse import parse_datetime
from django.db.models import Q
from datetime import datetime, time as dt_time


class BulkCallPendingOrdersView(APIView):
    """
    API endpoint to manually trigger calls to all pending OFD/Undelivered orders
    POST request - calls all orders that haven't been called successfully today
    """

    def post(self, request):
        """Make calls to all pending orders immediately"""

        # Get today's date range
        today_start = datetime.combine(datetime.now().date(), dt_time.min)
        today_end = datetime.combine(datetime.now().date(), dt_time.max)

        # Get all OFD/Undelivered orders from database
        all_orders = Order.objects.filter(
            Q(order_type='OFD') | Q(order_type='Undelivered')
        )

        if not all_orders.exists():
            return Response({
                'status': 'error',
                'message': 'No OFD/Undelivered orders found in database',
                'total_orders': 0,
                'called': 0,
                'skipped': 0,
                'failed': 0
            }, status=status.HTTP_404_NOT_FOUND)

        # Get AWBs already called successfully today
        successfully_called_awbs = CallHistory.objects.filter(
            created_at__range=(today_start, today_end),
            is_successful=True
        ).values_list('awb', flat=True).distinct()

        # Get all AWBs called today (for checking if already called)
        called_today_awbs = CallHistory.objects.filter(
            created_at__range=(today_start, today_end)
        ).values_list('awb', flat=True).distinct()

        pending_orders = []
        for order in all_orders:
            # Skip if already called successfully
            if order.awb in successfully_called_awbs:
                continue

            # Add to pending list if not called today OR needs retry
            if order.awb not in called_today_awbs:
                pending_orders.append(order)

        if not pending_orders:
            return Response({
                'status': 'success',
                'message': 'All orders have been called successfully today',
                'total_orders': all_orders.count(),
                'pending_orders': 0,
                'called': 0,
                'skipped': 0,
                'failed': 0
            }, status=status.HTTP_200_OK)

        # Start calling
        called_count = 0
        skipped_count = 0
        failed_count = 0
        call_results = []

        for order in pending_orders:
            phone_number = order.customer_mobile

            if not phone_number or phone_number == 'N/A' or len(str(phone_number).strip()) < 10:
                skipped_count += 1
                call_results.append({
                    'awb': order.awb,
                    'status': 'skipped',
                    'reason': 'No valid phone number'
                })
                continue

            # Prepare order data
            order_data = {
                'awb': order.awb,
                'customer_name': order.customer_name,
                'order_type': order.order_type,
                'current_status': order.current_status,
                'customer_address': order.customer_address,
                'customer_pincode': order.customer_pincode,
                'cod_amount': order.cod_amount
            }

            # Make call using VAPI
            result = VAPIService.make_ofd_call(phone_number, order_data)

            if "error" in result:
                failed_count += 1
                call_results.append({
                    'awb': order.awb,
                    'status': 'failed',
                    'reason': result.get('error')
                })
                continue

            # Save to database
            try:
                # Count previous calls today
                previous_calls = CallHistory.objects.filter(
                    awb=order.awb,
                    created_at__range=(today_start, today_end)
                ).count()

                CallHistory.objects.create(
                    call_id=result.get('id'),
                    awb=order.awb,
                    customer_name=order.customer_name,
                    customer_phone=phone_number,
                    order_type=order.order_type,
                    assistant_id=result.get('assistantId'),
                    phone_number_id=result.get('phoneNumberId'),
                    status=result.get('status'),
                    call_type=result.get('type'),
                    cost=result.get('cost', 0),
                    retry_count=previous_calls,
                    call_started_at=parse_datetime(result.get('createdAt')) if result.get('createdAt') else None,
                    vapi_response=result
                )

                called_count += 1
                call_results.append({
                    'awb': order.awb,
                    'status': 'success',
                    'call_id': result.get('id'),
                    'customer_name': order.customer_name
                })

            except Exception as e:
                failed_count += 1
                call_results.append({
                    'awb': order.awb,
                    'status': 'failed',
                    'reason': f'Database error: {str(e)}'
                })

        return Response({
            'status': 'success',
            'message': f'Bulk calling completed',
            'total_orders': all_orders.count(),
            'pending_orders': len(pending_orders),
            'called': called_count,
            'skipped': skipped_count,
            'failed': failed_count,
            'details': call_results
        }, status=status.HTTP_200_OK)
