"""
Project-wide utility functions.
Keep these pure (no Django ORM, no HTTP) so they're easy to test.
"""

import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterator


def date_range(start: date, end: date) -> Iterator[date]:
    """Yield every date from start up to (but not including) end."""
    current = start
    while current < end:
        yield current
        current += timedelta(days=1)


def nights_between(check_in: date, check_out: date) -> int:
    """Return the number of nights between two dates."""
    delta = (check_out - check_in).days
    if delta <= 0:
        raise ValueError("check_out must be after check_in")
    return delta


def format_price(amount: Decimal, currency: str = "₽") -> str:
    """Format a Decimal price for display: '12 500 ₽'."""
    return f"{amount:,.0f} {currency}".replace(",", "\u202f")


def slugify_ru(text: str) -> str:
    """
    Transliterate Russian text to a URL-safe slug.
    Falls back to Django's slugify for non-Russian characters.
    """
    from django.utils.text import slugify

    translit_map = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
        "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
        "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
        "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
        "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
        "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
        "э": "e", "ю": "yu", "я": "ya",
    }
    result = ""
    for char in text.lower():
        result += translit_map.get(char, char)
    return slugify(result)


def mask_email(email: str) -> str:
    """Mask email for display: 'jo***@gmail.com'."""
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        masked = local[0] + "***"
    else:
        masked = local[:2] + "***"
    return f"{masked}@{domain}"
