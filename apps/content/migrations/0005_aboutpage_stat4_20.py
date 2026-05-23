from django.db import migrations


def update_stat4(apps, schema_editor):
    AboutPage = apps.get_model("content", "AboutPage")
    AboutPage.objects.filter(stat4_number="10+").update(stat4_number="20+")


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0004_aboutpage"),
    ]

    operations = [
        migrations.RunPython(update_stat4, migrations.RunPython.noop),
    ]
