"""
Fix Phone Numbers Script
Run this to update all orders with phone numbers from Track API

Usage: python manage.py shell < fix_phone_numbers.py
"""

import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from orders.models import Order
from orders.services import IThinkService

print("\n" + "="*70)
print("FIXING PHONE NUMBERS FOR OFD/UNDELIVERED ORDERS")
print("="*70 + "\n")

# Get all orders with N/A phone numbers
orders_with_na_phone = Order.objects.filter(
    customer_mobile__in=['N/A', '', None]
).filter(
    order_type__in=['OFD', 'Undelivered']
)

total_count = orders_with_na_phone.count()
print(f"Found {total_count} orders with N/A phone numbers\n")

if total_count == 0:
    print("✓ All orders already have phone numbers!")
    sys.exit(0)

# Collect AWBs
awbs_to_track = [order.awb for order in orders_with_na_phone]

print(f"Fetching phone numbers from Track API...")

# Fetch in batches
phone_map = {}
batch_size = 30
updated_count = 0
still_na_count = 0

for i in range(0, len(awbs_to_track), batch_size):
    batch = awbs_to_track[i:i + batch_size]
    print(f"\nBatch {i//batch_size + 1}: Fetching {len(batch)} AWBs...")

    track_result = IThinkService.track_orders(batch)

    if track_result.get('status') == 'success':
        track_data = track_result.get('data', {})

        for awb, track_info in track_data.items():
            customer_details = track_info.get('customer_details', {})
            phone = customer_details.get('customer_mobile') or customer_details.get('customer_phone')

            if phone and phone != 'N/A' and phone != '':
                phone_map[awb] = phone
                print(f"  ✓ {awb}: Found phone {phone}")
            else:
                print(f"  ✗ {awb}: No phone in Track API")

print(f"\n" + "="*70)
print(f"Updating database...")
print("="*70 + "\n")

# Update orders with phone numbers
for order in orders_with_na_phone:
    if order.awb in phone_map:
        order.customer_mobile = phone_map[order.awb]
        order.save()
        print(f"✓ Updated {order.awb}: {phone_map[order.awb]}")
        updated_count += 1
    else:
        print(f"✗ Still N/A: {order.awb} (no phone available)")
        still_na_count += 1

print(f"\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"Total orders checked: {total_count}")
print(f"Updated with phone: {updated_count}")
print(f"Still N/A: {still_na_count}")
print("="*70 + "\n")

if updated_count > 0:
    print("✓ Phone numbers updated successfully!")
    print("  Refresh the frontend to see updated data.")
else:
    print("⚠ No phone numbers found in Track API")
    print("  These orders may not have phone numbers in iThink system.")
