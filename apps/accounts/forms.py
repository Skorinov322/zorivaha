"""Account forms."""

from django import forms
from django.contrib.auth import authenticate, password_validation
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from .models import User, UserRole


# ---------------------------------------------------------------------------
# RegisterForm
# ---------------------------------------------------------------------------

class RegisterForm(forms.Form):
    """
    Guest registration form.
    Fields: last_name, first_name, patronymic, email, password1, password2.
    """

    last_name = forms.CharField(
        label=_("Фамилия"),
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": _("Иванов"),
            "autocomplete": "family-name",
        }),
    )
    first_name = forms.CharField(
        label=_("Имя"),
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": _("Иван"),
            "autocomplete": "given-name",
        }),
    )
    patronymic = forms.CharField(
        label=_("Отчество"),
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": _("Иванович (необязаостиницано)"),
            "autocomplete": "additional-name",
        }),
    )
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "example@mail.ru",
            "autocomplete": "email",
        }),
    )
    password1 = forms.CharField(
        label=_("Пароль"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": _("Минимум 8 символов"),
            "autocomplete": "new-password",
            "id": "id_reg_password1",
        }),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label=_("Подтверждение пароля"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": _("Повторите пароль"),
            "autocomplete": "new-password",
        }),
    )
    agree_terms = forms.BooleanField(
        label=_("Я согласен с условиями использования и политикой конфиденциальности"),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        error_messages={"required": _("Необходимо принять условия использования.")},
    )

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                _("Пользоваостиница с таким email уже зарегистрирован.")
            )
        return email

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1", "")
        p2 = self.cleaned_data.get("password2", "")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_("Пароли не совпадают."))
        return p2

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password1")
        if password:
            password_validation.validate_password(password)
        return cleaned

    def save(self) -> User:
        """Create and return a new guest user."""
        from .models import UserRole
        data = self.cleaned_data
        user = User.objects.create_user(
            email=data["email"],
            password=data["password1"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            patronymic=data.get("patronymic", ""),
            role=UserRole.USER,
            is_active=True,
        )
        return user


# ---------------------------------------------------------------------------
# LoginForm
# ---------------------------------------------------------------------------

class LoginForm(forms.Form):
    """
    Email + password login form with remember-me option.
    """

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "example@mail.ru",
            "autocomplete": "email",
            "autofocus": True,
        }),
    )
    password = forms.CharField(
        label=_("Пароль"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": _("Ваш пароль"),
            "autocomplete": "current-password",
        }),
    )
    remember_me = forms.BooleanField(
        label=_("Запомнить меня"),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self._user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email", "").lower().strip()
        password = cleaned.get("password", "")

        if email and password:
            self._user_cache = authenticate(
                self.request, email=email, password=password
            )
            if self._user_cache is None:
                raise forms.ValidationError(
                    _("Неверный email или пароль. Проверьте данные и попробуйте снова."),
                    code="invalid_login",
                )
            if not self._user_cache.is_active:
                raise forms.ValidationError(
                    _("Ваша учётная запись отключена. Обратитесь к администратору."),
                    code="inactive",
                )
        return cleaned

    def get_user(self) -> User:
        return self._user_cache


# ---------------------------------------------------------------------------
# ProfileUpdateForm
# ---------------------------------------------------------------------------

class ProfileUpdateForm(forms.ModelForm):
    """Edit personal profile in the cabinet."""

    class Meta:
        model = User
        fields = [
            "email", "first_name", "last_name", "patronymic", "phone",
            "date_of_birth",
            "preferred_language",
        ]
        widgets = {
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "example@mail.ru",
                "autocomplete": "email",
            }),
            "first_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Имя"),
            }),
            "last_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Фамилия"),
            }),
            "patronymic": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Отчество (необязательно)"),
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "+7 (___) ___-__-__",
                "type": "tel",
                "data-mask": "+7 (000) 000-00-00",
                "data-mask-placeholder": "_"
            }),
            "date_of_birth": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }, format="%Y-%m-%d"),
            "preferred_language": forms.Select(attrs={"class": "form-select"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        qs = User.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("Пользователь с таким email уже зарегистрирован."))
        return email


# ---------------------------------------------------------------------------
# AvatarUploadForm
# ---------------------------------------------------------------------------

class AvatarUploadForm(forms.ModelForm):
    """Standalone avatar upload — handled via AJAX or separate POST."""

    class Meta:
        model = User
        fields = ["avatar"]
        widgets = {
            "avatar": forms.FileInput(attrs={
                "class": "form-control",
                "accept": "image/jpeg,image/png,image/webp",
            }),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar:
            # Max 5 MB
            if avatar.size > 5 * 1024 * 1024:
                raise forms.ValidationError(_("Размер файла не должен превышать 5 МБ."))
            if not avatar.content_type.startswith("image/"):
                raise forms.ValidationError(_("Загрузите изображение (JPEG, PNG или WebP)."))
        return avatar


# ---------------------------------------------------------------------------
# PasswordChangeForm
# ---------------------------------------------------------------------------

class CabinetPasswordChangeForm(forms.Form):
    """Change password from inside the personal cabinet."""

    current_password = forms.CharField(
        label=_("Текущий пароль"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "current-password",
        }),
    )
    new_password1 = forms.CharField(
        label=_("Новый пароль"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "new-password",
        }),
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label=_("Подтверждение нового пароля"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "new-password",
        }),
    )

    def __init__(self, user: User, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        pwd = self.cleaned_data.get("current_password")
        if not self.user.check_password(pwd):
            raise forms.ValidationError(_("Неверный текущий пароль."))
        return pwd

    def clean_new_password2(self):
        p1 = self.cleaned_data.get("new_password1", "")
        p2 = self.cleaned_data.get("new_password2", "")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_("Новые пароли не совпадают."))
        return p2

    def clean(self):
        cleaned = super().clean()
        new_pwd = cleaned.get("new_password1")
        if new_pwd:
            password_validation.validate_password(new_pwd, self.user)
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data["new_password1"])
        self.user.save(update_fields=["password"])
        return self.user


