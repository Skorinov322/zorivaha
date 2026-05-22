"""Template filters for the About page."""

import re

from django import template
from django.template.defaultfilters import linebreaks
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def format_about_text(value):
    """Remove markdown ** markers and render line breaks."""
    if not value:
        return ""
    text = str(value).replace("**", "")
    text = re.sub(r"^[•]\s*", "- ", text, flags=re.MULTILINE)
    return mark_safe(linebreaks(text))
