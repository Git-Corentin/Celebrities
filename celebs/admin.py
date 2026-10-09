from django.contrib import admin

from .models import Activity, Category, Celebrity, CelebritySighting


class SightingInline(admin.TabularInline):
    model = CelebritySighting
    extra = 0


@admin.register(Celebrity)
class CelebrityAdmin(admin.ModelAdmin):
    list_display = ("name", "popularity_score", "wikidata_id", "popularity_updated_at")
    search_fields = ("name", "name_key", "wikidata_id")
    filter_horizontal = ("activities",)
    inlines = [SightingInline]


@admin.register(CelebritySighting)
class SightingAdmin(admin.ModelAdmin):
    list_display = ("celebrity", "date_seen", "location")
    list_filter = ("date_seen",)
    search_fields = ("celebrity__name", "location", "notes")
    autocomplete_fields = ("celebrity",)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    list_editable = ("category",)
    list_filter = ("category",)
    search_fields = ("name",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)
