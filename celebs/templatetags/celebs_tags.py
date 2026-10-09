import math

from django import template

register = template.Library()


@register.filter
def views(value):
    """12345 -> '12,3 k' ; 2500000 -> '2,5 M'."""
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        return "–"
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f} M".replace(".", ",").replace(",0 ", " ")
    if v >= 10_000:
        return f"{v / 1000:.0f} k"
    if v >= 1000:
        return f"{v / 1000:.1f} k".replace(".", ",").replace(",0 ", " ")
    return str(int(v))


@register.filter
def popbar(value, maximum):
    """Largeur de barre en % sur une échelle logarithmique (sinon tout le monde est à 0 %)."""
    try:
        v, m = float(value or 0), float(maximum or 0)
    except (TypeError, ValueError):
        return 0
    if v <= 0 or m <= 0:
        return 0
    return max(3, round(math.log10(1 + v) / math.log10(1 + m) * 100))


@register.simple_tag(takes_context=True)
def qs(context, **changes):
    """Query string courante avec quelques paramètres modifiés : {% qs page=2 %}."""
    params = context["request"].GET.copy()
    for k, v in changes.items():
        if v in (None, ""):
            params.pop(k, None)
        else:
            params[k] = v
    return "?" + params.urlencode() if params else "?"


@register.filter
def in_list(value, items):
    return value in (items or [])
