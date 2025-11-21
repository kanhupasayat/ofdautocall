import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from orders.models import CallHistory, Order
from datetime import datetime, time as dt_time
from django.db.models import Q

print("=" * 70)
print("PENDING CALLS TEST")
print("=" * 70)

# Get today's range
today_start = datetime.combine(datetime.now().date(), dt_time.min)
today_end = datetime.combine(datetime.now().date(), dt_time.max)

# 1. Check OFD Orders in database
ofd_orders = Order.objects.filter(Q(order_type='OFD') | Q(order_type='Undelivered'))
print(f"\n1. OFD/Undelivered Orders in Database: {ofd_orders.count()}")
for order in ofd_orders[:5]:
    print(f"   - {order.awb} | {order.customer_name} | {order.order_type}")

# 2. Check today's call history
all_calls = CallHistory.objects.filter(created_at__range=(today_start, today_end))
print(f"\n2. Today's Call History: {all_calls.count()} calls")

# 3. Check successful calls
successful_calls = CallHistory.objects.filter(
    created_at__range=(today_start, today_end),
    is_successful=True
)
print(f"\n3. Successful Calls: {successful_calls.count()}")
for call in successful_calls:
    print(f"   ✓ {call.awb} | {call.customer_name} | {call.ended_reason}")

# 4. Check retry needed calls
retry_calls = CallHistory.objects.filter(
    created_at__range=(today_start, today_end),
    needs_retry=True,
    is_successful=False,
    retry_count__lt=3
)
print(f"\n4. Retry Needed Calls: {retry_calls.count()}")
for call in retry_calls:
    print(f"   🔁 {call.awb} | {call.customer_name}")
    print(f"      Reason: {call.ended_reason} | Retry #{call.retry_count}")
    print(f"      needs_retry: {call.needs_retry} | is_successful: {call.is_successful}")

# 5. Check not called orders
called_awbs = CallHistory.objects.filter(
    created_at__range=(today_start, today_end)
).values_list('awb', flat=True).distinct()

not_called_orders = ofd_orders.exclude(awb__in=called_awbs)
print(f"\n5. Not Called Orders: {not_called_orders.count()}")
for order in not_called_orders[:5]:
    print(f"   📞 {order.awb} | {order.customer_name} | {order.order_type}")

# 6. Summary
print(f"\n{'=' * 70}")
print("SUMMARY:")
print(f"  Total OFD Orders: {ofd_orders.count()}")
print(f"  Not Called: {not_called_orders.count()}")
print(f"  Retry Needed: {retry_calls.count()}")
print(f"  Successful: {successful_calls.count()}")
print(f"  Total Pending: {not_called_orders.count() + retry_calls.count()}")
print("=" * 70)
