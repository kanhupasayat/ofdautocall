from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'

    def ready(self):
        """Start scheduler automatically when Django app starts"""
        import os
        import sys
        import threading

        # Prevent running during migrations or in secondary processes
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return

        # Start scheduler in production (gunicorn) and development
        # Skip only in Django's auto-reloader process
        if os.environ.get('RUN_MAIN') != 'false':
            # Check database configuration
            def check_database_config():
                from django.conf import settings

                print("\n" + "="*70)
                print("Database Configuration Check:")
                print("="*70)

                database_url = os.environ.get('DATABASE_URL')
                db_engine = settings.DATABASES['default']['ENGINE']

                if database_url:
                    print(f"✅ DATABASE_URL is set: {database_url[:30]}...")
                else:
                    print("❌ DATABASE_URL is NOT set!")
                    print("⚠️  WARNING: Using SQLite fallback - data will be lost on restart!")

                if 'sqlite' in db_engine:
                    print(f"⚠️  WARNING: Using SQLite database: {db_engine}")
                    print("⚠️  This is OK for development, but NOT for production!")
                    print("⚠️  All data will be LOST when the server restarts!")
                    if not database_url:
                        print("")
                        print("To fix this in production:")
                        print("1. Create PostgreSQL database on Render")
                        print("2. Connect it to your web service")
                        print("3. Redeploy the application")
                else:
                    print(f"✅ Using production database: {db_engine}")

                print("="*70 + "\n")

            # Check VAPI environment variables
            def check_vapi_credentials():
                vapi_private_key = os.environ.get('VAPI_PRIVATE_KEY')
                vapi_phone_id = os.environ.get('VAPI_PHONE_NUMBER_ID')
                vapi_assistant_id = os.environ.get('VAPI_ASSISTANT_ID')

                print("\n" + "="*70)
                print("VAPI Credentials Check:")
                print("="*70)

                if vapi_private_key:
                    print(f"✅ VAPI_PRIVATE_KEY: {vapi_private_key[:10]}...")
                else:
                    print("❌ VAPI_PRIVATE_KEY: MISSING!")

                if vapi_phone_id:
                    print(f"✅ VAPI_PHONE_NUMBER_ID: {vapi_phone_id[:10]}...")
                else:
                    print("❌ VAPI_PHONE_NUMBER_ID: MISSING!")

                if vapi_assistant_id:
                    print(f"✅ VAPI_ASSISTANT_ID: {vapi_assistant_id[:10]}...")
                else:
                    print("❌ VAPI_ASSISTANT_ID: MISSING!")

                print("="*70 + "\n")

                if not all([vapi_private_key, vapi_phone_id, vapi_assistant_id]):
                    print("⚠️  WARNING: Some VAPI credentials are missing!")
                    print("⚠️  Calls will FAIL without proper credentials!")

            # Create superuser if it doesn't exist
            def create_superuser_if_needed():
                try:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    if not User.objects.filter(username='admin').exists():
                        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
                        print("[STARTUP] ✅ Superuser 'admin' created successfully!")
                    else:
                        print("[STARTUP] ℹ️ Superuser 'admin' already exists")
                except Exception as e:
                    print(f"[STARTUP] ⚠️ Failed to create superuser: {e}")

            # Start scheduler in background thread to avoid blocking startup
            def start_scheduler_background():
                from .scheduler import auto_call_scheduler
                auto_call_scheduler.start_hourly_scheduler()
                print("[STARTUP] ✅ Auto Call Scheduler started automatically!")

            # Check database configuration first
            check_database_config()

            # Check VAPI credentials
            check_vapi_credentials()

            # Create superuser (quick operation)
            create_superuser_if_needed()

            # Run scheduler in daemon thread so it doesn't block gunicorn startup
            scheduler_thread = threading.Thread(target=start_scheduler_background, daemon=True)
            scheduler_thread.start()
            print("[STARTUP] 🚀 Scheduler starting in background thread...")
