from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Max, Prefetch, Q
from django.db.models.functions import ExtractYear
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from . import filters, sync, wiki
from .forms import ActivityForm, CategoryForm, CelebrityForm, SightingForm
from .models import Activity, Category, Celebrity, CelebritySighting
from .text import normalize


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _known_locations():
    return (
        CelebritySighting.objects.exclude(location__isnull=True).exclude(location="")
        .values("location").annotate(n=Count("id")).order_by("-n", "location")
        .values_list("location", flat=True)[:400]
    )


# ───────────────────────────── Liste ─────────────────────────────

def celebrity_list(request):
    p = filters.ListParams.from_request(request)
    ids = filters.ordered_ids(p)
    paginator = Paginator(ids, p.per_page)
    page = paginator.get_page(p.page)
    celebrities = filters.load_page(list(page.object_list), p)
    max_pop = Celebrity.objects.aggregate(m=Max("popularity_score"))["m"] or 0

    ctx = {
        "p": p,
        "page": page,
        "celebrities": celebrities,
        "page_range": paginator.get_elided_page_range(page.number, on_each_side=2, on_ends=1),
        "result_count": paginator.count,
        "max_pop": max_pop,
        "sort_options": filters.SORT_OPTIONS,
        "per_page_options": filters.PER_PAGE,
        "query_base": _query_without(request, "page"),
    }
    if _is_ajax(request):
        return JsonResponse({
            "results": render_to_string("celebs/partials/results.html", ctx, request=request),
            "count": paginator.count,
            "ids": ids if request.GET.get("with_ids") else None,
        })

    categories = Category.objects.prefetch_related(
        Prefetch("activity_set", queryset=Activity.objects.annotate(n=Count("celebrities")).order_by("name"))
    )
    orphan_activities = Activity.objects.filter(category__isnull=True).annotate(n=Count("celebrities"))
    years = (
        CelebritySighting.objects.exclude(date_seen__isnull=True)
        .annotate(y=ExtractYear("date_seen")).values_list("y", flat=True).distinct().order_by("-y")
    )
    ctx.update({
        "categories": categories,
        "orphan_activities": orphan_activities,
        "years": years,
        "locations": _known_locations(),
        "stats": {
            "celebs": Celebrity.objects.count(),
            "sightings": CelebritySighting.objects.count(),
            "places": CelebritySighting.objects.exclude(location__isnull=True).exclude(location="")
                      .values("location").distinct().count(),
        },
    })
    return render(request, "celebs/celebrity_list.html", ctx)


def _query_without(request, *keys):
    q = request.GET.copy()
    for k in keys:
        q.pop(k, None)
    return q.urlencode()


# ───────────────────────────── Fiche ─────────────────────────────

def celebrity_detail(request, celeb_id):
    celebrity = get_object_or_404(
        Celebrity.objects.prefetch_related(
            Prefetch("activities", queryset=Activity.objects.select_related("category"))
        ),
        id=celeb_id,
    )
    sightings = celebrity.sightings.all()
    return render(request, "celebs/celebrity_detail.html", {
        "celebrity": celebrity,
        "sightings": sightings,
        "sighting_form": SightingForm(),
        "locations": _known_locations(),
    })


@login_required
def add_celebrity(request):
    """
    Une seule page pour deux cas :
    - nom inconnu → nouvelle célébrité + première rencontre ;
    - nom déjà connu → on ajoute juste une rencontre à la fiche existante.
    """
    existing = None
    if request.method == "POST":
        existing_id = request.POST.get("existing_id")
        if existing_id:
            existing = Celebrity.objects.filter(pk=existing_id).first()
        form = CelebrityForm(request.POST, request.FILES, instance=None)
        sighting_form = SightingForm(request.POST)

        if existing is not None:
            if sighting_form.is_valid():
                s = sighting_form.save(commit=False)
                s.celebrity = existing
                s.save()
                n = existing.sightings.count()
                messages.success(request, f"Rencontre n°{n} avec {existing.name} ajoutée.")
                return redirect(existing)
        elif form.is_valid() and sighting_form.is_valid():
            try:
                celeb = form.save()
            except (ValueError, OSError) as exc:
                form.add_error(None, f"Impossible de récupérer la photo : {exc}")
            else:
                s = sighting_form.save(commit=False)
                s.celebrity = celeb
                s.save()
                try:
                    wiki.refresh_popularity(celeb)
                except Exception:
                    messages.warning(request, "Popularité non calculée (Wikipédia injoignable) — réessayez plus tard.")
                messages.success(request, f"{celeb.name} ajouté·e au carnet.")
                if request.POST.get("again"):
                    return redirect("add_celebrity")
                return redirect(celeb)
    else:
        form = CelebrityForm()
        sighting_form = SightingForm()

    return render(request, "celebs/celebrity_form.html", {
        "form": form,
        "sighting_form": sighting_form,
        "existing": existing,
        "locations": _known_locations(),
        "mode": "add",
    })


