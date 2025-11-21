from django.contrib import admin
from django.utils.html import format_html
from .models import Order, CallHistory


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for Orders"""

    list_display = [
        'awb',
        'customer_name',
        'customer_mobile_display',
        'order_type_badge',
        'current_status',
        'cod_amount',
        'tracking_link_display',
        'synced_at_display'
    ]

    list_display_links = ['awb', 'customer_name']  # These fields open edit page

    list_filter = [
        'order_type',
        'synced_at',
        'created_at'
    ]

    search_fields = [
        'awb',
        'customer_name',
        'customer_mobile',
        'customer_address',
        'customer_pincode'
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'synced_at',
        'tracking_url_link'
    ]

    fieldsets = (
        ('Order Information', {
            'fields': (
                'awb',
                'order_type',
                'current_status',
                'tracking_url_link',
                'order_date'
            )
        }),
        ('Customer Details', {
            'fields': (
                'customer_name',
                'customer_mobile',
                'customer_address',
                'customer_pincode'
            )
        }),
        ('Order Details', {
            'fields': (
                'cod_amount',
                'weight',
                'last_scan'
            )
        }),
        ('System Information', {
            'fields': (
                'created_at',
                'updated_at',
                'synced_at'
            ),
            'classes': ('collapse',)
        })
    )

    def tracking_link_display(self, obj):
        """Separate tracking link button"""
        if obj.tracking_url:
            return format_html(
                '<a href="{}" target="_blank" style="background: #2196F3; color: white; padding: 4px 12px; border-radius: 4px; text-decoration: none; font-size: 0.85em; font-weight: bold;">🔗 Track</a>',
                obj.tracking_url
            )
        return '—'
    tracking_link_display.short_description = 'Tracking'

    def customer_mobile_display(self, obj):
        """Display phone with icon"""
        if obj.customer_mobile and obj.customer_mobile != 'N/A':
            return format_html(
                '<span style="color: #4CAF50;">📞 {}</span>',
                obj.customer_mobile
            )
        return format_html('<span style="color: #f44336;">❌ N/A</span>')
    customer_mobile_display.short_description = 'Mobile'

    def order_type_badge(self, obj):
        """Display order type with color badge"""
        if obj.order_type == 'OFD':
            color = '#2196F3'
            icon = '🚚'
        else:
            color = '#FF9800'
            icon = '⚠️'

        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 12px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.order_type
        )
    order_type_badge.short_description = 'Type'

    def synced_at_display(self, obj):
        """Display last sync time"""
        if obj.synced_at:
            return obj.synced_at.strftime('%Y-%m-%d %H:%M')
        return 'Never'
    synced_at_display.short_description = 'Last Synced'

    def tracking_url_link(self, obj):
        """Tracking URL as clickable link"""
        if obj.tracking_url:
            return format_html(
                '<a href="{}" target="_blank">Track Order →</a>',
                obj.tracking_url
            )
        return 'N/A'
    tracking_url_link.short_description = 'Tracking URL'

    # Allow editing all fields
    def get_readonly_fields(self, request, obj=None):
        """Make certain fields read-only only after creation"""
        if obj:  # Editing existing object
            return ['created_at', 'updated_at', 'synced_at', 'tracking_url_link']
        return []  # Creating new - all editable

    # Enable add permission for manual entry
    def has_add_permission(self, request):
        return True

    # Custom actions
    actions = ['mark_as_ofd', 'mark_as_undelivered', 'sync_phone_numbers', 'cleanup_all_data']

    def cleanup_all_data(self, request, queryset):
        """Delete ALL orders and call history - Fresh start"""
        from .models import CallHistory

        # Delete ALL call history
        call_deleted = CallHistory.objects.all().delete()[0]

        # Delete all OFD/Undelivered orders
        order_deleted = Order.objects.filter(
            order_type__in=['OFD', 'Undelivered']
        ).delete()[0]

        self.message_user(
            request,
            f'🗑️ Cleanup Complete! Deleted {order_deleted} orders and {call_deleted} call history records',
            level='success'
        )
    cleanup_all_data.short_description = '🗑️ DELETE ALL Orders & Call History (Fresh Start)'

    def mark_as_ofd(self, request, queryset):
        """Mark selected orders as OFD"""
        updated = queryset.update(order_type='OFD')
        self.message_user(request, f'{updated} orders marked as OFD')
    mark_as_ofd.short_description = '🚚 Mark as OFD'

    def mark_as_undelivered(self, request, queryset):
        """Mark selected orders as Undelivered"""
        updated = queryset.update(order_type='Undelivered')
        self.message_user(request, f'{updated} orders marked as Undelivered')
    mark_as_undelivered.short_description = '⚠️ Mark as Undelivered'

    def sync_phone_numbers(self, request, queryset):
        """Fetch phone numbers from Track API for selected orders"""
        from .services import IThinkService

        awbs_to_sync = []
        for order in queryset:
            if not order.customer_mobile or order.customer_mobile == 'N/A':
                awbs_to_sync.append(order.awb)

        if not awbs_to_sync:
            self.message_user(request, 'All selected orders already have phone numbers', level='warning')
            return

        # Fetch from Track API
        track_result = IThinkService.track_orders(awbs_to_sync)
        updated_count = 0

        if track_result.get('status') == 'success':
            track_data = track_result.get('data', {})
            for awb, track_info in track_data.items():
                customer_details = track_info.get('customer_details', {})
                phone = customer_details.get('customer_mobile') or customer_details.get('customer_phone')

                if phone and phone != 'N/A':
                    queryset.filter(awb=awb).update(customer_mobile=phone)
                    updated_count += 1

        self.message_user(request, f'Updated {updated_count} phone numbers from Track API')
    sync_phone_numbers.short_description = '📞 Sync Phone Numbers'


@admin.register(CallHistory)
class CallHistoryAdmin(admin.ModelAdmin):
    """Admin interface for Call History"""

    list_display = [
        'call_id_short',
        'awb',
        'customer_name',
        'customer_phone_display',
        'status_badge',
        'success_badge',
        'retry_info',
        'duration_display',
        'created_at_display'
    ]

    list_filter = [
        'status',
        'is_successful',
        'needs_retry',
        'call_type',
        'created_at'
    ]

    search_fields = [
        'call_id',
        'awb',
        'customer_name',
        'customer_phone'
    ]

    readonly_fields = [
        'call_id',
        'awb',
        'customer_name',
        'customer_phone',
        'order_type',
        'call_type',
        'status',
        'duration',
        'cost',
        'ended_reason',
        'vapi_response_display',
        'created_at',
        'updated_at',
        'call_started_at',
        'call_ended_at'
    ]

    fieldsets = (
        ('Call Information', {
            'fields': (
                'call_id',
                'status',
                'call_type',
                'ended_reason'
            )
        }),
        ('Order & Customer', {
            'fields': (
                'awb',
                'customer_name',
                'customer_phone',
                'order_type'
            )
        }),
        ('Call Details', {
            'fields': (
                'duration',
                'cost',
                'call_started_at',
                'call_ended_at'
            )
        }),
        ('Retry Information', {
            'fields': (
                'is_successful',
                'needs_retry',
                'retry_count'
            )
        }),
        ('VAPI Response', {
            'fields': ('vapi_response_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )

    def call_id_short(self, obj):
        """Short call ID display"""
        if obj.call_id:
            short_id = obj.call_id[:8] + '...'
            return format_html(
                '<code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px;">{}</code>',
                short_id
            )
        return 'N/A'
    call_id_short.short_description = 'Call ID'

    def customer_phone_display(self, obj):
        """Phone display with icon"""
        if obj.customer_phone:
            return format_html('📞 {}', obj.customer_phone)
        return 'N/A'
    customer_phone_display.short_description = 'Phone'

    def status_badge(self, obj):
        """Status with color badge"""
        status_colors = {
            'queued': '#9E9E9E',
            'ringing': '#2196F3',
            'in-progress': '#FF9800',
            'ended': '#4CAF50',
            'failed': '#f44336'
        }
        color = status_colors.get(obj.status, '#9E9E9E')

        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.85em; font-weight: bold;">{}</span>',
            color,
            obj.status.upper()
        )
    status_badge.short_description = 'Status'

    def success_badge(self, obj):
        """Success/Failure badge"""
        if obj.is_successful:
            return format_html(
                '<span style="color: #4CAF50; font-weight: bold;">✓ Success</span>'
            )
        elif obj.needs_retry:
            return format_html(
                '<span style="color: #FF9800; font-weight: bold;">🔁 Retry</span>'
            )
        else:
            return format_html(
                '<span style="color: #9E9E9E;">⏳ Pending</span>'
            )
    success_badge.short_description = 'Result'

    def retry_info(self, obj):
        """Retry count display"""
        if obj.retry_count > 0:
            return format_html(
                '<span style="background: #FF9800; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em;">Retry #{}</span>',
                obj.retry_count
            )
        return '—'
    retry_info.short_description = 'Retries'

    def duration_display(self, obj):
        """Duration in seconds"""
        if obj.duration:
            return f"{int(obj.duration)}s"
        return '—'
    duration_display.short_description = 'Duration'

    def created_at_display(self, obj):
        """Created at timestamp"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
    created_at_display.short_description = 'Called At'

    def vapi_response_display(self, obj):
        """Pretty print VAPI response"""
        if obj.vapi_response:
            import json
            formatted = json.dumps(obj.vapi_response, indent=2)
            return format_html(
                '<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 400px; overflow: auto;">{}</pre>',
                formatted
            )
        return 'No response data'
    vapi_response_display.short_description = 'VAPI Response (JSON)'

    # Disable add permission (calls are made via API)
    def has_add_permission(self, request):
        return False
