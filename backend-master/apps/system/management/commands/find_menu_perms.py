from django.core.management.base import BaseCommand
from apps.system.models import Menu


class Command(BaseCommand):
    """自定义管理命令。"""
    help = "Find menus by permission token substring"

    def add_arguments(self, parser):
        """add_arguments。"""
        parser.add_argument('token', nargs='?', default='notice')

    def handle(self, *args, **options):
        """命令处理入口。"""
        token = options.get('token')
        qs = Menu.objects.filter(perms__icontains=token)
        for m in qs:
            self.stdout.write(f"id={m.id} name={m.name} perms={m.perms}")
        if not qs.exists():
            self.stdout.write("no matches")
