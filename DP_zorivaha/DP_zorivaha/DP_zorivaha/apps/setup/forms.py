"""
Setup wizard form.

Collects the minimum required data to create the first superuser:
  - first_name, last_name (ФИО split into two fields + patronymic)
  - email
  - password (with confirmation)

Validation:
  - Email uniqueness (defensive, should never trigger on first run)
  - Password strength via Django's AUTH_PASSWORD_VALIDATORS
  - Passwords match
"""

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class SetupForm(forms.Form):
    """First-run setup form — creates the initial superuser."""

    # ---- Personal info ----
    first_name = forms.CharField(
        label=_("Имя"),
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": _("Имя"),
            "autofocus": True,
        }),
    )
    last_name = forms.CharField(
        label=_("Фамилия"),
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": _("Фамилия"),
        }),
    )
    patronymic = forms.CharField(
        label=_("Отчество"),
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": _("Отчество (необязательно)"),
        }),
    )

    # ---- Auth ----
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "admin@zorivaha.ru",
        }),
    )
    password1 = forms.CharField(
        label=_("Пароль"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": _("Придумайте пароль"),
            "autocomplete": "new-password",
        }),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label=_("Подтверждение пароля"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": _("Повторите пароль"),
            "autocomplete": "new-password",
        }),
    )

    # ---- Honeypot (bot protection) ----
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        label="",
    )

    def clean_website(self):
        """Honeypot field — must be empty. Bots fill it in."""
        value = self.cleaned_data.get("website", "")
        if value:
            raise forms.ValidationError("Обнаружена автоматическая отправка.")
        return value

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                _("Пользователь с таким email уже существует.")
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
            # Run Django's full password validation suite
            password_validation.validate_password(password)
        return cleaned

    def save(self) -> "User":
        """
        Create and return the first superuser.
        Must be called only after is_valid() returns True.
        """
        from apps.accounts.models import UserRole
        from apps.setup.middleware import invalidate_setup_cache

        data = self.cleaned_data
        user = User.objects.create_superuser(
            email=data["email"],
            password=data["password1"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            role=UserRole.ADMIN,
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )

        # Store patronymic in a dedicated field if it exists on the model,
        # otherwise append to last_name (graceful fallback)
        patronymic = data.get("patronymic", "").strip()
        if patronymic:
            if hasattr(user, "patronymic"):
                user.patronymic = patronymic
                user.save(update_fields=["patronymic"])
            # If no dedicated field, we simply skip — first_name + last_name is enough

        # Immediately invalidate the middleware cache so the next request
        # is served normally without a DB round-trip
        invalidate_setup_cache()

        return user
