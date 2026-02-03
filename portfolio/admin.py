from django.contrib import admin
from .models import Category, Project


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'color']
    list_editable = ['order']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'order', 'created_at']
    list_filter = ['category', 'created_at']
    list_editable = ['order']
    search_fields = ['title', 'description']
    ordering = ['category__order', 'order', '-created_at']

    fieldsets = (
        ('Informations principales', {
            'fields': ('title', 'category', 'short_description', 'description')
        }),
        ('Détails techniques', {
            'fields': ('technologies', 'github_url', 'pdf_report')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'order')
        }),
    )