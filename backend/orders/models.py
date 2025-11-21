
from django.db import models
from django.utils import timezone


class Order(models.Model):
    """Model to cache order data from iThink API"""

    # Order identifiers
    awb = models.CharField(max_length=100, unique=True, db_index=True)
    order_type = models.CharField(max_length=50, db_index=True)  # OFD, Undelivered, InTransit, ReadyToDispatch

    # Customer details
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    customer_mobile = models.CharField(max_length=20, null=True, blank=True)
    customer_address = models.TextField(null=True, blank=True)
    customer_pincode = models.CharField(max_length=10, null=True, blank=True)

    # Order details
    cod_amount = models.CharField(max_length=20, null=True, blank=True)
    weight = models.CharField(max_length=50, null=True, blank=True)
    order_date = models.CharField(max_length=100, null=True, blank=True)
    tracking_url = models.URLField(max_length=500, null=True, blank=True)
    current_status = models.CharField(max_length=100, null=True, blank=True)

    # Last scan information (JSON)
    last_scan = models.JSONField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    synced_at = models.DateTimeField(default=timezone.now, db_index=True)  # Last sync from API

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['awb']),  # For AWB lookups
            models.Index(fields=['order_type', '-updated_at']),  # For filtering by type
            models.Index(fields=['synced_at']),  # For sync operations
            models.Index(fields=['order_type', 'current_status']),  # For OFD/Undelivered filtering
            models.Index(fields=['customer_mobile']),  # For phone lookups
        ]

    def __str__(self):
        return f"{self.awb} - {self.order_type}"


class CallHistory(models.Model):
    """Model to store VAPI call history"""

    call_id = models.CharField(max_length=255, unique=True)
    awb = models.CharField(max_length=100, db_index=True)
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20, db_index=True)
    order_type = models.CharField(max_length=50)  # OFD or Undelivered

    # VAPI response fields
    assistant_id = models.CharField(max_length=255, null=True, blank=True)
    phone_number_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)  # queued, in-progress, completed, failed
    call_type = models.CharField(max_length=50, null=True, blank=True)

    # Call details
    duration = models.IntegerField(null=True, blank=True)  # in seconds
    cost = models.FloatField(null=True, blank=True)
    ended_reason = models.CharField(max_length=100, null=True, blank=True)

    # Retry tracking fields
    retry_count = models.IntegerField(default=0)  # How many times this order was retried
    is_successful = models.BooleanField(default=False, db_index=True)  # If call was successful
    needs_retry = models.BooleanField(default=False, db_index=True)  # If call needs retry

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    call_started_at = models.DateTimeField(null=True, blank=True)
    call_ended_at = models.DateTimeField(null=True, blank=True)

    # Full VAPI response (JSON)
    vapi_response = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Call History'
        verbose_name_plural = 'Call Histories'
        indexes = [
            models.Index(fields=['awb', '-created_at']),
            models.Index(fields=['customer_phone', '-created_at']),
        ]

    def __str__(self):
        return f"{self.awb} - {self.customer_phone} ({self.status})"

    def update_retry_status(self):
        """Update retry flags based on call outcome"""
        # Check if call was successful
        if self.vapi_response and isinstance(self.vapi_response, dict):
            analysis = self.vapi_response.get('analysis', {})
            if analysis:
                success_eval = analysis.get('successEvaluation')
                if success_eval is True or str(success_eval).lower() == 'true':
                    self.is_successful = True
                    self.needs_retry = False
                    return

        # Check if needs retry based on ended_reason
        retry_reasons = ['busy', 'no-answer', 'voicemail', 'assistant-error', 'pipeline-error-openai-voice-failed']
        if self.ended_reason and any(reason in self.ended_reason.lower() for reason in retry_reasons):
            self.needs_retry = True
            self.is_successful = False
        else:
            self.needs_retry = False
