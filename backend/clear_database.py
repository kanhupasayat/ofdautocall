"""
Script to clear all data from database tables
Run this with: python manage.py shell < clear_database.py
"""

from orders.models import Order, CallHistory

print("Clearing database...")

# Delete all CallHistory records
call_count = CallHistory.objects.all().count()
CallHistory.objects.all().delete()
print(f"Deleted {call_count} CallHistory records")

# Delete all Order records
order_count = Order.objects.all().count()
Order.objects.all().delete()
print(f"Deleted {order_count} Order records")

print("\nDatabase cleared successfully!")
print("All old data has been removed. New data will be synced on next scheduler run.")