class AdminSetUserPasswordForm(forms.Form):
    """Set a new password for a user from the management dashboard."""

    new_password1 = forms.CharField(
        label=_("Новый пароль"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "new-password",
        }),
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label=_("Подтверждение нового пароля"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "new-password",
        }),
    )

    def __init__(self, user: User, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_password2(self):
        p1 = self.cleaned_data.get("new_password1", "")
        p2 = self.cleaned_data.get("new_password2", "")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_("Пароли не совпадают."))
        return p2

    def clean(self):
        cleaned = super().clean()
        new_pwd = cleaned.get("new_password1")
        if new_pwd:
            password_validation.validate_password(new_pwd, self.user)
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data["new_password1"])
        self.user.save(update_fields=["password"])
        return self.user


# ---------------------------------------------------------------------------
# RoleAssignForm
# ---------------------------------------------------------------------------

class RoleAssignForm(forms.Form):
    """
    Role assignment form — shown only to ADMIN+ users.
    `assignable_roles` is injected at instantiation time so the choices
    are always scoped to what the current actor is allowed to assign.
    """

    role = forms.ChoiceField(
        label=_("Новая роль"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, assignable_roles: list = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = assignable_roles or UserRole.choices

    def clean_role(self):
        role = self.cleaned_data["role"]
        valid = [r.value for r in UserRole]
        if role not in valid:
            raise forms.ValidationError(_("Недопустимая роль."))
        return role


# ---------------------------------------------------------------------------
# GuestOrganizationForm
# ---------------------------------------------------------------------------

_guest_phone_validator = RegexValidator(
    regex=r"^\+?[\d\s\-\(\)]{7,20}$",
    message=_("Введите корректный номер телефона."),
)

_INP = "form-control"


class GuestOrganizationForm(forms.Form):
    """Organization creation form for guest personal cabinet."""

    name = forms.CharField(
        label=_("Название организации"),
        max_length=255,
        widget=forms.TextInput(attrs={"class": _INP, "placeholder": "ООО «Название компании»"}),
    )
    inn = forms.CharField(
        label=_("ИНН"),
        max_length=12,
        widget=forms.TextInput(attrs={"class": _INP, "placeholder": "1234567890"}),
        validators=[RegexValidator(
            regex=r"^\d{10}$|^\d{12}$",
            message=_("ИНН должен содержать 10 или 12 цифр"),
        )],
    )
    kpp = forms.CharField(
        label=_("КПП"),
        max_length=9,
        required=False,
        widget=forms.TextInput(attrs={"class": _INP, "placeholder": "123456789"}),
        validators=[RegexValidator(
            regex=r"^\d{9}$",
            message=_("КПП должен содержать 9 цифр"),
        )],
    )
    legal_address = forms.CharField(
        label=_("Юридический адрес"),
        widget=forms.Textarea(attrs={"class": _INP, "rows": 2}),
    )
    contact_person = forms.CharField(
        label=_("Контактное лицо"),
        max_length=200,
        widget=forms.TextInput(attrs={"class": _INP, "placeholder": "Иванов Иван Иванович"}),
    )
    phone = forms.CharField(
        label=_("Телефон"),
        max_length=20,
        required=False,
        validators=[_guest_phone_validator],
        widget=forms.TextInput(attrs={
            "class": _INP,
            "placeholder": "+7 (___) ___-__-__",
            "type": "tel",
        }),
    )
    email = forms.EmailField(
        label=_("Email"),
        required=False,
        widget=forms.EmailInput(attrs={"class": _INP, "placeholder": "info@company.ru"}),
    )

    def clean(self):
        cleaned = super().clean()
        from apps.crm.models import Organization

        name = cleaned.get("name")
        inn = cleaned.get("inn")
        if name and Organization.objects.filter(name=name).exists():
            self.add_error("name", _("Организация с таким названием уже существует."))
        if inn and Organization.objects.filter(inn=inn).exists():
            self.add_error("inn", _("Организация с таким ИНН уже существует."))
        return cleaned
