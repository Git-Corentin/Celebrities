import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from celebs import sync


class Command(BaseCommand):
    help = "Remplace les données celebs locales par data/celebs.json (après un git pull)."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", help="fichier JSON (défaut : data/celebs.json)")
        parser.add_argument("--no-backup", action="store_true")

    def handle(self, *args, **opts):
        db = Path(settings.DATABASES["default"]["NAME"])
        if not opts["no_backup"] and db.exists():
            backup = db.with_name(f"{db.stem}.backup-{datetime.now():%Y%m%d-%H%M%S}{db.suffix}")
            shutil.copy2(db, backup)
            self.stdout.write(f"Sauvegarde : {backup.name}")
        n = sync.import_data(opts["path"])
        self.stdout.write(self.style.SUCCESS(f"{n} objets importés."))
