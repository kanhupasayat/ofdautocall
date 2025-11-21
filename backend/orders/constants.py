# API Configuration Constants
BATCH_SIZE = 10  # Number of orders to process in one batch for tracking
READY_TO_DISPATCH_DAYS = 5  # Days to look back for ready-to-dispatch orders
IN_TRANSIT_DAYS = 10  # Days to look back for in-transit orders
OFD_DAYS = 10  # Days to look back for OFD/Undelivered orders
ESTIMATED_DELIVERY_DAYS = 3  # Estimated days for delivery after AWB creation

# Cache Configuration
CACHE_TIMEOUT_OFD = 300  # 5 minutes for OFD orders cache
CACHE_TIMEOUT_CALL_HISTORY = 30  # 30 seconds for call history cache

# Order Status Constants
ORDER_STATUS_MANIFESTED = 'Manifested'
ORDER_STATUS_IN_TRANSIT = 'In Transit'
ORDER_STATUS_OFD = 'OFD'
ORDER_STATUS_UNDELIVERED = 'Undelivered'
ORDER_STATUS_DELIVERED = 'Delivered'
ORDER_STATUS_RTO = 'RTO'

# Cleanup Status Keywords (for filtering delivered/completed orders)
CLEANUP_STATUSES = [
    'delivered',
    'rto',
    'cancelled',
    'lost',
    'damaged',
    'returned',
]

# Retry-worthy call ending reasons
RETRY_REASONS = [
    'busy',
    'no-answer',
    'voicemail',
    'assistant-error',
    'pipeline-error-openai-voice-failed',
]

# API Timeouts (in seconds)
ITHINK_API_TIMEOUT = 60
VAPI_API_TIMEOUT = 30

# Phone number validation
MIN_PHONE_NUMBER_LENGTH = 10
DEFAULT_COUNTRY_CODE = '+91'  # India
