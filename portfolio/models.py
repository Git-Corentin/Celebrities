# portfolio/models.py
from django.db import models


class Category(models.Model):
    """Catégorie de projet (Deep Learning, NLP, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=7,
        default="#6366f1",
        help_text="Couleur hexadécimale pour la catégorie (ex: #6366f1)"
    )
    order = models.IntegerField(
        default=0,
        help_text="Ordre d'affichage (plus petit = en premier)"
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Project(models.Model):
    title = models.CharField(max_length=200)
    short_description = models.TextField(max_length=300)
    description = models.TextField()

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='projects'
    )

    pdf_report = models.FileField(
        upload_to="reports/",
        blank=True,
        null=True
    )

    github_url = models.URLField(blank=True)
    technologies = models.CharField(
        max_length=200,
        help_text="Ex: C++, Python, Django, IA"
    )

    created_at = models.DateField()

    # NOUVEAU : Pour ordonner les projets dans leur catégorie
    order = models.IntegerField(
        default=0,
        help_text="Ordre d'affichage dans la catégorie"
    )

    class Meta:
        ordering = ['category__order', 'order', '-created_at']

    def __str__(self):
        return self.title