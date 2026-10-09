from django.core.management.base import BaseCommand

from celebs import sync


class Command(BaseCommand):
    help = "Exporte les données celebs dans data/celebs.json (option : commit + push git)."

    def add_arguments(self, parser):
        parser.add_argument("--git", action="store_true", help="git add + commit + pull --rebase + push")
        parser.add_argument("--no-push", action="store_true", help="avec --git : commit sans push")

    def handle(self, *args, **opts):
        if opts["git"]:
            ok, text = sync.git_sync(push=not opts["no_push"])
            (self.stdout.write if ok else self.stderr.write)(text)
            if not ok:
                raise SystemExit(1)
            return
        path, changed, counts = sync.export_data()
        self.stdout.write(f"{path} {'mis à jour' if changed else 'inchangé'} — {counts}")
