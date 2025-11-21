import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from orders.models import CallHistory
from orders.vapi_service import VAPIService

print("=" * 60)
print("VAPI API Test Script")
print("=" * 60)

# Get latest call from database
latest_call = CallHistory.objects.order_by('-created_at').first()

if not latest_call:
    print("\nNo calls found in database!")
    print("Please make at least one call first.")
    sys.exit(1)

print(f"\nLatest call in database:")
print(f"  Call ID: {latest_call.call_id}")
print(f"  AWB: {latest_call.awb}")
print(f"  Status: {latest_call.status}")
print(f"  Created: {latest_call.created_at}")
print(f"  Ended Reason in DB: {latest_call.ended_reason}")

# Fetch from VAPI API
print(f"\n{'=' * 60}")
print("Fetching fresh data from VAPI API...")
print(f"{'=' * 60}")

call_data = VAPIService.get_call_details(latest_call.call_id)

if 'error' in call_data:
    print(f"\nERROR: {call_data['error']}")
    if 'details' in call_data:
        print(f"Details: {call_data['details']}")
    sys.exit(1)

print("\nVAPI API Response:")
print(f"  Status: {call_data.get('status')}")
print(f"  Ended Reason: {call_data.get('endedReason')}")
print(f"  Duration: {call_data.get('duration')} seconds")
print(f"  Cost: ${call_data.get('cost', 0)}")

# Check for analysis
analysis = call_data.get('analysis', {})
if analysis:
    print(f"\n  Analysis found:")
    print(f"    Keys: {list(analysis.keys())}")
    success_eval = analysis.get('successEvaluation')
    print(f"    Success Evaluation: {success_eval} (type: {type(success_eval)})")
else:
    print(f"\n  NO ANALYSIS DATA in response")

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)
