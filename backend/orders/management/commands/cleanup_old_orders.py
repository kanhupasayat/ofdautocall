from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from orders.models import Order, CallHistory


class Command(BaseCommand):
    help = 'Delete old orders and call history - Run daily in morning'

    def handle(self, *args, **kwargs):
        # Delete ALL call history (fresh start every morning)
        call_deleted = CallHistory.objects.all().delete()[0]

        # Delete all OFD/Undelivered orders to force fresh sync
        order_deleted = Order.objects.filter(
            order_type__in=['OFD', 'Undelivered']
        ).delete()[0]

        self.stdout.write(
            self.style.SUCCESS(
                f'Morning cleanup complete! Deleted {order_deleted} orders, {call_deleted} call history records'
            )
        )
