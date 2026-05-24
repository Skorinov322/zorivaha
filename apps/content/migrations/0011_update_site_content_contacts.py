from django.db import migrations


LEGACY_PHONES = {
    "+7 (928) 000-00-00": "+7 (346) 628-70-03",
    "+7 (3466) 28-70-03": "+7 (346) 628-70-03",
    "+7 (3466) 28-23-61": "+7 (995) 097-30-59",
}

SITE_CONTENT_KEYS = {
    "contact_phone": "+7 (346) 628-70-03",
    "contact_phone_second": "+7 (995) 097-30-59",
    "contact_email": "zorivaha@mail.ru",
}


LEGACY_EMAILS = {
    "info@zorivaha.ru": "zorivaha@mail.ru",
}


def update_about_contacts(apps, schema_editor):
    AboutPage = apps.get_model("content", "AboutPage")
    for page in AboutPage.objects.all():
        text = page.contacts_text or ""
        updated = text
        for old, new in LEGACY_PHONES.items():
            updated = updated.replace(old, new)
        updated = updated.replace("info@zorivaha.ru", "zorivaha@mail.ru")
        if updated != text:
            page.contacts_text = updated
            page.save(update_fields=["contacts_text"])


def update_site_content_contacts(apps, schema_editor):
    SiteContent = apps.get_model("content", "SiteContent")

    for key, canonical in SITE_CONTENT_KEYS.items():
        try:
            obj = SiteContent.objects.get(key=key)
        except SiteContent.DoesNotExist:
            continue

        value = (obj.value_text or "").strip()
        if key.endswith("_email"):
            updated = LEGACY_EMAILS.get(value, value or canonical)
        else:
            updated = LEGACY_PHONES.get(value, value or canonical)

        if updated != value:
            obj.value_text = updated
            obj.save(update_fields=["value_text"])


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0010_update_contact_phones"),
    ]

    operations = [
        migrations.RunPython(update_about_contacts, migrations.RunPython.noop),
        migrations.RunPython(update_site_content_contacts, migrations.RunPython.noop),
    ]
