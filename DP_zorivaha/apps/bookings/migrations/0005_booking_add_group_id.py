import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('bookings', '0004_add_early_check_in'),
    ]
    operations = [
        migrations.AddField(
            model_name='booking',
            name='group_id',
            field=models.UUIDField(
                null=True,
                blank=True,
                db_index=True,
                verbose_name='ID группы',
                help_text='UUID группы броней, созданных в рамках одного запроса',
            ),
        ),
    ]
