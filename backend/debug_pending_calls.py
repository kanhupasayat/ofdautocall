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
print("DEBUG PENDING CALLS")
print("=" * 70)

# Get today's range
today_start = datetime.combine(datetime.now().date(), dt_time.min)
today_end = datetime.combine(datetime.now().date(), dt_time.max)

# 1. All OFD Orders
all_ofd = Order.objects.filter(Q(order_type='OFD') | Q(order_type='Undelivered'))
print(f"\n1. Total OFD/Undelivered Orders in Database: {all_ofd.count()}")
for i, order in enumerate(all_ofd, 1):
    print(f"   {i}. AWB: {order.awb}")
    print(f"      Status: {order.current_status}")
    print(f"      Type: {order.order_type}")
    print(f"      Customer: {order.customer_name} | {order.customer_mobile}")

# 2. Today's Call History
print(f"\n2. Today's Call History:")
today_calls = CallHistory.objects.filter(created_at__range=(today_start, today_end))
print(f"   Total calls today: {today_calls.count()}")
for i, call in enumerate(today_calls, 1):
    print(f"   {i}. AWB: {call.awb} | Status: {call.status}")
    print(f"      Ended Reason: {call.ended_reason}")
    print(f"      is_successful: {call.is_successful}")
    print(f"      needs_retry: {call.needs_retry}")
    print(f"      retry_count: {call.retry_count}")

# 3. Successfully called AWBs
successful_awbs = CallHistory.objects.filter(
    created_at__range=(today_start, today_end),
    is_successful=True
).values_list('awb', flat=True).distinct()
print(f"\n3. Successfully Called AWBs: {len(successful_awbs)}")
for awb in successful_awbs:
    print(f"   ✓ {awb}")

# 4. All called AWBs (successful or not)
all_called_awbs = CallHistory.objects.filter(
    created_at__range=(today_start, today_end)
).values_list('awb', flat=True).distinct()
print(f"\n4. All Called AWBs (including failed): {len(all_called_awbs)}")
for awb in all_called_awbs:
    print(f"   📞 {awb}")

# 5. NOT CALLED orders
not_called_orders = all_ofd.exclude(awb__in=all_called_awbs).exclude(awb__in=successful_awbs)
print(f"\n5. NOT CALLED Orders: {not_called_orders.count()}")
for order in not_called_orders:
    print(f"   🆕 {order.awb} | {order.customer_name} | {order.order_type}")

# 6. RETRY NEEDED calls
retry_calls = CallHistory.objects.filter(
    created_at__range=(today_start, today_end),
    needs_retry=True,
    is_successful=False,
    retry_count__lt=3
).exclude(awb__in=successful_awbs)
print(f"\n6. RETRY NEEDED Calls: {retry_calls.count()}")
for call in retry_calls:
    print(f"   🔁 {call.awb} | Retry #{call.retry_count}")
    print(f"      Reason: {call.ended_reason}")
    print(f"      needs_retry: {call.needs_retry}, is_successful: {call.is_successful}")

# 7. SUMMARY
print(f"\n{'=' * 70}")
print("PENDING CALLS SUMMARY:")
print(f"  Not Called: {not_called_orders.count()}")
print(f"  Retry Needed: {retry_calls.count()}")
print(f"  TOTAL PENDING: {not_called_orders.count() + retry_calls.count()}")
print("=" * 70)

# 8. Check if needs_retry is being set correctly
print(f"\n8. Checking needs_retry flag:")
all_failed_calls = CallHistory.objects.filter(
    created_at__range=(today_start, today_end),
    is_successful=False
)
print(f"   Total failed calls: {all_failed_calls.count()}")
for call in all_failed_calls:
    print(f"   AWB: {call.awb}")
    print(f"     ended_reason: {call.ended_reason}")
    print(f"     needs_retry: {call.needs_retry}")
    print(f"     is_successful: {call.is_successful}")
    print()