@login_required
def celebrity_edit(request, celebrity_id):
    celebrity = get_object_or_404(Celebrity, id=celebrity_id)
    if request.method == "POST":
        form = CelebrityForm(request.POST, request.FILES, instance=celebrity)
        if form.is_valid():
            try:
                celeb = form.save()
            except (ValueError, OSError) as exc:
                form.add_error(None, f"Impossible de récupérer la photo : {exc}")
            else:
                if not (celeb.wiki_title_fr or celeb.wiki_title_en):
                    try:
                        wiki.refresh_popularity(celeb)
                    except Exception:
                        pass
                messages.success(request, "Modifications enregistrées.")
                return redirect(celeb)
    else:
        form = CelebrityForm(instance=celebrity)
    return render(request, "celebs/celebrity_form.html", {
        "form": form,
        "celebrity": celebrity,
        "mode": "edit",
    })


@login_required
@require_POST
def celebrity_delete(request, celebrity_id):
    celebrity = get_object_or_404(Celebrity, id=celebrity_id)
    name = celebrity.name
    for f in (celebrity.image, celebrity.thumbnail):
        if f:
            f.delete(save=False)
    celebrity.delete()
    messages.success(request, f"{name} a été supprimé·e.")
    return redirect("celebrity_list")


# ─────────────────────────── Rencontres ───────────────────────────

@login_required
@require_POST
def add_sighting(request, celeb_id):
    celebrity = get_object_or_404(Celebrity, id=celeb_id)
    form = SightingForm(request.POST)
    if form.is_valid():
        s = form.save(commit=False)
        s.celebrity = celebrity
        s.save()
        messages.success(request, "Rencontre ajoutée.")
    else:
        messages.error(request, "Rencontre invalide : " + form.errors.as_text())
    return redirect(celebrity)


@login_required
def edit_celebrity_sighting(request, sighting_id):
    sighting = get_object_or_404(CelebritySighting.objects.select_related("celebrity"), id=sighting_id)
    if request.method == "POST":
        form = SightingForm(request.POST, instance=sighting)
        if form.is_valid():
            form.save()
            messages.success(request, "Rencontre modifiée.")
            return redirect(sighting.celebrity)
    else:
        form = SightingForm(instance=sighting)
    return render(request, "celebs/sighting_form.html", {
        "form": form, "sighting": sighting, "locations": _known_locations(),
    })


@login_required
@require_POST
def delete_celebrity_sighting(request, sighting_id):
    sighting = get_object_or_404(CelebritySighting, id=sighting_id)
    celebrity = sighting.celebrity
    sighting.delete()
    messages.success(request, "Rencontre supprimée.")
    return redirect(celebrity)


# ─────────────────────────── Activités ───────────────────────────

def activity_list(request):
    form = ActivityForm()
    cat_form = CategoryForm()
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect(f"{reverse('celebs_login')}?next={request.path}")
        if "add_category" in request.POST:
            cat_form = CategoryForm(request.POST)
            if cat_form.is_valid():
                cat_form.save()
                messages.success(request, "Secteur ajouté.")
                return redirect("activity_list")
        else:
            form = ActivityForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Activité ajoutée.")
                return redirect("activity_list")

    activities = Activity.objects.select_related("category").annotate(n=Count("celebrities"))
    groups = {}
    for a in activities.order_by("category__name", "name"):
        groups.setdefault(a.category, []).append(a)
    ordered = sorted(groups.items(), key=lambda kv: (kv[0] is None, kv[0].name if kv[0] else ""))
    return render(request, "celebs/activity_list.html", {
        "groups": ordered,
        "form": form,
        "cat_form": cat_form,
        "total": activities.count(),
    })


