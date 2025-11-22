"""
Django management command to verify database configuration and CallHistory table
Usage: python manage.py check_database
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from orders.models import CallHistory, Order
from django.db import connection


class Command(BaseCommand):
    help = 'Check database configuration and CallHistory table status'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*70)
        self.stdout.write("DATABASE DIAGNOSTIC CHECK")
        self.stdout.write("="*70 + "\n")

        # Check database configuration
        db_config = settings.DATABASES['default']
        self.stdout.write("📊 Database Configuration:")
        self.stdout.write(f"   Engine: {db_config['ENGINE']}")
        self.stdout.write(f"   Name: {db_config.get('NAME', 'N/A')}")
        self.stdout.write(f"   Host: {db_config.get('HOST', 'N/A')}")

        if 'sqlite' in db_config['ENGINE']:
            self.stdout.write(self.style.WARNING("   ⚠️  Using SQLite (development mode)"))
            self.stdout.write(self.style.WARNING("   ⚠️  Data will be lost on server restart!"))
        else:
            self.stdout.write(self.style.SUCCESS("   ✅ Using production database"))

        self.stdout.write("\n" + "-"*70 + "\n")

        # Check if tables exist
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name LIKE 'orders_%'
                """)
                tables = cursor.fetchall()

                self.stdout.write("📋 Database Tables:")
                if tables:
                    for table in tables:
                        self.stdout.write(f"   ✅ {table[0]}")
                else:
                    self.stdout.write(self.style.WARNING("   ⚠️  No tables found - migrations may not have run"))
        except Exception as e:
            # SQLite fallback
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'orders_%'")
                tables = cursor.fetchall()

                self.stdout.write("📋 Database Tables:")
                if tables:
                    for table in tables:
                        self.stdout.write(f"   ✅ {table[0]}")
                else:
                    self.stdout.write(self.style.WARNING("   ⚠️  No tables found"))
            except Exception as e2:
                self.stdout.write(self.style.ERROR(f"   ❌ Error checking tables: {str(e2)}"))

        self.stdout.write("\n" + "-"*70 + "\n")

        # Check CallHistory records
        try:
            total_calls = CallHistory.objects.count()
            self.stdout.write(f"📞 CallHistory Records: {total_calls}")

            if total_calls > 0:
                # Latest call
                latest_call = CallHistory.objects.order_by('-created_at').first()
                self.stdout.write("\n📊 Latest Call:")
                self.stdout.write(f"   AWB: {latest_call.awb}")
                self.stdout.write(f"   Phone: {latest_call.customer_phone}")
                self.stdout.write(f"   Status: {latest_call.status}")
                self.stdout.write(f"   Ended Reason: {latest_call.ended_reason}")
                self.stdout.write(f"   Success: {latest_call.is_successful}")
                self.stdout.write(f"   Created: {latest_call.created_at}")

                # Count by status
                from django.db.models import Count
                status_counts = CallHistory.objects.values('ended_reason').annotate(count=Count('id'))

                self.stdout.write("\n📈 Calls by Ended Reason:")
                for item in status_counts:
                    reason = item['ended_reason'] or 'Pending'
                    count = item['count']
                    self.stdout.write(f"   {reason}: {count}")

                # Today's calls
                from datetime import datetime, time
                today_start = datetime.combine(datetime.now().date(), time.min)
                today_calls = CallHistory.objects.filter(created_at__gte=today_start).count()
                self.stdout.write(f"\n📅 Today's Calls: {today_calls}")

            else:
                self.stdout.write(self.style.WARNING("   ⚠️  No call records found in database"))
                self.stdout.write(self.style.WARNING("   ⚠️  Make sure to trigger some calls first"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error querying CallHistory: {str(e)}"))

        self.stdout.write("\n" + "-"*70 + "\n")

        # Check Order records
        try:
            total_orders = Order.objects.count()
            self.stdout.write(f"📦 Order Records: {total_orders}")

            if total_orders > 0:
                ofd_count = Order.objects.filter(order_type='OFD').count()
                undelivered_count = Order.objects.filter(order_type='Undelivered').count()

                self.stdout.write(f"   OFD: {ofd_count}")
                self.stdout.write(f"   Undelivered: {undelivered_count}")
            else:
                self.stdout.write(self.style.WARNING("   ⚠️  No order records cached"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error querying Orders: {str(e)}"))

        self.stdout.write("\n" + "="*70)
        self.stdout.write("DIAGNOSTIC CHECK COMPLETE")
        self.stdout.write("="*70 + "\n")
