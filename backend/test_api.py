import requests
import json

# Test the In Transit API endpoint
print("Testing In Transit API endpoint...")
print("-" * 50)

try:
    response = requests.get('http://localhost:8000/api/orders/in-transit/')

    if response.status_code == 200:
        data = response.json()
        print(f"[OK] API Response Status: {response.status_code}")
        print(f"[OK] Total Orders: {data['count']}")
        print(f"[OK] Delayed Orders: {data['delayed_count']}")
        print(f"\nFirst few orders:")

        for i, order in enumerate(data['orders'][:3], 1):
            print(f"\n{i}. AWB: {order['awb']}")
            print(f"   Customer: {order['customer_name']}")
            print(f"   Status: {order.get('current_status', 'In Transit')}")
            print(f"   Estimated Delivery: {order['estimated_delivery_date']}")
            print(f"   Is Delayed: {order['is_delayed']}")
            print(f"   Tracking URL: {order['tracking_url']}")

    else:
        print(f"[ERROR] Status code {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"[ERROR] {str(e)}")

print("\n" + "=" * 50)
print("Testing Ready to Dispatch API endpoint...")
print("-" * 50)

try:
    response = requests.get('http://localhost:8000/api/orders/ready-to-dispatch/')

    if response.status_code == 200:
        data = response.json()
        print(f"[OK] API Response Status: {response.status_code}")
        print(f"[OK] Total Orders: {data['count']}")
        print(f"\nFirst few orders:")

        for i, order in enumerate(data['orders'][:3], 1):
            print(f"\n{i}. AWB: {order['awb']}")
            print(f"   Customer: {order['customer_name']}")
            print(f"   Status: {order.get('current_status', 'Ready to Dispatch')}")
            print(f"   Tracking URL: {order['tracking_url']}")

    else:
        print(f"[ERROR] Status code {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"[ERROR] {str(e)}")
