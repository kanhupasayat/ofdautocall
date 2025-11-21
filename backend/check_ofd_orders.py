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
print("CHECK OFD/UNDELIVERED ORDERS IN DATABASE")
print("=" * 70)

# Get all OFD orders
ofd_orders = Order.objects.filter(order_type='OFD')
print(f"\n1. OFD Orders: {ofd_orders.count()}")
for order in ofd_orders:
    print(f"   - {order.awb} | {order.customer_name} | Status: {order.current_status}")

# Get all Undelivered orders
undelivered_orders = Order.objects.filter(order_type='Undelivered')
print(f"\n2. Undelivered Orders: {undelivered_orders.count()}")
for order in undelivered_orders:
    print(f"   - {order.awb} | {order.customer_name} | Status: {order.current_status}")

# Get all OFD + Undelivered (combined)
all_orders = Order.objects.filter(Q(order_type='OFD') | Q(order_type='Undelivered'))
print(f"\n3. Total OFD + Undelivered: {all_orders.count()}")

# Check what order_types exist
all_order_types = Order.objects.values('order_type').distinct()
print(f"\n4. All order_types in database:")
for ot in all_order_types:
    count = Order.objects.filter(order_type=ot['order_type']).count()
    print(f"   - {ot['order_type']}: {count} orders")

# Get a sample of all orders
print(f"\n5. Sample of ALL orders in database:")
sample = Order.objects.all()[:10]
for order in sample:
    print(f"   - AWB: {order.awb}")
    print(f"     Type: {order.order_type}")
    print(f"     Status: {order.current_status}")
    print(f"     Customer: {order.customer_name}")
    print()

print("=" * 70)
