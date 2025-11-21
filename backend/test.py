import requests
import json
from datetime import datetime, timedelta

# Test script for iThink Logistics API - OFD Orders

print("=" * 60)
print("Out For Delivery (OFD) Orders - Last 10 Days")
print("=" * 60)

# API credentials
ACCESS_TOKEN = "7f9681a8addceb09d2223cb6c3e6bd85"
SECRET_KEY = "87c5cd46a2cd59209d2153da8a074a73"

# Get last 10 days orders
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

print(f"\nFetching orders from {start_date} to {end_date}...")
print("-" * 60)

# Order Details API
payload = {
    "data": {
        "start_date": start_date,
        "end_date": end_date,
        "access_token": ACCESS_TOKEN,
        "secret_key": SECRET_KEY
    }
}

try:
    response = requests.post(
        'https://my.ithinklogistics.com/api_v3/order/get_details.json',
        json=payload,
        timeout=30
    )

    data = response.json()

    if data.get('status') == 'success' and 'data' in data:
        orders = data['data']
        print(f"\n✓ Successfully fetched {len(orders)} orders")

        # Count by status
        status_count = {}
        for awb, order in orders.items():
            pickup_type = order.get('pickup_type', 'unknown')
            status_count[pickup_type] = status_count.get(pickup_type, 0) + 1

        print(f"\nOrders by type:")
        for status, count in status_count.items():
            print(f"  - {status}: {count} orders")

        # Show first 5 orders
        print(f"\nFirst 5 orders:")
        for i, (awb, order) in enumerate(list(orders.items())[:5], 1):
            print(f"\n{i}. AWB: {awb}")
            print(f"   Customer: {order.get('customer_name', 'N/A')}")
            print(f"   Type: {order.get('pickup_type', 'N/A')}")
            print(f"   Order Date: {order.get('order_date', 'N/A')}")
            print(f"   COD Amount: ₹{order.get('total_amount', 'N/A')}")

    else:
        print(f"\n✗ Error: {data.get('message', 'Unknown error')}")

except Exception as e:
    print(f"\n✗ Exception: {str(e)}")

print("\n" + "=" * 60)
