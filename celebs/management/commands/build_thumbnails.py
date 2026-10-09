from django.core.management.base import BaseCommand
from django.db.models import Q

from celebs.models import Celebrity


class Command(BaseCommand):
    help = "Génère les miniatures manquantes (à lancer une fois après la mise à jour)."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="regénère aussi les miniatures existantes")

    def handle(self, *args, **opts):
        qs = Celebrity.objects.exclude(image="").exclude(image__isnull=True)
        if not opts["all"]:
            qs = qs.filter(Q(thumbnail="") | Q(thumbnail__isnull=True))
        n = 0
        for c in qs:
            c.build_thumbnail()
            n += 1
        self.stdout.write(self.style.SUCCESS(f"{n} miniature(s) générée(s)."))
