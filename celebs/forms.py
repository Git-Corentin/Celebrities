from django import forms
from django.core.files.base import ContentFile
from django.utils.text import slugify

from .models import Activity, Category, Celebrity, CelebritySighting
from . import wiki


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        kwargs["format"] = "%Y-%m-%d"
        super().__init__(**kwargs)


class ActivitiesField(forms.CharField):
    """Liste d'activités séparées par des virgules (alimentée par le sélecteur JS)."""

    def clean(self, value):
        value = super().clean(value)
        names, seen = [], set()
        for raw in (value or "").split(","):
            name = " ".join(raw.split())
            if name and name.lower() not in seen:
                seen.add(name.lower())
                names.append(name)
        return names


def save_activities(celeb, names):
    """Associe les activités (créées si besoin) et retire celles qui ne sont plus listées."""
    existing = {a.name.lower(): a for a in Activity.objects.filter(name__in=names)}
    # name est unique mais sensible à la casse sous SQLite : on cherche aussi en iexact
    acts = []
    for name in names:
        act = existing.get(name.lower()) or Activity.objects.filter(name__iexact=name).first()
        if act is None:
            act = Activity.objects.create(name=name)
        acts.append(act)
    celeb.activities.set(acts)


class CelebrityForm(forms.ModelForm):
    # Champ texte visible (« Acteur, Humoriste ») : le JS le transforme en étiquettes ;
    # sans JS il reste utilisable et n'efface jamais les activités par erreur.
    activities = ActivitiesField(required=False, widget=forms.TextInput(attrs={"autocomplete": "off"}))
    image = forms.ImageField(required=False, widget=forms.FileInput(attrs={"accept": "image/*"}))
    image_url = forms.URLField(required=False, widget=forms.HiddenInput, assume_scheme="https")
    remove_image = forms.BooleanField(required=False, label="Supprimer la photo")

    class Meta:
        model = Celebrity
        fields = ["name", "image", "wikidata_id", "wiki_title_fr", "wiki_title_en"]
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "off", "placeholder": "Prénom Nom", "autofocus": True}),
            "wikidata_id": forms.TextInput(attrs={"placeholder": "Q12345"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and not self.is_bound:
            self.initial["activities"] = ",".join(self.instance.activities.values_list("name", flat=True))

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if not name:
            raise forms.ValidationError("Le nom est obligatoire.")
        return name

    def clean_wikidata_id(self):
        value = self.cleaned_data.get("wikidata_id", "").strip().upper()
        if value and not (value.startswith("Q") and value[1:].isdigit()):
            raise forms.ValidationError("Format attendu : Q suivi de chiffres (ex. Q1290).")
        return value

    def clean_image_url(self):
        url = self.cleaned_data.get("image_url")
        if url and not wiki.is_allowed_image_url(url):
            raise forms.ValidationError("Cette image ne provient pas de Wikimedia.")
        return url

    def save(self, commit=True):
        celeb = super().save(commit=False)
        # Nom ou identifiant changé à la main ⇒ on ré-identifiera la page Wikipédia.
        if self.instance.pk and {"name", "wikidata_id"} & set(self.changed_data):
            if "wiki_title_fr" not in self.changed_data:
                celeb.wiki_title_fr = ""
            if "wiki_title_en" not in self.changed_data:
                celeb.wiki_title_en = ""
        if self.cleaned_data.get("remove_image") and not self.cleaned_data.get("image"):
            celeb.image = None
        url = self.cleaned_data.get("image_url")
        if url and not self.files.get("image"):
            data = wiki.download_image(url)
            ext = url.rsplit(".", 1)[-1].lower()
            ext = ext if ext in ("jpg", "jpeg", "png", "webp") else "jpg"
            celeb.image.save(f"{slugify(celeb.name) or 'photo'}.{ext}", ContentFile(data), save=False)
        if commit:
            celeb.save()
            save_activities(celeb, self.cleaned_data.get("activities", []))
        return celeb


class SightingForm(forms.ModelForm):
    class Meta:
        model = CelebritySighting
        fields = ["date_seen", "location", "notes"]
        widgets = {
            "date_seen": DateInput(),
            "location": forms.TextInput(attrs={"list": "known-locations", "placeholder": "Ville, lieu, événement…"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Contexte, anecdote, photo prise…"}),
        }


# Ancien nom conservé pour compatibilité
CelebritySightingForm = SightingForm


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["name", "category"]
        labels = {"name": "Nom", "category": "Secteur"}

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        qs = Activity.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Cette activité existe déjà.")
        return name


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        labels = {"name": "Nouveau secteur"}
