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
            # Start scheduler in background thread to avoid blocking startup
            def start_scheduler_background():
                from .scheduler import auto_call_scheduler
                auto_call_scheduler.start_hourly_scheduler()
                print("[STARTUP] ✅ Auto Call Scheduler started automatically!")

            # Run in daemon thread so it doesn't block gunicorn startup
            scheduler_thread = threading.Thread(target=start_scheduler_background, daemon=True)
            scheduler_thread.start()
            print("[STARTUP] 🚀 Scheduler starting in background thread...")
