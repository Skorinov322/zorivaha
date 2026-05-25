"""
hotel/forms.py

Forms:
  AvailabilitySearchForm — поиск доступных номеров по датам
  ContactForm — форма обратной связи
  RoomCategoryForm — создание/редактирование категории номеров
  RoomForm — создание/редактирование номеров
  RoomImageForm — загрузка изображений
  RoomStatusForm — изменение статуса номера
"""

from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from .models import Amenity, RoomCategory, Room, RoomImage


phone_validator = RegexValidator(
    regex=r"^\+?[\d\s\-\(\)]{7,20}$",
    message=_("Введите корректный номер телефона."),
)


class AvailabilitySearchForm(forms.Form):
    """Форма поиска доступных номеров по датам"""
    
    check_in = forms.DateField(
        label=_("Дата заезда"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    check_out = forms.DateField(
        label=_("Дата выезда"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    guests = forms.IntegerField(
        label=_("Количество гостей"),
        min_value=1,
        max_value=10,
        initial=2,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned = super().clean()
        check_in = cleaned.get("check_in")
        check_out = cleaned.get("check_out")
        if check_in and check_out and check_out <= check_in:
            raise forms.ValidationError(_("Дата выезда должна быть позже даты заезда."))
        return cleaned


class ContactForm(forms.Form):
    """Форма обратной связи на странице контактов"""
    
    name = forms.CharField(
        label=_("Ваше имя"),
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'lux-input',
            'placeholder': 'Иван Иванов',
            'autocomplete': 'name'
        })
    )
    
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            'class': 'lux-input',
            'placeholder': 'ivan@example.com',
            'autocomplete': 'email'
        })
    )

    phone = forms.CharField(
        label=_("Телефон"),
        max_length=20,
        required=False,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={
            'class': 'lux-input',
            'placeholder': '+7 (___) ___-__-__',
            'autocomplete': 'tel',
            'type': 'tel',
            'data-mask': '+7 (000) 000-00-00',
            'data-mask-placeholder': '_'
        })
    )
    
    subject = forms.CharField(
        label=_("Тема"),
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'lux-input',
            'placeholder': 'Вопрос о бронировании'
        })
    )
    
    message = forms.CharField(
        label=_("Сообщение"),
        widget=forms.Textarea(attrs={
            'class': 'lux-input',
            'rows': 5,
            'placeholder': 'Напишите ваш вопрос или пожелание...',
            'style': 'resize:vertical;min-height:130px'
        })
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user and user.is_authenticated and not self.data:
            self.fields["name"].initial = user.get_full_name() or user.email
            self.fields["email"].initial = user.email
            self.fields["phone"].initial = user.phone


class RoomCategoryForm(forms.ModelForm):
    """Форма создания/редактирования категории номеров"""

    new_amenities = forms.CharField(
        label=_("Добавить удобства"),
        required=False,
        help_text=_("Введите несколько удобств через запятую или с новой строки."),
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Wi-Fi, кондиционер, телевизор",
        }),
    )

    class Meta:
        model = RoomCategory
        fields = [
            'name', 'slug', 'description', 'short_description',
            'max_guests', 'bed_type', 'area_sqm',
            'base_price_per_night', 'weekend_price_per_night',
            'thumbnail', 'amenities', 'is_active', 'is_featured'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'short_description': forms.TextInput(attrs={'class': 'form-control'}),
            'max_guests': forms.NumberInput(attrs={'class': 'form-control'}),
            'bed_type': forms.Select(attrs={'class': 'form-select'}),
            'area_sqm': forms.NumberInput(attrs={'class': 'form-control'}),
            'base_price_per_night': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'weekend_price_per_night': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control'}),
            'amenities': forms.CheckboxSelectMultiple(),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Slug is auto-generated via JS or in model.save(), so it's optional in the form
        self.fields['slug'].required = False
        self.fields['amenities'].queryset = Amenity.objects.order_by("sort_order", "name")

    def clean_new_amenities(self):
        raw_value = self.cleaned_data.get("new_amenities", "")
        names = []
        seen = set()

        for value in raw_value.replace("\n", ",").split(","):
            name = value.strip()
            key = name.casefold()
            if name and key not in seen:
                names.append(name)
                seen.add(key)

        return names


class RoomForm(forms.ModelForm):
    """Форма создания/редактирования номеров"""
    
    class Meta:
        model = Room
        fields = [
            'category', 'number', 'subdivision', 'floor', 'status',
            'max_guests_per_room', 'has_balcony', 'has_sea_view',
            'has_mountain_view', 'extra_amenities', 'notes'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'subdivision': forms.TextInput(attrs={'class': 'form-control'}),
            'floor': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'max_guests_per_room': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'has_balcony': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_sea_view': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_mountain_view': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'extra_amenities': forms.CheckboxSelectMultiple(),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class RoomImageForm(forms.ModelForm):
    """Форма загрузки изображений для категории номеров"""
    
    class Meta:
        model = RoomImage
        fields = ['image', 'caption', 'alt_text', 'is_primary']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'caption': forms.TextInput(attrs={'class': 'form-control'}),
            'alt_text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class RoomStatusForm(forms.ModelForm):
    """Форма быстрого изменения статуса номера"""
    
    class Meta:
        model = Room
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
        }