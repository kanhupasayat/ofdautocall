import requests
import json

awb = "13624626468034"

payload = {
    "data": {
        "awb_number_list": awb,
        "access_token": "7f9681a8addceb09d2223cb6c3e6bd85",
        "secret_key": "87c5cd46a2cd59209d2153da8a074a73"
    }
}

response = requests.post('https://api.ithinklogistics.com/api_v3/order/track.json', json=payload)
data = response.json()

print("API Response:")
print(json.dumps(data, indent=2))

if data.get('status') == 'success' and 'data' in data:
    if awb in data['data']:
        order_info = data['data'][awb]
        print(f"\nAWB: {awb}")
        print(f"Current Status: {order_info.get('current_status')}")
        print(f"Delivered: {order_info.get('delivered')}")
        print(f"RTO: {order_info.get('rto')}")
