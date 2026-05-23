# Generated manually

from django.db import migrations, models
import apps.core.models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0003_populate_legalpages'),
    ]

    operations = [
        migrations.CreateModel(
            name='AboutPage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='обновлено')),
                ('hero_title', models.CharField(default='О гостинице Зори Ваха', max_length=200, verbose_name='заголовок героя')),
                ('hero_subtitle', models.CharField(default='Комфортное размещение в самом сердце Излучинска с заботой о каждом госте', max_length=300, verbose_name='подзаголовок героя')),
                ('about_title', models.CharField(default='О нас', max_length=200, verbose_name='заголовок блока О нас')),
                ('about_text', models.TextField(help_text='Основная информация о гостинице', verbose_name='текст блока О нас')),
                ('about_image', models.ImageField(blank=True, help_text='Рекомендуемый размер: 800x600px', null=True, upload_to='about/%Y/%m/', verbose_name='фото для блока О нас')),
                ('rooms_title', models.CharField(default='Номера', max_length=200, verbose_name='заголовок блока Номера')),
                ('rooms_text', models.TextField(help_text='Информация о номерах и категориях', verbose_name='текст блока Номера')),
                ('rooms_image', models.ImageField(blank=True, help_text='Рекомендуемый размер: 800x600px', null=True, upload_to='about/%Y/%m/', verbose_name='фото для блока Номера')),
                ('services_title', models.CharField(default='Сервис и инфраструктура', max_length=200, verbose_name='заголовок блока Сервис')),
                ('services_text', models.TextField(help_text='Информация об услугах и удобствах', verbose_name='текст блока Сервис')),
                ('services_image', models.ImageField(blank=True, help_text='Рекомендуемый размер: 800x600px', null=True, upload_to='about/%Y/%m/', verbose_name='фото для блока Сервис')),
                ('contacts_title', models.CharField(default='Важная информация и контакты', max_length=200, verbose_name='заголовок блока Контакты')),
                ('contacts_text', models.TextField(help_text='Правила проживания и контактная информация', verbose_name='текст блока Контакты')),
                ('contacts_image', models.ImageField(blank=True, help_text='Рекомендуемый размер: 800x600px', null=True, upload_to='about/%Y/%m/', verbose_name='фото для блока Контакты')),
                ('stat1_number', models.CharField(default='48+', max_length=20, verbose_name='статистика 1: число')),
                ('stat1_label', models.CharField(default='Номеров', max_length=50, verbose_name='статистика 1: подпись')),
                ('stat2_number', models.CharField(default='3★', max_length=20, verbose_name='статистика 2: число')),
                ('stat2_label', models.CharField(default='Категория', max_length=50, verbose_name='статистика 2: подпись')),
                ('stat3_number', models.CharField(default='24/7', max_length=20, verbose_name='статистика 3: число')),
                ('stat3_label', models.CharField(default='Поддержка', max_length=50, verbose_name='статистика 3: подпись')),
                ('stat4_number', models.CharField(default='10+', max_length=20, verbose_name='статистика 4: число')),
                ('stat4_label', models.CharField(default='Лет опыта', max_length=50, verbose_name='статистика 4: подпись')),
                ('is_active', models.BooleanField(default=True, verbose_name='активна')),
            ],
            options={
                'verbose_name': 'страница О нас',
                'verbose_name_plural': 'страницы О нас',
            },
            bases=(apps.core.models.TimeStampedModel,),
        ),
    ]