@login_required
def activity_edit(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    if request.method == "POST":
        form = ActivityForm(request.POST, instance=activity)
        if form.is_valid():
            form.save()
            messages.success(request, "Activité modifiée.")
            return redirect("activity_list")
    else:
        form = ActivityForm(instance=activity)
    return render(request, "celebs/activity_edit.html", {"form": form, "activity": activity})


@login_required
@require_POST
def delete_activity(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    activity.delete()
    messages.success(request, f"Activité « {activity.name} » supprimée.")
    return redirect("activity_list")


@require_POST
@login_required
def set_activity_category(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    cat_id = request.POST.get("category") or None
    activity.category = Category.objects.filter(pk=cat_id).first() if cat_id else None
    activity.save()
    return JsonResponse({"ok": True})


# ───────────────────────────── API JSON ─────────────────────────────

@require_GET
def search_activities(request):
    query = normalize(request.GET.get("q", ""))
    acts = Activity.objects.select_related("category").annotate(n=Count("celebrities")).order_by("-n", "name")
    out = [
        {"name": a.name, "category": a.category.name if a.category else "", "n": a.n}
        for a in acts if query in normalize(a.name)
    ][:12]
    return JsonResponse({"activities": [a["name"] for a in out], "items": out})


@require_GET
def check_celebrity_exists(request):
    """Correspondance exacte (sans accents/casse) + noms proches pour éviter les doublons."""
    key = normalize(request.GET.get("name", ""))
    if len(key) < 2:
        return JsonResponse({"exists": False, "similar": []})
    exact = Celebrity.objects.filter(name_key=key).annotate(n=Count("sightings")).first()
    similar = []
    if not exact:
        words = [w for w in key.split() if len(w) > 2]
        q = Q(name_key__startswith=key)
        for w in words:
            q |= Q(name_key__contains=w)
        similar = [
            {"id": c.pk, "name": c.name, "url": c.get_absolute_url()}
            for c in Celebrity.objects.filter(q)[:5]
        ]
    if exact:
        return JsonResponse({
            "exists": True, "celebrity_id": exact.pk, "name": exact.name, "count": exact.n,
            "url": exact.get_absolute_url(), "avatar": exact.avatar_url,
        })
    return JsonResponse({"exists": False, "similar": similar})


@login_required
@require_GET
def image_suggestions(request):
    name = request.GET.get("name", "").strip()
    if len(name) < 3:
        return JsonResponse({"results": []})
    return JsonResponse(wiki.image_suggestions(name))


@login_required
@require_POST
def update_popularity(request, celebrity_id):
    celebrity = get_object_or_404(Celebrity, id=celebrity_id)
    try:
        score = wiki.refresh_popularity(celebrity)
        messages.success(request, f"Popularité mise à jour : {int(score):,} vues sur 60 jours".replace(",", " "))
    except Exception:
        messages.error(request, "Wikipédia ne répond pas, réessayez dans un moment.")
    return redirect(celebrity)


@login_required
@require_POST
def update_popularity_batch(request):
    """Met à jour un petit lot (≤ 8) en parallèle ; le navigateur enchaîne les lots."""
    ids = []
    for v in request.POST.getlist("ids"):
        try:
            ids.append(int(v))
        except ValueError:
            pass
    celebs = list(Celebrity.objects.filter(pk__in=ids[:8]))
    results = wiki.refresh_many(celebs)
    return JsonResponse({
        "results": [
            {"id": pk, "score": score, "ok": score is not None}
            for pk, score in results.items()
        ]
    })


@login_required
@require_GET
def all_celeb_ids(request):
    qs = Celebrity.objects.order_by("popularity_updated_at", "pk")
    return JsonResponse({"ids": list(qs.values_list("id", flat=True))})


@login_required
@require_POST
def git_sync_view(request):
    from django.conf import settings
    if not settings.CELEBS_GIT_SYNC_ENABLED:
        messages.error(request, "La synchronisation git est désactivée sur ce serveur.")
    else:
        ok, text = sync.git_sync()
        (messages.success if ok else messages.error)(request, f"Synchronisation git : {text}")
    return redirect(request.POST.get("next") or "celebrity_list")
