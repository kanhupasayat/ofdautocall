#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from orders.services import IThinkService
from datetime import datetime, timedelta

# Get last 5 days orders
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')

print(f"Fetching orders from {start_date} to {end_date}...")
orders_result = IThinkService.get_orders_by_date_range(start_date, end_date)

if orders_result.get('status') != 'success':
    print(f"Error: {orders_result}")
    sys.exit(1)

orders_data = orders_result['data']
print(f"Total orders: {len(orders_data)}")

# Get only forward orders
forward_orders = []
for awb, order in orders_data.items():
    if order.get('pickup_type') == 'forward':
        forward_orders.append(awb)

print(f"Forward orders: {len(forward_orders)}")

# Now track first 10 to see statuses (API limit is 10)
test_batch = forward_orders[:10]
print(f"\nTracking first {len(test_batch)} orders...")

track_result = IThinkService.track_orders(test_batch)

if track_result.get('status') != 'success':
    print(f"Track error: {track_result}")
    sys.exit(1)

tracking_data = track_result.get('data', {})
print(f"Received tracking data for {len(tracking_data)} orders\n")

# Analyze statuses
status_counts = {}
manifested_count = 0

for awb in test_batch:
    if awb in tracking_data:
        track_info = tracking_data[awb]
        current_status = track_info.get('current_status', 'Unknown')

        # Count statuses
        status_counts[current_status] = status_counts.get(current_status, 0) + 1

        # Check if manifested
        current_status_lower = current_status.lower()
        is_manifested = (
            'manifest' in current_status_lower and
            'transit' not in current_status_lower and
            'delivery' not in current_status_lower and
            'delivered' not in current_status_lower and
            'pickup' not in current_status_lower and
            'ofd' not in current_status_lower and
            'rto' not in current_status_lower
        )

        if is_manifested:
            manifested_count += 1
            print(f"[MANIFESTED] {awb}: {current_status}")
        else:
            print(f"[NOT MANIFESTED] {awb}: {current_status}")
    else:
        print(f"[NO DATA] {awb}: No tracking data")

print(f"\n========================================")
print(f"Status Summary:")
print(f"========================================")
for status, count in sorted(status_counts.items()):
    print(f"{status}: {count}")

print(f"\n========================================")
print(f"Manifested orders: {manifested_count} out of {len(test_batch)}")
print(f"========================================")
