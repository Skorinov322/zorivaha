"""Canonical public contact details for the hotel website."""

CONTACT_PHONE_CANONICAL = "+7 (346) 628-70-03"
CONTACT_PHONE_SECOND_CANONICAL = "+7 (995) 097-30-59"
CONTACT_EMAIL_CANONICAL = "zorivaha@mail.ru"

LEGACY_PHONES = frozenset({
    "+7 (928) 000-00-00",
    "+7 (3466) 28-70-03",
    "+7 (3466) 28-23-61",
})

LEGACY_EMAILS = frozenset({
    "info@zorivaha.ru",
})


def resolve_contact_phone(value: str, *, primary: bool = True) -> str:
    """Return canonical phone when env/CMS still has a placeholder value."""
    fallback = CONTACT_PHONE_CANONICAL if primary else CONTACT_PHONE_SECOND_CANONICAL
    cleaned = (value or "").strip()
    if not cleaned or cleaned in LEGACY_PHONES:
        return fallback
    return cleaned


def resolve_contact_email(value: str) -> str:
    """Return canonical email when env/CMS still has a placeholder value."""
    cleaned = (value or "").strip()
    if not cleaned or cleaned in LEGACY_EMAILS:
        return CONTACT_EMAIL_CANONICAL
    return cleaned
