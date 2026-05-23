"""
content/models_about.py

Модель для редактируемого контента страницы "О нас"
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel


class AboutPage(TimeStampedModel):
    """
    Singleton модель для контента страницы "О нас".
    Редактируется через админ-панель.
    """
    
    # Основной контент
    hero_title = models.CharField(
        _("заголовок героя"),
        max_length=200,
        default="О гостинице Зори Ваха"
    )
    hero_subtitle = models.CharField(
        _("подзаголовок героя"),
        max_length=300,
        default="Комфортное размещение в самом сердце Излучинска с заботой о каждом госте"
    )
    
    # Блок "О нас"
    about_title = models.CharField(
        _("заголовок блока О нас"),
        max_length=200,
        default="О нас"
    )
    about_text = models.TextField(
        _("текст блока О нас"),
        help_text=_("Основная информация о гостинице")
    )
    about_gallery_photo = models.ForeignKey(
        "content.HotelGallery",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="about_blocks_about",
        verbose_name=_("фото из галереи (блок О нас)"),
        help_text=_("Выберите фото из галереи гостиницы"),
    )
    about_image = models.ImageField(
        _("фото для блока О нас (загрузка)"),
        upload_to="about/%Y/%m/",
        null=True,
        blank=True,
        help_text=_("Альтернатива: загрузить файл, если не выбрано фото из галереи"),
    )
    
    # Блок "Номера"
    rooms_title = models.CharField(
        _("заголовок блока Номера"),
        max_length=200,
        default="Номера"
    )
    rooms_text = models.TextField(
        _("текст блока Номера"),
        help_text=_("Информация о номерах и категориях")
    )
    rooms_gallery_photo = models.ForeignKey(
        "content.HotelGallery",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="about_blocks_rooms",
        verbose_name=_("фото из галереи (блок Номера)"),
        help_text=_("Выберите фото из галереи гостиницы"),
    )
    rooms_image = models.ImageField(
        _("фото для блока Номера (загрузка)"),
        upload_to="about/%Y/%m/",
        null=True,
        blank=True,
        help_text=_("Альтернатива: загрузить файл"),
    )
    
    # Блок "Сервис и инфраструктура"
    services_title = models.CharField(
        _("заголовок блока Сервис"),
        max_length=200,
        default="Сервис и инфраструктура"
    )
    services_text = models.TextField(
        _("текст блока Сервис"),
        help_text=_("Информация об услугах и удобствах")
    )
    services_gallery_photo = models.ForeignKey(
        "content.HotelGallery",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="about_blocks_services",
        verbose_name=_("фото из галереи (блок Сервис)"),
        help_text=_("Выберите фото из галереи гостиницы"),
    )
    services_image = models.ImageField(
        _("фото для блока Сервис (загрузка)"),
        upload_to="about/%Y/%m/",
        null=True,
        blank=True,
        help_text=_("Альтернатива: загрузить файл"),
    )
    
    # Блок "Контакты и правила"
    contacts_title = models.CharField(
        _("заголовок блока Контакты"),
        max_length=200,
        default="Важная информация и контакты"
    )
    contacts_text = models.TextField(
        _("текст блока Контакты"),
        help_text=_("Правила проживания и контактная информация")
    )
    contacts_gallery_photo = models.ForeignKey(
        "content.HotelGallery",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="about_blocks_contacts",
        verbose_name=_("фото из галереи (блок Контакты)"),
        help_text=_("Выберите фото из галереи гостиницы"),
    )
    contacts_image = models.ImageField(
        _("фото для блока Контакты (загрузка)"),
        upload_to="about/%Y/%m/",
        null=True,
        blank=True,
        help_text=_("Альтернатива: загрузить файл"),
    )
    
    # Статистика (4 блока)
    stat1_number = models.CharField(_("статистика 1: число"), max_length=20, default="48+")
    stat1_label = models.CharField(_("статистика 1: подпись"), max_length=50, default="Номеров")
    
    stat2_number = models.CharField(_("статистика 2: число"), max_length=20, default="Без звезд")
    stat2_label = models.CharField(_("статистика 2: подпись"), max_length=50, default="Категория")
    
    stat3_number = models.CharField(_("статистика 3: число"), max_length=20, default="24/7")
    stat3_label = models.CharField(_("статистика 3: подпись"), max_length=50, default="Поддержка")
    
    stat4_number = models.CharField(_("статистика 4: число"), max_length=20, default="20+")
    stat4_label = models.CharField(_("статистика 4: подпись"), max_length=50, default="Лет опыта")
    
    # Мета
    is_active = models.BooleanField(_("активна"), default=True)
    
    class Meta:
        verbose_name = _("О нас")
        verbose_name_plural = _("О нас")
    
    def __str__(self):
        return "Страница О нас"
    
    def save(self, *args, **kwargs):
        # Singleton pattern - только одна запись
        self.pk = 1
        super().save(*args, **kwargs)

    def get_block_image_url(self, gallery_photo, image_field):
        """URL for block image: gallery photo takes priority over upload."""
        if gallery_photo and gallery_photo.image:
            return gallery_photo.image.url
        if image_field:
            return image_field.url
        return None

    @property
    def about_image_url(self):
        return self.get_block_image_url(self.about_gallery_photo, self.about_image)

    @property
    def rooms_image_url(self):
        return self.get_block_image_url(self.rooms_gallery_photo, self.rooms_image)

    @property
    def services_image_url(self):
        return self.get_block_image_url(self.services_gallery_photo, self.services_image)

    @property
    def contacts_image_url(self):
        return self.get_block_image_url(self.contacts_gallery_photo, self.contacts_image)
    
    @classmethod
    def get_instance(cls):
        """Получить единственный экземпляр страницы"""
        obj, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'about_text': '''Мы предлагаем всё необходимое для полноценного отдыха и продуктивной работы: чистые, ухоженные номера, продуманную инфраструктуру и доброжелательную атмосферу. Особого внимания заслуживает наш зелёный уголок на третьем этаже — место для тихого отдыха в любое время года.

Наша команда работает без громких обещаний и излишнего пафоса. Вместо этого мы ежедневно заботимся о том, чтобы ваше пребывание было максимально спокойным, а любая поездка — даже самая напряжённая командировка — становилась чуть менее утомительной.

«Зори Ваха» — это не просто гостиница. Это место, где соблюдают стандарты, но не забывают о человеческом отношении. Мы будем рады видеть вас в числе наших гостей.''',
                'rooms_text': '''В гостинице 48 номеров. Цены варьируются в зависимости от категории: стандартные номера от 1800 ₽/ночь, люксы — дороже.

Категории номеров:
• Эконом: две одноместные кровати, возможное подселение
• Стандарт: с удобствами на блоке (санузел общий с соседним номером)
• Полулюкс: одноместные и двухместные
• Люкс: двухместный с двуспальной кроватью, отдельный санузел

Оснащение номеров:
Во всех номерах: телевизор (кабельное ТВ), холодильник, чайник, микроволновая печь, халат и тапочки.''',
                'services_text': '''Ресепшн:
• Заезд: после 12:00
• Выезд: до 12:00
• Работает круглосуточно

Wellness & SPA:
Сауна, спа-центр, массажный кабинет, солярий, соляная комната, инфракрасная сауна, тренажерный зал.

Удобства:
Бесплатная парковка, Wi-Fi, круглосуточная стойка регистрации, гладильные принадлежности, фен, факс/ксерокс, камера хранения, прачечная.''',
                'contacts_text': '''Правила:
• Документы: при заезде необходим оригинал паспорта
• Политика курения: гостиница полностью для некурящих
• Домашние животные: размещение не допускается

Адрес:
пгт. Излучинск, ул. Школьная, д. 12, Нижневартовский район, Ханты-Мансийский АО — Югра

Телефоны:
+7 (3466) 28-70-03
+7 (3466) 28-23-61'''
            }
        )
        return obj
