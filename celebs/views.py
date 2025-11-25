from django.shortcuts import render, redirect, get_object_or_404
from .models import Celebrity, CelebritySighting, Activity, Category
from .forms import CelebrityForm, CelebritySightingForm, ActivityForm
from .utils import get_wikipedia_popularity
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
import unicodedata
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.db.models import Min


def add_celebrity(request):
    if request.method == "POST":
        form = CelebrityForm(request.POST, request.FILES)
        sighting_form = CelebritySightingForm(request.POST, request.FILES)
        celebrity_id = request.POST.get('celebrity_id')

        if form.is_valid() and sighting_form.is_valid():
            if celebrity_id:
                celebrity = Celebrity.objects.get(id=celebrity_id)
            else:
                celebrity_name = form.cleaned_data['name'].strip()
                celebrity, created = Celebrity.objects.get_or_create(name=celebrity_name)
                if created:
                    celebrity.image = form.cleaned_data.get('image')
                    celebrity.popularity_score = get_wikipedia_popularity(celebrity.name)
                    celebrity.save()

            # Ajout ou mise à jour des activités même si la célébrité existait déjà
            activities_names = request.POST.get("activities", "").split(",")
            for name in activities_names:
                if name:
                    activity, _ = Activity.objects.get_or_create(name=name.strip())
                    celebrity.activities.add(activity)

            sighting = sighting_form.save(commit=False)
            sighting.celebrity = celebrity
            sighting.save()

            messages.success(request, f"{celebrity.name} bien ajouté à la liste !")
            return redirect("celebrity_list")
    else:
        form = CelebrityForm()
        sighting_form = CelebritySightingForm()

    return render(request, "celebs/add_celebrity.html", {
        "form": form,
        "sighting_form": sighting_form
    })


def celebrity_edit(request, celebrity_id):
    celebrity = get_object_or_404(Celebrity, id=celebrity_id)

    if request.method == "POST":
        form = CelebrityForm(request.POST, request.FILES, instance=celebrity)
        if form.is_valid():
            celeb = form.save()

            # On efface les activités existantes avant de les mettre à jour
            celeb.activities.clear()

            # Récupérer et nettoyer les noms d'activités
            activities_names = request.POST.get("activities", "").split(",")
            for name in activities_names:
                name = name.strip()  # Retirer les espaces inutiles
                if name:  # Vérifier que le nom de l'activité n'est pas vide
                    activity, created = Activity.objects.get_or_create(name=name)
                    celeb.activities.add(activity)

            return redirect('celebrity_detail', celeb_id=celeb.id)
    else:
        form = CelebrityForm(instance=celebrity)
        # Pré-remplir le champ caché des activités avec les activités actuelles
        initial_activities = ",".join(celebrity.activities.values_list('name', flat=True))
        form.fields['activities'].initial = initial_activities

    return render(request, 'celebs/celebrity_edit.html', {
        'form': form,
        'celebrity': celebrity
    })


def remove_accents(text):
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


def celebrity_list(request):
    categories = Category.objects.all()
    activities = Activity.objects.all()

    selected_category = request.GET.get("category")
    selected_activities = request.GET.getlist("activities[]")
    sort_by = request.GET.get("sort", "name")

    queryset = Celebrity.objects.all().prefetch_related("sightings", "activities")

    if selected_category:
        queryset = queryset.filter(activities__category_id=selected_category)

    if selected_activities:
        queryset = queryset.filter(activities__id__in=selected_activities)

    if selected_category or selected_activities:
        queryset = queryset.distinct()

    allowed_sorts = ["name", "-name", "popularity_score", "-popularity_score", "activities", "-activities"]

    if sort_by in allowed_sorts:
        reverse = sort_by.startswith('-')

        if "activities" in sort_by:
            # Tri côté Python mais sur l'ensemble du queryset filtré
            queryset = sorted(
                queryset,
                key=lambda c: remove_accents(c.activities.first().name if c.activities.exists() else "").lower(),
                reverse=reverse
            )
        else:
            queryset = queryset.order_by(sort_by)

    per_page_options = [50, 100, 150, 200, 250, 300, 1000]
    try:
        per_page = int(request.GET.get('per_page', 50))
        if per_page <= 0:
            per_page = 50
    except (ValueError, TypeError):
        per_page = 50

    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page', 1)
    celebrities = paginator.get_page(page_number)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        list_html = render_to_string("partials/celebrity_list_items.html", {"celebrities": celebrities})
        pagination_html = render_to_string(
            "partials/celebrity_pagination.html",
            {
                "celebrities": celebrities,
                "sort_by": sort_by,
                "per_page": per_page,
                "per_page_options": per_page_options
            }
        )
        return JsonResponse({"items": list_html, "pagination": pagination_html})

    return render(request, "celebs/celebrity_list.html", {
        "categories": categories,
        "activities": activities,
        "celebrities": celebrities,
        "sort_by": sort_by,
        "per_page_options": per_page_options,
        "current_per_page": per_page,
    })


