# portfolio/templatetags/media_filters.py
"""Template filters for the portfolio app.

`render_markdown` is the only one with an optional dependency
(python-markdown). It degrades to escaped plain text if the package
is missing, so a fresh deploy never 500s because of it.
"""

import os

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def filter_by_type(media_list, media_type):
    """Keep only the ProjectMedia entries of a given type."""
    return [m for m in media_list if m.media_type == media_type]


@register.filter
def uncategorized(projects):
    """Projects that have no category assigned."""
    return [p for p in projects if not p.category_id]


@register.filter
def split_commas(value):
    """'Python, PyTorch , SQL' -> ['Python', 'PyTorch', 'SQL']"""
    if not value:
        return []
    return [part.strip() for part in str(value).split(',') if part.strip()]


@register.filter
def basename(path):
    """'project_media/report_v2.pdf' -> 'report_v2.pdf'"""
    return os.path.basename(str(path or ''))


# Extensions are added one by one so a missing optional dependency
# (e.g. Pygments for codehilite) never breaks the whole render.
_CANDIDATE_EXTENSIONS = [
    'fenced_code',
    'tables',
    'sane_lists',
    'attr_list',
    'nl2br',
    'toc',
    'codehilite',
]


def _usable_extensions(md_module):
    usable = []
    for name in _CANDIDATE_EXTENSIONS:
        try:
            md_module.markdown('', extensions=usable + [name])
            usable.append(name)
        except Exception:
            continue
    return usable


@register.filter
def render_markdown(media):
    """Read a Markdown ProjectMedia file and render it to HTML.

    Usage:  {{ media|render_markdown }}
    """
    try:
        media.file.open('rb')
        raw = media.file.read()
        media.file.close()
    except Exception:
        return ''

    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', errors='replace')

    try:
        import markdown as md_module
    except ImportError:
        # No python-markdown installed: show the source, readable and safe.
        return mark_safe('<pre><code>%s</code></pre>' % escape(raw))

    try:
        html = md_module.markdown(raw, extensions=_usable_extensions(md_module))
    except Exception:
        return mark_safe('<pre><code>%s</code></pre>' % escape(raw))

    return mark_safe(html)