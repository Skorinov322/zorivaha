from django.db import migrations


def update_stat2(apps, schema_editor):
    AboutPage = apps.get_model("content", "AboutPage")
    AboutPage.objects.filter(stat2_number="3★").update(stat2_number="Без звезд")


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0005_aboutpage_stat4_20"),
    ]

    operations = [
        migrations.RunPython(update_stat2, migrations.RunPython.noop),
    ]
