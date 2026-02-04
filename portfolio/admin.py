# portfolio/admin.py
from django.contrib import admin
from .models import Category, Institution, Project, ProjectMedia


class ProjectMediaInline(admin.TabularInline):
    model = ProjectMedia
    extra = 1
    fields = ('media_type', 'file', 'caption', 'order')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):  # ← ModelAdmin, PAS TranslationAdmin
    list_display = ('name', 'slug', 'color', 'order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'website')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'institution', 'is_research', 'created_at')
    list_filter = ('category', 'institution', 'is_research')
    search_fields = ('title', 'description')
    inlines = [ProjectMediaInline]


@admin.register(ProjectMedia)
class ProjectMediaAdmin(admin.ModelAdmin):
    list_display = ('project', 'media_type', 'caption', 'order', 'uploaded_at')
    list_filter = ('media_type', 'project')