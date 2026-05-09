# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('crm', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='is_approved',
            field=models.BooleanField(default=False, db_index=True, verbose_name='подтверждена'),
        ),
        migrations.AddField(
            model_name='organization',
            name='created_by_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_organizations', to=settings.AUTH_USER_MODEL, verbose_name='создана пользователем'),
        ),
    ]