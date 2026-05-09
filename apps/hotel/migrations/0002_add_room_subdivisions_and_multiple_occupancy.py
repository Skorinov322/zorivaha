# Generated manually for room subdivisions and multiple occupancy

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotel', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='subdivision',
            field=models.CharField(blank=True, help_text='Например: а, б, в для разделения номера на части', max_length=5, verbose_name='подразделение'),
        ),
        migrations.AddField(
            model_name='room',
            name='max_concurrent_bookings',
            field=models.PositiveSmallIntegerField(default=1, help_text='Количество гостей, которые могут одновременно находиться в номере', verbose_name='макс. одновременных броней'),
        ),
        migrations.AlterField(
            model_name='room',
            name='number',
            field=models.CharField(max_length=10, verbose_name='номер комнаты'),
        ),
        migrations.AddConstraint(
            model_name='room',
            constraint=models.UniqueConstraint(fields=('number', 'subdivision'), name='unique_room_number_subdivision'),
        ),
        migrations.AlterModelOptions(
            name='room',
            options={'ordering': ['floor', 'number', 'subdivision'], 'verbose_name': 'номер', 'verbose_name_plural': 'номера'},
        ),
    ]