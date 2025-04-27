from django.shortcuts import render, redirect, get_object_or_404
from .models import Celebrity, CelebritySighting, Activity
from .forms import CelebrityForm, CelebritySightingForm, ActivityForm
from .utils import get_wikipedia_popularity
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
import unicodedata


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
    celebrities = Celebrity.objects.prefetch_related('sightings', 'activities').all()

    sort_by = request.GET.get('sort', 'name')
    allowed_sorts = ['name', '-name', 'popularity_score', '-popularity_score', 'activities', '-activities']

    # Filtre activité
    activity_id = request.GET.get('activity')
    activities = Activity.objects.all()
    if activity_id:
        celebrities = celebrities.filter(activities__id=activity_id)

    # Tri spécifique
    if sort_by in allowed_sorts:
        if 'activities' in sort_by:
            reverse = sort_by.startswith('-')
            celebrities = sorted(
                celebrities,
                key=lambda c: remove_accents(c.activities.first().name) if c.activities.exists() else '',
                reverse=reverse
            )
        elif 'name' in sort_by:
            reverse = sort_by.startswith('-')
            celebrities = sorted(
                celebrities,
                key=lambda c: remove_accents(c.name).lower(),
                reverse=reverse
            )
        else:
            celebrities = celebrities.order_by(sort_by)

    # Colonnes affichées
    columns = [
        ("name", "Nom"),
        ("popularity_score", "Popularité"),
        ("activities", "Activités"),
    ]

    return render(request, "celebs/celebrity_list.html", {
        "celebrities": celebrities,
        "activities": activities,
        "selected_activity": int(activity_id) if activity_id else None,
        "sort_by": sort_by,
        "columns": columns,
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