from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from celebs import wiki
from celebs.models import Celebrity


class Command(BaseCommand):
    help = "Recalcule la popularité Wikipédia (fr + en, 60 jours). Idéal en tâche planifiée."

    def add_arguments(self, parser):
        parser.add_argument("--older-than", type=int, default=0, metavar="JOURS",
                            help="seulement les fiches pas mises à jour depuis N jours")
        parser.add_argument("--zero", action="store_true", help="seulement les popularités à 0")
        parser.add_argument("--reidentify", action="store_true",
                            help="oublie les titres Wikipédia mémorisés et ré-identifie tout le monde")

    def handle(self, *args, **opts):
        qs = Celebrity.objects.all()
        if opts["older_than"]:
            limit = timezone.now() - timedelta(days=opts["older_than"])
            qs = qs.filter(Q(popularity_updated_at__isnull=True) | Q(popularity_updated_at__lt=limit))
        if opts["zero"]:
            qs = qs.filter(popularity_score=0)
        celebs = list(qs)
        if opts["reidentify"]:
            for c in celebs:
                c.wiki_title_fr = c.wiki_title_en = ""
        self.stdout.write(f"{len(celebs)} célébrités à traiter…")
        failed = 0
        for i in range(0, len(celebs), 8):
            chunk = celebs[i:i + 8]
            res = wiki.refresh_many(chunk)
            for c in chunk:
                score = res.get(c.pk)
                if score is None:
                    failed += 1
                self.stdout.write(f"  {c.name:<40} {'ERREUR' if score is None else int(score)}")
        self.stdout.write(self.style.SUCCESS(f"Terminé ({failed} erreur(s))."))
