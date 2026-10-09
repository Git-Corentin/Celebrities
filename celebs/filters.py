"""Filtrage et tri de la liste — partagé par la page HTML et les réponses AJAX."""
from dataclasses import dataclass, field
from datetime import date

from django.db.models import Count, F, Max, Min, Prefetch, Q

from .models import Activity, Celebrity, CelebritySighting
from .text import normalize

SORTS = {
    "name": ("Nom", "name_key"),
    "pop": ("Popularité", "popularity_score"),
    "seen": ("Dernière rencontre", "last_seen"),
    "count": ("Nb de rencontres", "n_sightings"),
    "act": ("Activité", None),  # tri Python (accents)
    "added": ("Ajout", "id"),
}
DEFAULT_DIR = {"name": "", "pop": "-", "seen": "-", "count": "-", "act": "", "added": "-"}
SORT_OPTIONS = [
    ("name", "Nom, de A à Z"),
    ("-name", "Nom, de Z à A"),
    ("-pop", "Les plus connus"),
    ("pop", "Les moins connus"),
    ("-seen", "Rencontre la plus récente"),
    ("seen", "Rencontre la plus ancienne"),
    ("-count", "Le plus de rencontres"),
    ("act", "Activité"),
    ("-added", "Ajout le plus récent"),
]
PER_PAGE = [25, 50, 100, 200, 500]


def _ints(values):
    out = []
    for v in values:
        try:
            out.append(int(v))
        except (TypeError, ValueError):
            pass
    return out


def _date(value):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


@dataclass
class ListParams:
    q: str = ""
    categories: list = field(default_factory=list)
    activities: list = field(default_factory=list)
    location: str = ""
    date_from: date = None
    date_to: date = None
    year: int = None
    no_photo: bool = False
    sort: str = "name"
    desc: bool = False
    per_page: int = 50
    page: str = "1"
    view: str = "table"

    @classmethod
    def from_request(cls, request):
        g = request.GET
        sort = g.get("sort", "name")
        desc = sort.startswith("-")
        sort = sort.lstrip("-")
        if sort not in SORTS:
            sort, desc = "name", False
        try:
            per = int(g.get("per", 50))
        except ValueError:
            per = 50
        year = _ints([g.get("year")])
        return cls(
            q=g.get("q", "").strip(),
            categories=_ints(g.getlist("cat")),
            activities=_ints(g.getlist("act")),
            location=g.get("loc", "").strip(),
            date_from=_date(g.get("from")),
            date_to=_date(g.get("to")),
            year=year[0] if year else None,
            no_photo=g.get("nophoto") == "1",
            sort=sort,
            desc=desc,
            per_page=per if per in PER_PAGE else 50,
            page=g.get("page", "1"),
            view="grid" if g.get("view") == "grid" else "table",
        )

    @property
    def sort_param(self):
        return ("-" if self.desc else "") + self.sort

    @property
    def sighting_filtered(self):
        return bool(self.location or self.date_from or self.date_to or self.year)

    @property
    def active_count(self):
        return sum([
            bool(self.q), bool(self.categories), bool(self.activities), bool(self.location),
            bool(self.date_from or self.date_to), bool(self.year), self.no_photo,
        ])


def matching_locations(text):
    """Recherche de lieu insensible aux accents et à la casse."""
    needle = normalize(text)
    locations = CelebritySighting.objects.exclude(location__isnull=True).exclude(location="")
    return [loc for loc in locations.values_list("location", flat=True).distinct() if needle in normalize(loc)]


def sightings_queryset(p):
    qs = CelebritySighting.objects.all()
    if p.location:
        qs = qs.filter(location__in=matching_locations(p.location))
    if p.date_from:
        qs = qs.filter(date_seen__gte=p.date_from)
    if p.date_to:
        qs = qs.filter(date_seen__lte=p.date_to)
    if p.year:
        qs = qs.filter(date_seen__year=p.year)
    return qs


def ordered_ids(p):
    """Renvoie la liste ordonnée des id correspondant aux filtres (léger : pas d'objets complets)."""
    qs = Celebrity.objects.all()
    if p.q:
        needle = normalize(p.q)
        act_ids = [a.pk for a in Activity.objects.only("id", "name") if needle in normalize(a.name)]
        qs = qs.filter(Q(name_key__contains=needle) | Q(activities__in=act_ids))
    if p.categories:
        qs = qs.filter(activities__category__in=p.categories)
    if p.activities:
        qs = qs.filter(activities__in=p.activities)
    if p.sighting_filtered:
        qs = qs.filter(pk__in=sightings_queryset(p).values("celebrity_id"))
    if p.no_photo:
        qs = qs.filter(Q(image="") | Q(image__isnull=True))

    ids = qs.values("pk").distinct()
    base = Celebrity.objects.filter(pk__in=ids)

    if p.sort == "act":
        rows = base.annotate(first_act=Min("activities__name")).values_list("pk", "first_act", "name_key")
        rows = sorted(rows, key=lambda r: (r[1] is None, normalize(r[1] or ""), r[2]), reverse=False)
        if p.desc:
            with_act = [r for r in rows if r[1] is not None][::-1]
            rows = with_act + [r for r in rows if r[1] is None]
        return [r[0] for r in rows]

    field_name = SORTS[p.sort][1]
    base = base.annotate(last_seen=Max("sightings__date_seen"), n_sightings=Count("sightings", distinct=True))
    expr = F(field_name).desc(nulls_last=True) if p.desc else F(field_name).asc(nulls_last=True)
    return list(base.order_by(expr, "name_key").values_list("pk", flat=True))


def load_page(ids, p):
    """Charge uniquement les objets de la page affichée, avec tout ce qu'il faut en 3 requêtes."""
    shown = sightings_queryset(p) if p.sighting_filtered else CelebritySighting.objects.all()
    objs = (
        Celebrity.objects.filter(pk__in=ids)
        .annotate(n_sightings=Count("sightings", distinct=True), last_seen=Max("sightings__date_seen"))
        .prefetch_related(
            Prefetch("activities", queryset=Activity.objects.select_related("category")),
            Prefetch("sightings", queryset=shown.order_by(F("date_seen").desc(nulls_last=True), "-id"),
                     to_attr="shown_sightings"),
        )
    )
    by_id = {o.pk: o for o in objs}
    return [by_id[i] for i in ids if i in by_id]
