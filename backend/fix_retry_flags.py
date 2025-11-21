import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from orders.models import CallHistory
from datetime import datetime, time as dt_time

print("=" * 70)
print("FIX RETRY FLAGS FOR EXISTING CALLS")
print("=" * 70)

# Get today's calls
today_start = datetime.combine(datetime.now().date(), dt_time.min)
today_end = datetime.combine(datetime.now().date(), dt_time.max)

all_calls = CallHistory.objects.filter(created_at__range=(today_start, today_end))
print(f"\nTotal calls today: {all_calls.count()}")

updated_count = 0
already_set_count = 0

for call in all_calls:
    print(f"\n{'='*70}")
    print(f"Call ID: {call.call_id}")
    print(f"AWB: {call.awb} | Customer: {call.customer_name}")
    print(f"Status: {call.status}")
    print(f"Ended Reason: {call.ended_reason}")
    print(f"BEFORE: is_successful={call.is_successful}, needs_retry={call.needs_retry}")

    # Call the update_retry_status method
    old_is_successful = call.is_successful
    old_needs_retry = call.needs_retry

    call.update_retry_status()
    call.save()

    print(f"AFTER:  is_successful={call.is_successful}, needs_retry={call.needs_retry}")

    if old_is_successful != call.is_successful or old_needs_retry != call.needs_retry:
        print("✓ UPDATED")
        updated_count += 1
    else:
        print("- No change")
        already_set_count += 1

print(f"\n{'='*70}")
print("SUMMARY:")
print(f"  Total calls: {all_calls.count()}")
print(f"  Updated: {updated_count}")
print(f"  Already correct: {already_set_count}")
print("=" * 70)

# Show retry needed calls
print("\nRETRY NEEDED CALLS:")
retry_calls = CallHistory.objects.filter(
    created_at__range=(today_start, today_end),
    needs_retry=True,
    is_successful=False
)
print(f"Total: {retry_calls.count()}")
for call in retry_calls:
    print(f"  🔁 {call.awb} | {call.ended_reason} | Retry #{call.retry_count}")
