from orders.models import CallHistory
import json

call = CallHistory.objects.filter(awb='21025849704862').first()

print('=== CALL DETAILS ===')
print(f'AWB: {call.awb}')
print(f'Status: {call.status}')
print(f'Ended Reason: {call.ended_reason}')
print(f'Recording URL in DB: {call.recording_url}')
print(f'Transcript in DB: {len(call.transcript) if call.transcript else 0} chars')

print('\n=== RECORDING URL IN VAPI RESPONSE ===')
print(f"recordingUrl: {call.vapi_response.get('recordingUrl')}")
print(f"stereoRecordingUrl: {call.vapi_response.get('stereoRecordingUrl')}")

print('\n=== TRANSCRIPT IN VAPI RESPONSE ===')
transcript = call.vapi_response.get('transcript', 'No transcript')
if transcript:
    print(transcript[:500])

print('\n=== ARTIFACT ===')
artifact = call.vapi_response.get('artifact')
print(f'Artifact exists: {artifact is not None}')
if artifact:
    print(json.dumps(artifact, indent=2)[:500])

print('\n=== NOW EXTRACTING ===')
# Extract recording
recording_url = (
    call.vapi_response.get('recordingUrl') or
    call.vapi_response.get('stereoRecordingUrl') or
    call.vapi_response.get('artifact', {}).get('recordingUrl') or
    call.vapi_response.get('artifact', {}).get('recording', {}).get('mono', {}).get('combinedUrl')
)

if recording_url:
    call.recording_url = recording_url
    print(f'✅ Extracted recording URL: {recording_url[:80]}...')
else:
    print('❌ No recording URL found')

# Extract transcript
transcript = (
    call.vapi_response.get('transcript') or
    call.vapi_response.get('artifact', {}).get('transcript')
)

if transcript:
    call.transcript = transcript
    print(f'✅ Extracted transcript: {len(transcript)} chars')
else:
    print('❌ No transcript found')

call.save()
print('\n✅ Call history updated!')
