import os
import sys
import django
import requests

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

print("=" * 70)
print("FORCE SYNC OFD/UNDELIVERED ORDERS")
print("=" * 70)

# Call the OFD API endpoint to force refresh
url = "http://localhost:8000/api/orders/ofd/"

print("\nCalling OFD API to fetch latest data from iThink...")
print(f"URL: {url}")

try:
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        print("\n✓ Success!")
        print(f"Total orders: {data.get('total_count', 0)}")
        print(f"OFD: {data.get('ofd_count', 0)}")
        print(f"Undelivered: {data.get('undelivered_count', 0)}")

        if data.get('undelivered_count', 0) > 0:
            print("\n✓ Found Undelivered orders:")
            for order in data.get('orders', []):
                if order.get('order_type') == 'Undelivered':
                    print(f"   - {order['awb']} | {order['customer_name']}")
        else:
            print("\nℹ No Undelivered orders found")
            print("This is normal - Undelivered orders appear when delivery attempts fail")
    else:
        print(f"\n✗ Error: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n✗ Error: {e}")
    print("\nMake sure backend is running:")
    print("  cd C:\\Users\\Lenovo\\Desktop\\Intransit\\backend")
    print("  python manage.py runserver")

print("\n" + "=" * 70)
