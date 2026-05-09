from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [
        ('hotel', '0002_add_room_subdivisions_and_multiple_occupancy'),
    ]
    operations = [
        migrations.RenameField(
            model_name='room',
            old_name='max_concurrent_bookings',
            new_name='max_guests_per_room',
        ),
        migrations.AlterField(
            model_name='room',
            name='max_guests_per_room',
            field=models.PositiveSmallIntegerField(
                default=1,
                verbose_name='макс. персон в номере',
                validators=[django.core.validators.MinValueValidator(1)],
                help_text='Максимальное количество персон, которые могут одновременно проживать в номере',
            ),
        ),
    ]
