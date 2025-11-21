#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from orders.models import CallHistory

# Extract recording for specific call
call = CallHistory.objects.filter(awb='21025849704862').first()

if call:
    recording_url = call.vapi_response.get('recordingUrl')
    transcript = call.vapi_response.get('transcript', '')

    call.recording_url = recording_url
    call.transcript = transcript
    call.save()

    print(f'Updated call {call.awb}')
    print(f'Recording: {recording_url[:60]}...')
    print(f'Transcript: {len(transcript)} chars')
else:
    print('Call not found')
