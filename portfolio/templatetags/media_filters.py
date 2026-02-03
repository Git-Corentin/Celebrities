# portfolio/templatetags/media_filters.py
from django import template

register = template.Library()

@register.filter
def filter_by_type(media_list, media_type):
    """Filtre une liste de ProjectMedia par type"""
    return [media for media in media_list if media.media_type == media_type]