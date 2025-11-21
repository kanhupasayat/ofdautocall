import requests
import json

# Test script for VAPI call

print("=" * 60)
print("VAPI Test Call - 6370997812")
print("=" * 60)

url = "http://localhost:8000/api/orders/make-call/"

payload = {
    "phone_number": "6370997812",
    "order_data": {
        "awb": "TEST123456",
        "customer_name": "Test Customer",
        "order_type": "OFD",
        "current_status": "Out for delivery",
        "customer_address": "Test Address, Jaipur",
        "customer_pincode": "302001",
        "cod_amount": "500"
    }
}

print("\nMaking test call to: 6370997812")
print("-" * 60)

try:
    response = requests.post(url, json=payload, timeout=30)

    print(f"\nStatus Code: {response.status_code}")
    print("\nResponse:")
    print(json.dumps(response.json(), indent=2))

    if response.status_code == 200:
        print("\n[OK] Call initiated successfully!")
    else:
        print("\n[ERROR] Call failed!")

except Exception as e:
    print(f"\n[ERROR] Exception: {str(e)}")

print("\n" + "=" * 60)
