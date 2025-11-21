import os
import sys
import django
import requests

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from orders.vapi_service import VAPIService

print("=" * 70)
print("TEST CALL TO SINGLE NUMBER")
print("=" * 70)

# Test number
phone_number = "6370997812"

# Order data
order_data = {
    'awb': 'TEST123456',
    'customer_name': 'Test Customer',
    'order_type': 'OFD',
    'current_status': 'Out for delivery',
    'customer_address': 'Test Address',
    'customer_pincode': '123456',
    'cod_amount': '500'
}

print(f"\nCalling: {phone_number}")
print(f"Order: {order_data['awb']}")
print(f"Customer: {order_data['customer_name']}")
print(f"\nInitiating call...\n")

# Make call
result = VAPIService.make_ofd_call(phone_number, order_data)

if 'error' in result:
    print(f"ERROR: {result['error']}")
    if 'details' in result:
        print(f"Details: {result['details']}")
else:
    print("SUCCESS!")
    print(f"Call ID: {result.get('id')}")
    print(f"Status: {result.get('status')}")
    print(f"Type: {result.get('type')}")

    # Save to database
    from orders.models import CallHistory
    from django.utils.dateparse import parse_datetime
    from datetime import datetime, time as dt_time

    try:
        # Get retry count
        today_start = datetime.combine(datetime.now().date(), dt_time.min)
        previous_calls = CallHistory.objects.filter(
            awb=order_data.get('awb'),
            created_at__gte=today_start
        ).count()

        call_history = CallHistory.objects.create(
            call_id=result.get('id'),
            awb=order_data.get('awb'),
            customer_name=order_data.get('customer_name'),
            customer_phone=phone_number,
            order_type=order_data.get('order_type'),
            assistant_id=result.get('assistantId'),
            phone_number_id=result.get('phoneNumberId'),
            status=result.get('status'),
            call_type=result.get('type'),
            cost=result.get('cost', 0),
            ended_reason=result.get('endedReason'),
            retry_count=previous_calls,
            call_started_at=parse_datetime(result.get('createdAt')) if result.get('createdAt') else None,
            vapi_response=result
        )
        print(f"\nSaved to database!")
        print(f"Retry count: {previous_calls}")

    except Exception as e:
        print(f"\nError saving: {e}")

print("\n" + "=" * 70)
print("Check Call History page or VAPI dashboard for details")
print("VAPI Dashboard: https://dashboard.vapi.ai")
print("=" * 70)
