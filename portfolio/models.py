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


class Institution(models.Model):
    """Établissement associé au projet"""
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    logo = models.ImageField(
        upload_to="institutions/",
        help_text="Logo circulaire de l'établissement (PNG recommandé)"
    )
    website = models.URLField(blank=True)

    class Meta:
        ordering = ['name']

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

    institution = models.ForeignKey(
        Institution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='projects',
        help_text="Établissement où le projet a été réalisé"
    )

    is_research = models.BooleanField(
        default=False,
        help_text="Cocher si c'est un projet de recherche"
    )

    github_url = models.URLField(blank=True)
    technologies = models.CharField(
        max_length=200,
        help_text="Ex: C++, Python, Django, IA"
    )

    created_at = models.DateField()

    order = models.IntegerField(
        default=0,
        help_text="Ordre d'affichage dans la catégorie"
    )

    class Meta:
        ordering = ['category__order', 'order', '-created_at']

    def __str__(self):
        return self.title


class ProjectMedia(models.Model):
    """Fichiers multimédias associés à un projet"""

    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Vidéo'),
        ('pdf', 'PDF'),
        ('markdown', 'Markdown / README')
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='media_files'
    )

    media_type = models.CharField(
        max_length=10,
        choices=MEDIA_TYPES,
        help_text="Type de fichier"
    )

    file = models.FileField(
        upload_to="project_media/",
        help_text="Fichier image, vidéo ou PDF"
    )

    caption = models.CharField(
        max_length=200,
        blank=True,
        help_text="Légende optionnelle"
    )

    order = models.IntegerField(
        default=0,
        help_text="Ordre d'affichage"
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'uploaded_at']
        verbose_name_plural = "Project Media"

    def __str__(self):
        return f"{self.project.title} - {self.get_media_type_display()} #{self.order}"