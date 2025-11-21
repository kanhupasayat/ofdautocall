import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from orders.models import CallHistory
from django.utils import timezone

today = timezone.now().date()

# Check successful calls
successful_calls = CallHistory.objects.filter(
    created_at__date=today,
    ended_reason__in=['customer-ended-call', 'assistant-ended-call']
)

print(f'Successful calls (conversation happened): {successful_calls.count()}')

with_recording = successful_calls.filter(recording_url__isnull=False)
without_recording = successful_calls.filter(recording_url__isnull=True)

print(f'With recording: {with_recording.count()}')
print(f'WITHOUT recording: {without_recording.count()}\n')

if without_recording.count() > 0:
    print('⚠️ Missing recordings in successful calls:')
    for c in without_recording:
        print(f'  AWB: {c.awb}')
        print(f'  Ended: {c.ended_reason}')
        print(f'  Created: {c.created_at}')
        print(f'  Has vapi_response: {c.vapi_response is not None}')
        if c.vapi_response:
            has_rec = 'recordingUrl' in c.vapi_response or 'stereoRecordingUrl' in c.vapi_response
            print(f'  Recording in vapi_response: {has_rec}')
        print('  ---')
