# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0005_booking_add_group_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='booking',
            name='infants',
        ),
    ]