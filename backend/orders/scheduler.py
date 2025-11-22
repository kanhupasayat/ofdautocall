import schedule
import time
import threading
from datetime import datetime, time as dt_time
from .vapi_service import VAPIService
from .models import CallHistory, Order
from django.utils.dateparse import parse_datetime
from django.db.models import Q


class AutoCallScheduler:
    """
    Scheduler to automatically call pending orders every hour from 10 AM to 1 PM
    """

    def __init__(self):
        self.running = False
        self.thread = None
        self.hourly_mode = True  # Run hourly from 10 AM - 1 PM

        # Live tracking variables
        self.current_session = {
            'is_calling': False,
            'session_start': None,
            'total_to_call': 0,
            'completed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'current_order': None,
            'logs': []  # Last 20 logs
        }

    def get_pending_calls(self):
        """
        Get pending calls list (Not Called + Retry Needed)
        OPTIMIZED: Only calls that need calling, avoids duplicates
        """
        from datetime import datetime, time as dt_time, timedelta

        # Get all OFD/Undelivered orders
        ofd_orders = Order.objects.filter(
            Q(order_type='OFD') | Q(order_type='Undelivered')
        )

        # Get today's call history
        today_start = datetime.combine(datetime.now().date(), dt_time.min)
        today_end = datetime.combine(datetime.now().date(), dt_time.max)

        # Get all AWBs that were called today successfully
        successfully_called_awbs = CallHistory.objects.filter(
            created_at__range=(today_start, today_end),
            is_successful=True
        ).values_list('awb', flat=True).distinct()

        # OPTIMIZATION: Get AWBs called in last 2 hours (avoid calling too frequently)
        two_hours_ago = datetime.now() - timedelta(hours=2)
        recently_called_awbs = CallHistory.objects.filter(
            created_at__gte=two_hours_ago
        ).values_list('awb', flat=True).distinct()

        # Get all AWBs that were called today (to check if called or not)
        called_awbs = CallHistory.objects.filter(
            created_at__range=(today_start, today_end)
        ).values_list('awb', flat=True).distinct()

        pending_calls = []

        # 1. Not Called Orders - OFD orders that haven't been called today
        for order in ofd_orders:
            # Skip if already called successfully
            if order.awb in successfully_called_awbs:
                continue

            # OPTIMIZATION: Skip if called in last 2 hours (avoid spamming)
            if order.awb in recently_called_awbs:
                continue

            if order.awb not in called_awbs:
                pending_calls.append({
                    'awb': order.awb,
                    'customer_name': order.customer_name,
                    'customer_mobile': order.customer_mobile,
                    'customer_address': order.customer_address,
                    'customer_pincode': order.customer_pincode,
                    'cod_amount': order.cod_amount,
                    'order_type': order.order_type,
                    'current_status': order.current_status,
                    'call_status': 'not_called',
                    'retry_count': 0
                })

        # 2. Retry Needed Orders - Failed calls that need retry
        retry_calls = CallHistory.objects.filter(
            created_at__range=(today_start, today_end),
            needs_retry=True,
            is_successful=False,
            retry_count__lt=3  # Max 3 retries
        ).exclude(awb__in=successfully_called_awbs).order_by('awb', '-created_at')

        processed_awbs = set()
        for call in retry_calls:
            # Only take the latest call per AWB
            if call.awb in processed_awbs:
                continue
            processed_awbs.add(call.awb)

            # Get order details from Order model
            try:
                order = Order.objects.get(awb=call.awb)
                pending_calls.append({
                    'awb': call.awb,
                    'customer_name': call.customer_name,
                    'customer_mobile': call.customer_phone,
                    'customer_address': order.customer_address,
                    'customer_pincode': order.customer_pincode,
                    'cod_amount': order.cod_amount,
                    'order_type': call.order_type,
                    'current_status': order.current_status,
                    'call_status': 'retry_needed',
                    'retry_count': call.retry_count,
                    'last_call_reason': call.ended_reason
                })
            except Order.DoesNotExist:
                continue

        return pending_calls

    def add_log(self, message, log_type='info'):
        """Add log message to current session"""
        log_entry = {
            'time': datetime.now().strftime('%H:%M:%S'),
            'message': message,
            'type': log_type  # 'info', 'success', 'error', 'warning'
        }
        self.current_session['logs'].append(log_entry)
        # Keep only last 20 logs
        if len(self.current_session['logs']) > 20:
            self.current_session['logs'] = self.current_session['logs'][-20:]

    def sync_ofd_orders(self):
        """Sync OFD/Undelivered orders from iThink API before calling"""
        from .services import IThinkService
        from datetime import timedelta

        print(f"\n{'='*70}")
        print(f"PRE-SYNC: Fetching Fresh OFD/Undelivered Data - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*70}")

        msg = "🔄 Starting iThink API sync - Fetching last 7 days orders..."
        print(f"[SYNC] {msg}")
        self.add_log(msg, 'info')

        # Get orders from last 7 days
        from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')

        msg = f"📡 API Call: Order Details API ({from_date} to {to_date})"
        print(f"[API] {msg}")
        self.add_log(msg, 'info')

        result = IThinkService.get_orders_by_date_range(from_date, to_date)

        if "error" in result:
            msg = f"❌ Sync failed: {result.get('error')}"
            print(f"[FAIL] {msg}")
            self.add_log(msg, 'error')
            return 0

        if result.get('status') != 'success' or 'data' not in result:
            msg = f"Sync failed: Invalid response"
            print(f"[FAIL] {msg}")
            self.add_log(msg, 'error')
            return 0

        orders_data = result['data']
        new_count = 0
        updated_count = 0

        msg = f"✅ API Response received: {len(orders_data)} total orders found"
        print(f"[API] {msg}")
        self.add_log(msg, 'success')

        # Collect OFD/Undelivered orders first (to avoid unnecessary Track API calls)
        msg = "🔍 Filtering OFD/Undelivered orders..."
        print(f"[FILTER] {msg}")
        self.add_log(msg, 'info')

        temp_ofd_orders = []
        for awb, order in orders_data.items():
            order_status = order.get('latest_courier_status', '').lower()

            # Skip delivered and RTO
            if 'delivered' in order_status and 'undelivered' not in order_status:
                continue
            if 'rto' in order_status:
                continue

            # Check if OFD or Undelivered
            is_ofd = any(s in order_status for s in ['out for delivery', 'ofd', 'dispatched for delivery'])
            is_undelivered = any(s in order_status for s in ['undelivered', 'not delivered', 'delivery failed'])

            if is_ofd or is_undelivered:
                order_type = 'OFD' if is_ofd else 'Undelivered'
                temp_ofd_orders.append({
                    'awb': awb,
                    'order': order,
                    'order_type': order_type,
                    'order_status': order_status
                })

        msg = f"📦 Found {len(temp_ofd_orders)} OFD/Undelivered orders (filtered from {len(orders_data)})"
        print(f"[SYNC] {msg}")
        self.add_log(msg, 'success')

        # Get phone numbers from Track API for orders with missing/invalid phone
        awbs_to_track = []
        for item in temp_ofd_orders:
            order = item['order']
            # Check BOTH customer_phone AND customer_mobile fields
            phone = order.get('customer_phone') or order.get('customer_mobile')
            if not phone or phone == 'N/A' or phone == '' or len(phone) < 10:
                awbs_to_track.append(item['awb'])

        # Fetch phone numbers from Track API in batches
        phone_map = {}
        if awbs_to_track:
            msg = f"📞 {len(awbs_to_track)} orders missing phone - calling Track API..."
            print(f"[SYNC] {msg}")
            self.add_log(msg, 'warning')

            batch_size = 10  # iThink API limit: Maximum 10 AWBs per tracking request
            for i in range(0, len(awbs_to_track), batch_size):
                batch = awbs_to_track[i:i + batch_size]
                msg = f"📡 API Call: Track API - Batch {i//batch_size + 1} ({len(batch)} AWBs)"
                print(f"[API]   {msg}")
                self.add_log(msg, 'info')

                track_result = IThinkService.track_orders(batch)
                if track_result.get('status') == 'success':
                    track_data = track_result.get('data', {})
                    for awb, track_info in track_data.items():
                        customer_details = track_info.get('customer_details', {})
                        phone = customer_details.get('customer_mobile') or customer_details.get('customer_phone')
                        if phone and phone != 'N/A' and len(phone) >= 10:
                            phone_map[awb] = phone
                            print(f"[SYNC]     ✓ {awb}: {phone}")

        # Now process and save orders with phone numbers
        for item in temp_ofd_orders:
            awb = item['awb']
            order = item['order']
            order_type = item['order_type']
            order_status = item['order_status']

            # Get phone from Order Details first (check BOTH fields), then Track API
            customer_mobile = order.get('customer_phone') or order.get('customer_mobile')
            if not customer_mobile or customer_mobile == 'N/A' or customer_mobile == '' or len(customer_mobile) < 10:
                customer_mobile = phone_map.get(awb, 'N/A')

            # Check if already exists
            existing = Order.objects.filter(awb=awb).first()
            if existing:
                # Update if order type changed OR if phone was N/A and now we have valid phone
                if existing.order_type != order_type or (existing.customer_mobile == 'N/A' and customer_mobile != 'N/A'):
                    existing.order_type = order_type
                    existing.current_status = order_status
                    existing.customer_mobile = customer_mobile
                    existing.save()
                    updated_count += 1
                    phone_status = "✓" if customer_mobile != 'N/A' else "✗"
                    print(f"[SYNC] {phone_status} Updated: {awb} - {customer_mobile}")
            else:
                Order.objects.create(
                    awb=awb,
                    customer_name=order.get('customer_name', 'N/A'),
                    customer_mobile=customer_mobile,
                    customer_address=order.get('customer_address', 'N/A'),
                    customer_pincode=order.get('customer_pincode', 'N/A'),
                    cod_amount=order.get('cod_amount', 0),
                    weight=order.get('weight', 0),
                    order_date=order.get('order_date'),
                    tracking_url=f'https://www.ithinklogistics.co.in/postship/tracking/{awb}',
                    current_status=order_status,
                    order_type=order_type
                )
                new_count += 1
                phone_status = "✓" if customer_mobile != 'N/A' else "✗"
                print(f"[SYNC] {phone_status} Created: {awb} - {customer_mobile}")

        msg = f"✅ Database sync complete: {new_count} new orders, {updated_count} updated"
        print(f"[OK] {msg}")
        self.add_log(msg, 'success')

        msg = f"💾 Total OFD/Undelivered orders in system: {Order.objects.filter(Q(order_type='OFD') | Q(order_type='Undelivered')).count()}"
        print(f"[DB] {msg}")
        self.add_log(msg, 'info')

        return new_count + updated_count

    def make_calls_to_pending_orders(self):
        """Make calls to all pending orders (not called + retry needed)"""
        current_time = datetime.now()
        print(f"\n{'='*70}")
        print(f"Auto Call Scheduler - {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

        # Check if within allowed time (10 AM - 5 PM)
        current_hour = current_time.hour
        if current_hour < 10 or current_hour >= 17:
            msg = f"Outside calling hours (10 AM - 5 PM). Current: {current_hour}:00"
            print(f"[TIME] {msg}")
            self.add_log(msg, 'warning')
            return

        # Initialize session
        self.current_session = {
            'is_calling': True,
            'session_start': current_time.strftime('%H:%M:%S'),
            'total_to_call': 0,
            'completed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'current_order': None,
            'logs': self.current_session.get('logs', [])  # Preserve old logs
        }

        # STEP 1: Sync new OFD/Undelivered orders from iThink API
        msg = "🔄 STEP 1: Syncing fresh OFD/Undelivered orders from iThink..."
        print(f"[SESSION] {msg}")
        self.add_log(msg, 'info')
        self.sync_ofd_orders()

        # STEP 2: Get all pending calls
        msg = "📋 STEP 2: Identifying pending calls (not called + retry needed)..."
        print(f"[SESSION] {msg}")
        self.add_log(msg, 'info')
        pending_calls = self.get_pending_calls()

        if not pending_calls:
            msg = "No pending calls found. All orders called successfully!"
            print(f"[OK] {msg}")
            self.add_log(msg, 'success')
            self.current_session['is_calling'] = False
            return

        self.current_session['total_to_call'] = len(pending_calls)

        not_called = [c for c in pending_calls if c['call_status'] == 'not_called']
        retry_needed = [c for c in pending_calls if c['call_status'] == 'retry_needed']

        msg = f"📞 STEP 3: Making calls to {len(pending_calls)} orders ({len(not_called)} new + {len(retry_needed)} retry)"
        print(f"[CALL] {msg}")
        self.add_log(msg, 'info')

        success_count = 0
        failed_count = 0
        skipped_count = 0

        for call_data in pending_calls:
            phone_number = call_data.get('customer_mobile')

            # Update current order
            self.current_session['current_order'] = {
                'awb': call_data.get('awb'),
                'customer_name': call_data.get('customer_name'),
                'retry_count': call_data.get('retry_count', 0)
            }

            if not phone_number or phone_number == 'N/A':
                msg = f"Skipping {call_data['awb']} - No phone number"
                print(f"[SKIP] {msg}")
                self.add_log(msg, 'warning')
                skipped_count += 1
                self.current_session['skipped'] = skipped_count
                self.current_session['completed'] += 1
                continue

            retry_label = f"Retry #{call_data['retry_count']}" if call_data['retry_count'] > 0 else "First Call"
            msg = f"📞 Calling {call_data['awb']} - {call_data['customer_name']} ({retry_label})"
            print(f"[CALL] {msg}")
            self.add_log(msg, 'info')

            # Make call using VAPI
            msg = f"📡 API Call: VAPI - Making call to {phone_number}"
            print(f"[API] {msg}")
            self.add_log(msg, 'info')

            result = VAPIService.make_ofd_call(phone_number, call_data)

            if "error" in result:
                msg = f"❌ Call failed for {call_data['awb']}: {result.get('error')}"
                print(f"   [FAIL] {msg}")
                self.add_log(msg, 'error')
                failed_count += 1
                self.current_session['failed'] = failed_count
                self.current_session['completed'] += 1
                continue

            # Save to database with retry count
            msg = f"💾 Saving call record to database..."
            self.add_log(msg, 'info')

            try:
                previous_calls = CallHistory.objects.filter(
                    awb=call_data.get('awb'),
                    created_at__gte=datetime.combine(datetime.now().date(), dt_time.min)
                ).count()

                CallHistory.objects.create(
                    call_id=result.get('id'),
                    awb=call_data.get('awb', 'N/A'),
                    customer_name=call_data.get('customer_name', 'N/A'),
                    customer_phone=phone_number,
                    order_type=call_data.get('order_type', 'OFD'),
                    assistant_id=result.get('assistantId'),
                    phone_number_id=result.get('phoneNumberId'),
                    status=result.get('status'),
                    call_type=result.get('type'),
                    cost=result.get('cost', 0),
                    ended_reason=result.get('endedReason'),
                    retry_count=previous_calls,
                    call_started_at=parse_datetime(result.get('createdAt')) if result.get('createdAt') else None,
                    vapi_response=result
                )
                msg = f"✅ Call successful: {call_data['awb']} | Call ID: {result.get('id')[:12]}... | Cost: ${result.get('cost', 0)}"
                print(f"   [OK] {msg}")
                self.add_log(msg, 'success')
                success_count += 1
                self.current_session['successful'] = success_count
                self.current_session['completed'] += 1
            except Exception as e:
                msg = f"Error saving {call_data['awb']}: {str(e)}"
                print(f"   [FAIL] {msg}")
                self.add_log(msg, 'error')
                failed_count += 1
                self.current_session['failed'] = failed_count
                self.current_session['completed'] += 1

            # Small delay between calls
            time.sleep(2)

        # Session complete
        self.current_session['is_calling'] = False
        self.current_session['current_order'] = None

        total_cost = sum([call.cost for call in CallHistory.objects.filter(
            created_at__gte=datetime.combine(datetime.now().date(), dt_time.min)
        )])

        summary = f"🎉 Session Complete! Success: {success_count} | Failed: {failed_count} | Skipped: {skipped_count} | Total Cost: ${total_cost:.4f}"
        print(f"\n{'='*70}")
        print(f"[STATS] {summary}")
        print(f"{'='*70}\n")
        self.add_log(summary, 'success')

    def run_scheduler(self):
        """Run the scheduler in background"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def cleanup_daily_data(self):
        """Delete all orders and call history - Fresh start every morning at 9:45 AM"""
        from django.core.cache import cache

        print("\n" + "="*70)
        print("DAILY CLEANUP - 9:45 AM")
        print("="*70)

        # Delete ALL call history
        call_deleted = CallHistory.objects.all().delete()[0]

        # Delete all OFD/Undelivered orders
        order_deleted = Order.objects.filter(
            order_type__in=['OFD', 'Undelivered']
        ).delete()[0]

        # Clear ALL Django cache
        cache.clear()

        print(f"✓ Deleted {order_deleted} orders")
        print(f"✓ Deleted {call_deleted} call history records")
        print(f"✓ Cleared all cache (OFD orders, call history, etc.)")
        print(f"✓ Fresh start! Ready for new day")
        print(f"   Next cleanup: Tomorrow 9:45 AM")
        print("="*70 + "\n")

    def extract_missing_recordings(self):
        """
        Extract recordings from vapi_response for calls that don't have recording_url yet
        This is a fallback in case webhooks don't catch recordings
        """
        # NOTE: recording_url field doesn't exist in CallHistory model yet
        # This function is placeholder for future enhancement
        return

        # Find calls with vapi_response but no recording_url
        calls = CallHistory.objects.filter(
            vapi_response__isnull=False
        )

        if calls.count() == 0:
            return

        print(f"\n[EXTRACT RECORDINGS] Found {calls.count()} calls")

        updated_count = 0
        for call in calls:
            # Extract recording URL (check multiple locations)
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
                print(f"[EXTRACT] Updated {call.awb} - Recording: {'Yes' if recording_url else 'No'} | Transcript: {'Yes' if transcript else 'No'}")

        if updated_count > 0:
            print(f"[EXTRACT RECORDINGS] Extracted {updated_count} recordings")

    def start_hourly_scheduler(self):
        """Start hourly scheduler - calls 4 times per day (10:30 AM, 11 AM, 12 PM, 1 PM)"""
        if self.running:
            print("⚠ Scheduler already running")
            return

        schedule.clear()

        # Schedule daily cleanup at 9:45 AM
        schedule.every().day.at("09:45").do(self.cleanup_daily_data)

        # Pre-sync jobs: 10 minutes before each call session
        # This fetches fresh OFD/Undelivered data before calls start
        schedule.every().day.at("10:20").do(self.sync_ofd_orders)  # 10 min before 10:30
        schedule.every().day.at("10:50").do(self.sync_ofd_orders)  # 10 min before 11:00
        schedule.every().day.at("11:50").do(self.sync_ofd_orders)  # 10 min before 12:00
        schedule.every().day.at("12:50").do(self.sync_ofd_orders)  # 10 min before 1:00

        # Schedule calls at 10:30 AM, 11 AM, 12 PM, 1 PM
        # Smart filtering prevents duplicate/spam calls
        schedule.every().day.at("10:30").do(self.make_calls_to_pending_orders)
        schedule.every().day.at("11:00").do(self.make_calls_to_pending_orders)
        schedule.every().day.at("12:00").do(self.make_calls_to_pending_orders)
        schedule.every().day.at("13:00").do(self.make_calls_to_pending_orders)

        # Extract missing recordings every 10 minutes (fallback if webhook misses)
        schedule.every(10).minutes.do(self.extract_missing_recordings)

        self.running = True
        self.thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.thread.start()

        print(f"[OK] Hourly Auto Call Scheduler Started")
        print(f"   Daily cleanup: 9:45 AM (auto delete all data)")
        print(f"   Pre-sync times: 10:20 AM, 10:50 AM, 11:50 AM, 12:50 PM (10 min before calls)")
        print(f"   Calling times: 10:30 AM, 11:00 AM, 12:00 PM, 1:00 PM (4 sessions)")
        print(f"   Recording extraction: Every 10 minutes (auto-extract missing recordings)")
        print(f"   Smart filtering: 2-hour cooldown + duplicate prevention")
        print(f"   Current time: {datetime.now().strftime('%H:%M:%S')}")

    def start(self, time_str=None):
        """
        Start the scheduler
        If time_str is provided, schedule once at that time
        Otherwise, start hourly scheduler (10 AM - 1 PM)
        """
        if time_str:
            # Legacy mode - single time
            if self.running:
                print("⚠ Scheduler already running")
                return

            schedule.clear()
            schedule.every().day.at(time_str).do(self.make_calls_to_pending_orders)
            self.running = True
            self.thread = threading.Thread(target=self.run_scheduler, daemon=True)
            self.thread.start()
            print(f"[OK] Scheduler started - Calls at {time_str} daily")
        else:
            # Hourly mode (10 AM - 1 PM)
            self.start_hourly_scheduler()

    def stop(self):
        """Stop the scheduler"""
        self.running = False
        schedule.clear()
        print("[OK] Auto call scheduler stopped")

    def get_status(self):
        """Get scheduler status with live session data"""
        next_runs = []
        for job in schedule.jobs:
            next_runs.append(str(job.next_run))

        return {
            'running': self.running,
            'mode': 'hourly' if self.hourly_mode else 'single',
            'cleanup_time': '09:45',  # Daily cleanup at 9:45 AM
            'scheduled_times': ['10:30', '11:00', '12:00', '13:00'] if self.hourly_mode else [],
            'next_runs': next_runs,
            'current_time': datetime.now().strftime('%H:%M:%S'),

            # Live session data
            'live_session': self.current_session
        }


# Global scheduler instance
auto_call_scheduler = AutoCallScheduler()
