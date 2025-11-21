import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from orders.models import Order
from django.db.models import Q

print("=" * 70)
print("CLEANUP DELIVERED/RTO ORDERS")
print("=" * 70)

# Get all OFD/Undelivered orders
all_orders = Order.objects.filter(Q(order_type='OFD') | Q(order_type='Undelivered'))
print(f"\nTotal OFD/Undelivered orders in database: {all_orders.count()}")

# List all orders with their status
print("\nCurrent orders:")
for order in all_orders:
    print(f"  {order.awb} | {order.current_status} | {order.order_type}")

# Define cleanup statuses
cleanup_statuses = ['delivered', 'rto', 'cancelled', 'lost', 'damaged', 'returned']

# Find orders to delete
to_delete = []
for order in all_orders:
    if order.current_status:
        status_lower = order.current_status.lower()
        if any(cleanup_status in status_lower for cleanup_status in cleanup_statuses):
            to_delete.append(order)

print(f"\n{'=' * 70}")
print(f"Found {len(to_delete)} orders to DELETE:")
for order in to_delete:
    print(f"  ✗ {order.awb} | {order.current_status}")

if len(to_delete) > 0:
    confirm = input(f"\nDelete {len(to_delete)} orders? (yes/no): ")
    if confirm.lower() == 'yes':
        deleted_count = 0
        for order in to_delete:
            order.delete()
            deleted_count += 1
        print(f"\n✓ Deleted {deleted_count} orders")
    else:
        print("\n✗ Deletion cancelled")
else:
    print("\n✓ No orders to delete")

# Show remaining orders
remaining = Order.objects.filter(Q(order_type='OFD') | Q(order_type='Undelivered'))
print(f"\n{'=' * 70}")
print(f"Remaining OFD/Undelivered orders: {remaining.count()}")
for order in remaining:
    print(f"  ✓ {order.awb} | {order.current_status} | {order.order_type}")
print("=" * 70)
