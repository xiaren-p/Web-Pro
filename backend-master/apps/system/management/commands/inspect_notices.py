from django.core.management.base import BaseCommand
from apps.system.models import Notice
from apps.system.serializers import NoticeBriefSerializer, NoticeDetailSerializer


class Command(BaseCommand):
    help = "Inspect notices and print sample serialized outputs"

    def handle(self, *args, **options):
        qs = Notice.objects.all().order_by('-id')
        self.stdout.write(f"total={qs.count()}")
        first = qs.first()
        if not first:
            self.stdout.write("no notices")
            return
        self.stdout.write("--- brief ---")
        self.stdout.write(str(NoticeBriefSerializer(first).data))
        self.stdout.write("--- detail ---")
        self.stdout.write(str(NoticeDetailSerializer(first).data))
