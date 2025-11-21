from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'

    def ready(self):
        """Start scheduler automatically when Django app starts"""
        import os
        # Only run in main process (not in reloader)
        if os.environ.get('RUN_MAIN') == 'true' or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            from .scheduler import auto_call_scheduler
            # Start scheduler automatically in hourly mode
            auto_call_scheduler.start_hourly_scheduler()
            print("[STARTUP] Auto Call Scheduler started automatically!")
