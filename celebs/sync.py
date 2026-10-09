"""
Synchronisation des données avec git.

Principe : la base SQLite (fichier binaire, impossible à fusionner) ne va plus
dans git. À la place, toutes les données de l'app sont exportées dans
data/celebs.json — un fichier texte trié, lisible et fusionnable par git.

  Site (PythonAnywhere)                      PC (PyCharm)
  ─────────────────────                      ────────────
  modif. sur le site (connecté)
  → bouton « Synchroniser vers git »
    = export JSON + git commit + git push ─→ git pull
                                             python manage.py import_celebs
"""
import json
import subprocess
from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.db import transaction

from .models import Activity, Category, Celebrity, CelebritySighting

MODELS = [Category, Activity, Celebrity, CelebritySighting]  # ordre des dépendances


def export_data(path=None):
    path = Path(path or settings.CELEBS_EXPORT_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    objects = []
    for model in MODELS:
        objects.extend(model.objects.order_by("pk"))
    text = serializers.serialize("json", objects, indent=2, ensure_ascii=False)
    # Fin de ligne finale : diffs git propres
    new = text.rstrip() + "\n"
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if new != old:
        path.write_text(new, encoding="utf-8")
    counts = {m._meta.model_name: m.objects.count() for m in MODELS}
    return path, new != old, counts


@transaction.atomic
def import_data(path=None):
    """Remplace les données celebs locales par le contenu du fichier JSON."""
    path = Path(path or settings.CELEBS_EXPORT_FILE)
    raw = path.read_text(encoding="utf-8")
    json.loads(raw)  # validation avant de toucher à la base
    for model in reversed(MODELS):
        model.objects.all().delete()
    count = 0
    for obj in serializers.deserialize("json", raw):
        obj.save()  # sauvegarde brute : pas de logique save(), pas de miniature recalculée
        count += 1
    return count


def _git(*args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=90,
    )


def git_sync(message="Mise à jour des données celebs depuis le site", push=True):
    """Export + git add (données + photos) + commit + push. Renvoie (ok, texte)."""
    root = Path(settings.BASE_DIR)
    path, changed, counts = export_data()
    media = Path(settings.MEDIA_ROOT) / "celebs"
    log = []
    to_add = [str(path.relative_to(root))]
    if media.exists():
        try:
            to_add.append(str(media.relative_to(root)))
        except ValueError:
            pass
    r = _git("add", "--", to_add[0], cwd=root)
    if r.returncode:
        return False, r.stderr.strip() or "git add a échoué"
    if len(to_add) > 1 and _git("add", "--", to_add[1], cwd=root).returncode:
        to_add = to_add[:1]  # photos ignorées par .gitignore : on n'envoie que les données
        log.append("Photos non versionnées (ignorées par .gitignore).")
    r = _git("diff", "--cached", "--quiet", cwd=root)
    if r.returncode == 0:
        log.append("Rien de nouveau à committer.")
    else:
        summary = ", ".join(f"{v} {k}" for k, v in counts.items())
        r = _git("commit", "-m", f"{message}\n\n{summary}", "--", *to_add, cwd=root)
        if r.returncode:
            return False, r.stderr.strip() or r.stdout.strip()
        log.append("Commit créé.")
    if push:
        # Récupère d'abord les commits faits ailleurs (code poussé depuis PyCharm).
        r = _git("pull", "--rebase", "--autostash", cwd=root)
        if r.returncode:
            _git("rebase", "--abort", cwd=root)
            return False, "Commit local fait, mais git pull a échoué (conflit ?) : " + (r.stderr.strip() or r.stdout.strip())
        r = _git("push", cwd=root)
        if r.returncode:
            return False, "Commit local fait, mais le push a échoué : " + (r.stderr.strip() or r.stdout.strip())
        log.append("Envoyé sur le dépôt distant.")
    return True, " ".join(log)
