# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='patronymic',
            field=models.CharField(blank=True, max_length=150, verbose_name='отчество'),
        ),
    ]
