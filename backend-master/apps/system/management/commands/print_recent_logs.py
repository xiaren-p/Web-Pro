from django.core.management.base import BaseCommand
from apps.system.models import OperLog


class Command(BaseCommand):
    """自定义管理命令。"""
    help = "Print recent operation logs with elapsed time"

    def add_arguments(self, parser):
        """add_arguments。"""
        parser.add_argument('--limit', type=int, default=100, help='Number of rows to print')

    def handle(self, *args, **options):
        """命令处理入口。"""
        limit = options.get('limit') or 100
        qs = OperLog.objects.order_by('-id')[:limit]
        self.stdout.write("ID\tCreatedAt\tModule\tAction\tResult\tElapsed(ms)")
        for o in qs:
            self.stdout.write(f"{o.id}\t{o.created_at:%Y-%m-%d %H:%M:%S}\t{o.module}\t{o.action}\t{o.result}\t{o.elapsed_ms}")
