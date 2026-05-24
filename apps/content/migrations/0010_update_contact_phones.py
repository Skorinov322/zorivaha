from django.db import migrations


OLD_PHONES = (
    "+7 (3466) 28-70-03",
    "+7 (3466) 28-23-61",
)
NEW_PHONES = (
    "+7 (346) 628-70-03",
    "+7 (995) 097-30-59",
)


def update_contact_phones(apps, schema_editor):
    AboutPage = apps.get_model("content", "AboutPage")
    for page in AboutPage.objects.all():
        text = page.contacts_text or ""
        updated = text
        for old, new in zip(OLD_PHONES, NEW_PHONES):
            updated = updated.replace(old, new)
        if updated != text:
            page.contacts_text = updated
            page.save(update_fields=["contacts_text"])


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0009_gallery_section_about"),
    ]

    operations = [
        migrations.RunPython(update_contact_phones, migrations.RunPython.noop),
    ]
