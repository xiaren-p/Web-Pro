from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

try:
    from api_v1.models import OrderProfitCache
except Exception:
    OrderProfitCache = None


class Command(BaseCommand):
    help = 'Prune OrderProfitCache entries older than TTL minutes (default 10)'

    def add_arguments(self, parser):
        parser.add_argument('--minutes', type=int, default=10, help='TTL in minutes')
        parser.add_argument('--dry-run', action='store_true', help='Only show count, do not delete')

    def handle(self, *args, **options):
        minutes = int(options.get('minutes') or 10)
        dry_run = bool(options.get('dry_run'))
        if OrderProfitCache is None:
            self.stdout.write(self.style.WARNING('OrderProfitCache model not available'))
            return
        cutoff = timezone.now() - timedelta(minutes=minutes)
        qs = OrderProfitCache.objects.filter(created_at__lt=cutoff)
        count = qs.count()
        if dry_run:
            self.stdout.write(f'[dry-run] would delete {count} entries older than {minutes} minutes')
            return
        if count == 0:
            self.stdout.write('No entries to delete')
            return
        qs.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} OrderProfitCache entries older than {minutes} minutes'))