def celebrity_detail(request, celeb_id):
    celebrity = get_object_or_404(Celebrity, id=celeb_id)
    return render(request, "celebs/celebrity_detail.html", {"celebrity": celebrity})


@require_POST
def celebrity_delete(request, celebrity_id):
    celebrity = get_object_or_404(Celebrity, id=celebrity_id)
    celebrity.delete()
    return redirect('celebrity_list')


def activity_list(request):
    activities = Activity.objects.all()

    if request.method == "POST":
        form = ActivityForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("activity_list")
    else:
        form = ActivityForm()

    return render(request, "celebs/activity_list.html", {
        "activities": activities,
        "form": form
    })


def search_activities(request):
    query = request.GET.get("q", "")
    activities = Activity.objects.filter(name__icontains=query)
    activity_names = list(activities.values_list("name", flat=True))
    return JsonResponse({"activities": activity_names})


def delete_activity(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    if request.method == "POST":
        activity.delete()
        return redirect("activity_list")


def activity_edit(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    if request.method == "POST":
        form = ActivityForm(request.POST, instance=activity)
        if form.is_valid():
            form.save()
            return redirect("activity_list")
    else:
        form = ActivityForm(instance=activity)

    return render(request, "celebs/activity_edit.html", {
        "form": form,
        "activity": activity,
    })


def check_celebrity_exists(request):
    name = request.GET.get('name')
    if name:
        exists = Celebrity.objects.filter(name__iexact=name).exists()
        if exists:
            celebrity = Celebrity.objects.get(name__iexact=name)
            return JsonResponse({'exists': True, 'celebrity_id': celebrity.id, 'count': celebrity.sightings.count()})
    return JsonResponse({'exists': False})


def edit_celebrity_sighting(request, sighting_id):
    sighting = get_object_or_404(CelebritySighting, id=sighting_id)
    if request.method == "POST":
        form = CelebritySightingForm(request.POST, instance=sighting)
        if form.is_valid():
            form.save()
            return redirect('celebrity_detail', celeb_id=sighting.celebrity.id)
    else:
        form = CelebritySightingForm(instance=sighting)
    return render(request, 'celebs/edit_celebrity_sighting.html', {'form': form, 'sighting': sighting})


@require_POST
def delete_celebrity_sighting(request, sighting_id):
    sighting = get_object_or_404(CelebritySighting, id=sighting_id)
    celebrity_id = sighting.celebrity.id
    sighting.delete()
    return redirect('celebrity_detail', celeb_id=celebrity_id)


def update_popularity(request, celebrity_id):
    celebrity = get_object_or_404(Celebrity, id=celebrity_id)

    if request.method == "POST":
        new_score = get_wikipedia_popularity(celebrity.name)
        celebrity.popularity_score = new_score
        celebrity.save()
        messages.success(request, f"Popularité mise à jour : {new_score}")

    return redirect("celebrity_detail", celeb_id=celebrity.id)


@require_POST
def update_popularity_step(request):
    """
    Met à jour la popularité d'une célébrité donnée par son ID.
    Le front enverra : { celeb_id: X }
    """
    celeb_id = request.POST.get("celeb_id")

    if not celeb_id:
        return JsonResponse({"error": "No celeb_id provided"}, status=400)

    try:
        celeb = Celebrity.objects.get(id=celeb_id)
    except Celebrity.DoesNotExist:
        return JsonResponse({"error": "Celebrity not found"}, status=404)

    new_score = get_wikipedia_popularity(celeb.name)
    celeb.popularity_score = new_score
    celeb.save()

    return JsonResponse({
        "success": True,
        "celeb_id": celeb.id,
        "new_score": new_score
    })


def all_celeb_ids(request):
    ids = list(Celebrity.objects.values_list("id", flat=True))
    return JsonResponse({"ids": ids})