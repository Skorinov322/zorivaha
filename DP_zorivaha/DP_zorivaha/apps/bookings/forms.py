"""
bookings/forms.py

Forms:
  BookingCreateForm   — публичная форма бронирования (гость)
  BookingCancelForm   — подтверждение отмены (гость)
  BookingStaffForm    — создание/редактирование брони сотрудником
  BookingFilterForm   — фильтр списка броней (staff)
"""

from datetime import date, timedelta

from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from apps.hotel.models import RoomCategory, Room
from apps.crm.models import Organization


phone_validator = RegexValidator(
    regex=r"^\+?[\d\s\-\(\)]{7,20}$",
    message=_("Введите корректный номер телефона."),
)

_INPUT  = "form-control"
_SELECT = "form-select"
_CHECK  = "form-check-input"


# ---------------------------------------------------------------------------
# BookingCreateForm  (public, guest-facing)
# ---------------------------------------------------------------------------

class BookingCreateForm(forms.Form):
    """
    Full booking form shown on /bookings/create/.
    Pre-fills contact fields from the authenticated user's profile.
    """

    # ---- Contact info (snapshot) ----
    guest_last_name = forms.CharField(
        label=_("Фамилия"), max_length=150,
        widget=forms.TextInput(attrs={"class": _INPUT, "placeholder": "Иванов"}),
    )
    guest_first_name = forms.CharField(
        label=_("Имя"), max_length=150,
        widget=forms.TextInput(attrs={"class": _INPUT, "placeholder": "Иван"}),
    )
    guest_patronymic = forms.CharField(
        label=_("Отчество"), max_length=150, required=False,
        widget=forms.TextInput(attrs={"class": _INPUT, "placeholder": "Иванович (необязательно)"}),
    )
    guest_phone = forms.CharField(
        label=_("Телефон"), max_length=20,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={
            "class": _INPUT, 
            "placeholder": "+7 (___) ___-__-__",
            "type": "tel",
            "data-mask": "+7 (000) 000-00-00",
            "data-mask-placeholder": "_"
        }),
    )
    guest_email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={"class": _INPUT, "placeholder": "example@mail.ru"}),
    )

    # ---- Room selection ----
    room_category = forms.ModelChoiceField(
        label=_("Категория номера"),
        queryset=RoomCategory.objects.filter(is_active=True).order_by("sort_order"),
        widget=forms.Select(attrs={"class": _SELECT, "id": "id_room_category"}),
        empty_label=_("— Выберите категорию —"),
    )
    room = forms.ModelChoiceField(
        label=_("Конкретный номер"),
        queryset=Room.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": _SELECT, "id": "id_room"}),
        empty_label=_("— Назначить автоматически —"),
        help_text=_("Оставьте пустым — номер будет назначен при заселении"),
    )

    # ---- Dates ----
    check_in = forms.DateField(
        label=_("Дата заезда"),
        widget=forms.DateInput(attrs={
            "class": _INPUT, "type": "date",
            "min": str(date.today()),
        }),
    )
    check_out = forms.DateField(
        label=_("Дата выезда"),
        widget=forms.DateInput(attrs={"class": _INPUT, "type": "date"}),
    )

    # ---- Guests ----
    adults = forms.IntegerField(
        label=_("Взрослых"), min_value=1, max_value=10, initial=2,
        widget=forms.NumberInput(attrs={"class": _INPUT, "min": 1, "max": 10}),
    )
    children = forms.IntegerField(
        label=_("Детей"), min_value=0, max_value=8, initial=0,
        widget=forms.NumberInput(attrs={"class": _INPUT, "min": 0, "max": 8}),
    )

    # ---- Optional ----
    organization = forms.ModelChoiceField(
        label=_("Организация"),
        queryset=Organization.objects.filter(is_active=True).order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": _SELECT}),
        empty_label=_("— Частное лицо —"),
        help_text=_("Для корпоративных броней"),
    )
    arrival_time = forms.TimeField(
        label=_("Примерное время прибытия"), required=False,
        widget=forms.TimeInput(attrs={"class": _INPUT, "type": "time"}),
    )
    special_requests = forms.CharField(
        label=_("Особые пожелания"), required=False,
        widget=forms.Textarea(attrs={"class": _INPUT, "rows": 3,
                                     "placeholder": _("Аллергии, предпочтения, пожелания…")}),
    )

    def __init__(self, *args, user=None, category_id=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Pre-fill contact fields from user profile
        if user and not self.data:
            self.fields["guest_first_name"].initial = user.first_name
            self.fields["guest_last_name"].initial  = user.last_name
            self.fields["guest_email"].initial      = user.email
            self.fields["guest_phone"].initial      = getattr(user, "phone", "")

        # Hide room selection for regular users (only staff can select specific rooms)
        if user and not (user.is_staff or user.is_admin):
            self.fields["room"].widget = forms.HiddenInput()
            self.fields["room"].required = False
            self.fields["room"].help_text = _("Номер будет назначен автоматически при заселении")

        # Pre-select category if passed via GET
        if category_id:
            self.fields["room_category"].initial = category_id
            # Only load rooms for staff users
            if user and (user.is_staff or user.is_admin):
                self._load_rooms_for_category(category_id)

        # If category already submitted, load rooms for it (only for staff)
        if self.data.get("room_category") and user and (user.is_staff or user.is_admin):
            self._load_rooms_for_category(self.data["room_category"])

    def _load_rooms_for_category(self, category_id):
        """Populate room choices for the selected category."""
        try:
            rooms = Room.objects.filter(
                category_id=int(category_id),
                status=Room.RoomStatus.AVAILABLE,
            ).order_by("floor", "number", "subdivision")
            
            # Create custom choices with full room number display
            choices = [("", _("— Назначить автоматически —"))]
            for room in rooms:
                occupancy_info = ""
                if room.max_concurrent_bookings > 1:
                    current = room.get_current_occupancy_count()
                    occupancy_info = f" ({current}/{room.max_concurrent_bookings})"
                
                label = f"{room.full_number}{occupancy_info}"
                choices.append((room.id, label))
            
            self.fields["room"].choices = choices
        except (ValueError, TypeError):
            pass

    # ---- Validation ----

    def clean_check_in(self):
        check_in = self.cleaned_data["check_in"]
        if check_in < date.today():
            raise forms.ValidationError(_("Дата заезда не может быть в прошлом."))
        return check_in

    def clean(self):
        cleaned   = super().clean()
        check_in  = cleaned.get("check_in")
        check_out = cleaned.get("check_out")
        category  = cleaned.get("room_category")
        adults    = cleaned.get("adults", 1)
        children  = cleaned.get("children", 0)

        if check_in and check_out:
            if check_out <= check_in:
                self.add_error("check_out", _("Дата выезда должна быть позже даты заезда."))
            elif (check_out - check_in).days > 60:
                self.add_error("check_out", _("Максимальный срок бронирования — 60 ночей."))

        # Capacity check
        if category and (adults + (children or 0)) > category.max_guests:
            raise forms.ValidationError(
                _(f"Категория «{category.name}» вмещает максимум {category.max_guests} гостей.")
            )

        # Room belongs to selected category
        room = cleaned.get("room")
        if room and category and room.category != category:
            self.add_error("room", _("Выбранный номер не принадлежит этой категории."))

        return cleaned


# ---------------------------------------------------------------------------
# BookingCancelForm
# ---------------------------------------------------------------------------

class BookingCancelForm(forms.Form):
    reason = forms.CharField(
        label=_("Причина отмены"), required=False,
        widget=forms.Textarea(attrs={"class": _INPUT, "rows": 3}),
    )
    confirm = forms.BooleanField(
        label=_("Я подтверждаю отмену бронирования"),
        required=True,
        widget=forms.CheckboxInput(attrs={"class": _CHECK}),
        error_messages={"required": _("Необходимо подтвердить отмену.")},
    )


# ---------------------------------------------------------------------------
# BookingStaffForm  (staff CRUD)
# ---------------------------------------------------------------------------

class BookingStaffForm(forms.Form):
    """
    Extended form for staff: all fields + internal notes + status override.
    Used in dashboard for creating/editing bookings manually.
    """

    # ---- Contact ----
    guest_last_name  = forms.CharField(label=_("Фамилия"),  max_length=150,
                                       widget=forms.TextInput(attrs={"class": _INPUT}))
    guest_first_name = forms.CharField(label=_("Имя"),      max_length=150,
                                       widget=forms.TextInput(attrs={"class": _INPUT}))
    guest_patronymic = forms.CharField(label=_("Отчество"), max_length=150, required=False,
                                       widget=forms.TextInput(attrs={"class": _INPUT}))
    guest_phone = forms.CharField(
        label=_("Телефон"), max_length=20, validators=[phone_validator],
        widget=forms.TextInput(attrs={
            "class": _INPUT, 
            "type": "tel",
            "data-mask": "+7 (000) 000-00-00",
            "data-mask-placeholder": "_"
        }),
    )
    guest_email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={"class": _INPUT}),
    )

    # ---- Room ----
    room_category = forms.ModelChoiceField(
        label=_("Категория"),
        queryset=RoomCategory.objects.filter(is_active=True).order_by("sort_order"),
        widget=forms.Select(attrs={"class": _SELECT}),
        empty_label=_("— Выберите —"),
    )
    room = forms.ModelChoiceField(
        label=_("Номер"), queryset=Room.objects.none(), required=False,
        widget=forms.Select(attrs={"class": _SELECT}),
        empty_label=_("— Автоматически —"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Load all rooms with custom display
        rooms = Room.objects.select_related('category').order_by("category__name", "floor", "number", "subdivision")
        choices = [("", _("— Автоматически —"))]
        
        for room in rooms:
            occupancy_info = ""
            if room.max_concurrent_bookings > 1:
                current = room.get_current_occupancy_count()
                occupancy_info = f" ({current}/{room.max_concurrent_bookings})"
            
            label = f"{room.category.name} - {room.full_number}{occupancy_info}"
            choices.append((room.id, label))
        
        self.fields["room"].choices = choices

    # ---- Dates ----
    check_in  = forms.DateField(label=_("Заезд"),
                                widget=forms.DateInput(attrs={"class": _INPUT, "type": "date"}))
    check_out = forms.DateField(label=_("Выезд"),
                                widget=forms.DateInput(attrs={"class": _INPUT, "type": "date"}))

    # ---- Guests ----
    adults   = forms.IntegerField(label=_("Взрослых"), min_value=1, max_value=10, initial=2,
                                  widget=forms.NumberInput(attrs={"class": _INPUT}))
    children = forms.IntegerField(label=_("Детей"),    min_value=0, max_value=8,  initial=0,
                                  widget=forms.NumberInput(attrs={"class": _INPUT}))

    # ---- Optional ----
    organization = forms.ModelChoiceField(
        label=_("Организация"),
        queryset=Organization.objects.filter(is_active=True).order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": _SELECT}),
        empty_label=_("— Частное лицо —"),
    )
    source = forms.ChoiceField(
        label=_("Источник"),
        choices=[("", "—")] + list(__import__(
            "apps.bookings.models", fromlist=["BookingSource"]
        ).BookingSource.choices),
        widget=forms.Select(attrs={"class": _SELECT}),
        required=False,
    )
    arrival_time   = forms.TimeField(label=_("Время прибытия"), required=False,
                                     widget=forms.TimeInput(attrs={"class": _INPUT, "type": "time"}))
    special_requests = forms.CharField(label=_("Пожелания"), required=False,
                                       widget=forms.Textarea(attrs={"class": _INPUT, "rows": 2}))
    internal_notes   = forms.CharField(label=_("Внутренние заметки"), required=False,
                                       widget=forms.Textarea(attrs={"class": _INPUT, "rows": 2}))
    discount_amount = forms.DecimalField(
        label=_("Скидка (₽)"), min_value=0, initial=0, required=False,
        widget=forms.NumberInput(attrs={"class": _INPUT, "step": "0.01"}),
    )
    discount_reason = forms.CharField(label=_("Причина скидки"), max_length=200, required=False,
                                      widget=forms.TextInput(attrs={"class": _INPUT}))

    def clean(self):
        cleaned   = super().clean()
        check_in  = cleaned.get("check_in")
        check_out = cleaned.get("check_out")
        if check_in and check_out:
            if check_out <= check_in:
                self.add_error("check_out", _("Дата выезда должна быть позже даты заезда."))
        return cleaned


# ---------------------------------------------------------------------------
# BookingFilterForm  (staff list filter)
# ---------------------------------------------------------------------------

class BookingFilterForm(forms.Form):
    from apps.bookings.models import BookingStatus as _BS

    q = forms.CharField(
        label=_("Поиск"), required=False,
        widget=forms.TextInput(attrs={
            "class": _INPUT,
            "placeholder": _("Номер брони, имя, email…"),
        }),
    )
    status = forms.ChoiceField(
        label=_("Статус"), required=False,
        choices=[("", _("Все статусы"))] + list(_BS.choices),
        widget=forms.Select(attrs={"class": _SELECT}),
    )
    check_in_from = forms.DateField(
        label=_("Заезд с"), required=False,
        widget=forms.DateInput(attrs={"class": _INPUT, "type": "date"}),
    )
    check_in_to = forms.DateField(
        label=_("Заезд по"), required=False,
        widget=forms.DateInput(attrs={"class": _INPUT, "type": "date"}),
    )
    category = forms.ModelChoiceField(
        label=_("Категория"), required=False,
        queryset=RoomCategory.objects.filter(is_active=True).order_by("sort_order"),
        widget=forms.Select(attrs={"class": _SELECT}),
        empty_label=_("Все категории"),
    )
