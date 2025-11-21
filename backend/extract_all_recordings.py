#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from orders.models import CallHistory

# Extract recordings for all calls that have vapi_response but no recording_url
calls = CallHistory.objects.filter(
    vapi_response__isnull=False,
    recording_url__isnull=True
)

print(f'Found {calls.count()} calls with vapi_response but no recording_url')

updated_count = 0
for call in calls:
    # Extract recording URL
    recording_url = (
        call.vapi_response.get('recordingUrl') or
        call.vapi_response.get('stereoRecordingUrl') or
        call.vapi_response.get('artifact', {}).get('recordingUrl') or
        call.vapi_response.get('artifact', {}).get('stereoRecordingUrl') or
        call.vapi_response.get('artifact', {}).get('recording', {}).get('mono', {}).get('combinedUrl')
    )

    # Extract transcript
    transcript = (
        call.vapi_response.get('transcript') or
        call.vapi_response.get('artifact', {}).get('transcript')
    )

    if recording_url or transcript:
        if recording_url:
            call.recording_url = recording_url
        if transcript:
            call.transcript = transcript

        call.save()
        updated_count += 1
        print(f'[OK] Updated {call.awb} - Recording: {"Yes" if recording_url else "No"} | Transcript: {"Yes" if transcript else "No"}')

print(f'\n[DONE] Updated {updated_count} calls')
