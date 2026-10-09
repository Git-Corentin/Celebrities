import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from .text import normalize


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "secteur"

    def __str__(self):
        return self.name


class Activity(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "activité"

    def save(self, *args, **kwargs):
        self.name = (self.name or "").strip()
        if not self.name:
            raise ValueError("Le nom de l'activité ne peut pas être vide.")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


THUMB_SIZE = (240, 240)


class Celebrity(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    # Version sans accents / minuscules : recherche et tri rapides en SQL.
    name_key = models.CharField(max_length=255, db_index=True, blank=True, editable=False)

    image = models.ImageField(upload_to="celebs/", blank=True, null=True)
    thumbnail = models.ImageField(upload_to="celebs/thumbs/", blank=True, null=True, editable=False)

    activities = models.ManyToManyField(Activity, blank=True, related_name="celebrities")

    # ── Popularité ──
    popularity_score = models.FloatField(default=0)  # vues Wikipédia fr+en sur 60 jours
    views_fr = models.PositiveIntegerField(default=0, editable=False)
    views_en = models.PositiveIntegerField(default=0, editable=False)
    popularity_updated_at = models.DateTimeField(null=True, blank=True, editable=False)

    # Identification Wikipédia (remplie automatiquement, corrigeable à la main)
    wikidata_id = models.CharField("Wikidata (Qxxx)", max_length=20, blank=True)
    wiki_title_fr = models.CharField("Titre Wikipédia FR", max_length=255, blank=True)
    wiki_title_en = models.CharField("Titre Wikipédia EN", max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        ordering = ["name_key"]
        verbose_name = "célébrité"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("celebrity_detail", args=[self.pk])

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._loaded_image = instance.__dict__.get("image")
        return instance

    def save(self, *args, **kwargs):
        self.name = (self.name or "").strip()
        self.name_key = normalize(self.name)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "name" in update_fields:
            kwargs["update_fields"] = set(update_fields) | {"name_key"}
        super().save(*args, **kwargs)

        current = self.image.name if self.image else ""
        previous = getattr(self, "_loaded_image", None)
        previous = previous.name if hasattr(previous, "name") else (previous or "")
        if current != previous or (current and not self.thumbnail):
            self.build_thumbnail()
        self._loaded_image = self.image.name if self.image else ""

    def build_thumbnail(self):
        """Miniature carrée 240px : la liste charge ~10 Ko par image au lieu de plusieurs Mo."""
        from PIL import Image, ImageOps

        if self.thumbnail:
            self.thumbnail.delete(save=False)
        if not self.image:
            Celebrity.objects.filter(pk=self.pk).update(thumbnail=None)
            return
        try:
            self.image.open("rb")
            img = Image.open(self.image)
            img = ImageOps.exif_transpose(img).convert("RGB")
            img = ImageOps.fit(img, THUMB_SIZE, Image.LANCZOS, centering=(0.5, 0.35))
            buf = BytesIO()
            img.save(buf, "JPEG", quality=84, optimize=True)
        except Exception:
            return
        finally:
            try:
                self.image.close()
            except Exception:
                pass
        base = slugify(os.path.splitext(os.path.basename(self.image.name))[0]) or "img"
        self.thumbnail.save(f"{base}-{self.pk}.jpg", ContentFile(buf.getvalue()), save=False)
        Celebrity.objects.filter(pk=self.pk).update(thumbnail=self.thumbnail.name)

    @property
    def avatar_url(self):
        if self.thumbnail:
            return self.thumbnail.url
        if self.image:
            return self.image.url
        return ""

    @property
    def initials(self):
        parts = [p for p in self.name.replace("-", " ").split() if p]
        return "".join(p[0] for p in parts[:2]).upper() or "?"

    @property
    def wikipedia_url(self):
        if self.wiki_title_fr:
            return "https://fr.wikipedia.org/wiki/" + self.wiki_title_fr.replace(" ", "_")
        if self.wiki_title_en:
            return "https://en.wikipedia.org/wiki/" + self.wiki_title_en.replace(" ", "_")
        return ""


class CelebritySighting(models.Model):
    celebrity = models.ForeignKey(Celebrity, on_delete=models.CASCADE, related_name='sightings')
    date_seen = models.DateField("date", null=True, blank=True)
    location = models.CharField("lieu", max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-date_seen", "-id"]
        verbose_name = "rencontre"

    def __str__(self):
        return f"{self.celebrity.name} seen on {self.date_seen} at {self.location}"
