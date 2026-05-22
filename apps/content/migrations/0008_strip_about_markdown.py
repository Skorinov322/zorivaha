from django.db import migrations


TEXT_FIELDS = ("about_text", "rooms_text", "services_text", "contacts_text")


def strip_markers(apps, schema_editor):
    AboutPage = apps.get_model("content", "AboutPage")
    for page in AboutPage.objects.all():
        changed = False
        for field in TEXT_FIELDS:
            value = getattr(page, field) or ""
            cleaned = value.replace("**", "")
            if cleaned != value:
                setattr(page, field, cleaned)
                changed = True
        if changed:
            page.save(update_fields=TEXT_FIELDS)


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0007_aboutpage_gallery_photos"),
    ]

    operations = [
        migrations.RunPython(strip_markers, migrations.RunPython.noop),
    ]
