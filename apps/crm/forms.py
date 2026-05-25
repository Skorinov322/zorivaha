"""
crm/forms.py

Forms:
  ClientProfileForm   — редактирование CRM-профиля клиента
  AdminCommentForm    — добавление комментария администратора
  InteractionForm     — лог взаимодействия с клиентом
  TaskForm            — создание/редактирование задачи
  ClientStatusForm    — быстрая смена статуса клиента
  OrganizationForm    — создание/редактирование организации
"""

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _

from .models import ClientProfile, AdminComment, Interaction, Task, Organization

_C = "form-control"
_S = "form-select"
_K = "form-check-input"


# ---------------------------------------------------------------------------
# ClientProfileForm
# ---------------------------------------------------------------------------

class ClientProfileForm(forms.ModelForm):
    class Meta:
        model  = ClientProfile
        fields = [
            "client_type", "guest_type", "status",
            "organization", "assigned_manager",
            "preferred_room_category", "preferred_floor",
            "dietary_requirements", "special_needs",
            "vip_notes",
        ]
        widgets = {
            "client_type":             forms.Select(attrs={"class": _S}),
            "guest_type":              forms.Select(attrs={"class": _S}),
            "status":                  forms.Select(attrs={"class": _S}),
            "organization":            forms.Select(attrs={"class": _S}),
            "assigned_manager":        forms.Select(attrs={"class": _S}),
            "preferred_room_category": forms.Select(attrs={"class": _S}),
            "preferred_floor":         forms.NumberInput(attrs={"class": _C, "min": 1}),
            "dietary_requirements":    forms.TextInput(attrs={"class": _C}),
            "special_needs":           forms.Textarea(attrs={"class": _C, "rows": 3}),
            "vip_notes":               forms.Textarea(attrs={"class": _C, "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import User, UserRole
        self.fields["assigned_manager"].queryset = User.objects.filter(
            role__in=[UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
        ).order_by("last_name", "first_name")
        self.fields["assigned_manager"].required = False
        self.fields["organization"].required = False
        self.fields["preferred_room_category"].required = False


# ---------------------------------------------------------------------------
# AdminCommentForm
# ---------------------------------------------------------------------------

class AdminCommentForm(forms.ModelForm):
    class Meta:
        model  = AdminComment
        fields = ["body", "is_pinned"]
        widgets = {
            "body":      forms.Textarea(attrs={
                "class": _C, "rows": 3,
                "placeholder": _("Комментарий виден только сотрудникам…"),
            }),
            "is_pinned": forms.CheckboxInput(attrs={"class": _K}),
        }
        labels = {
            "body":      _("Комментарий"),
            "is_pinned": _("Закрепить"),
        }


# ---------------------------------------------------------------------------
# InteractionForm
# ---------------------------------------------------------------------------

class InteractionForm(forms.ModelForm):
    class Meta:
        model  = Interaction
        fields = ["interaction_type", "subject", "body", "outcome", "follow_up_date", "is_resolved"]
        widgets = {
            "interaction_type": forms.Select(attrs={"class": _S}),
            "subject":          forms.TextInput(attrs={"class": _C, "placeholder": _("Тема")}),
            "body":             forms.Textarea(attrs={"class": _C, "rows": 4}),
            "outcome":          forms.TextInput(attrs={"class": _C, "placeholder": _("Краткий итог")}),
            "follow_up_date":   forms.DateInput(attrs={"class": _C, "type": "date"}),
            "is_resolved":      forms.CheckboxInput(attrs={"class": _K}),
        }


# ---------------------------------------------------------------------------
# TaskForm
# ---------------------------------------------------------------------------

class TaskForm(forms.ModelForm):
    class Meta:
        model  = Task
        fields = ["title", "description", "assigned_to", "priority", "due_date"]
        widgets = {
            "title":       forms.TextInput(attrs={"class": _C}),
            "description": forms.Textarea(attrs={"class": _C, "rows": 3}),
            "assigned_to": forms.Select(attrs={"class": _S}),
            "priority":    forms.Select(attrs={"class": _S}),
            "due_date":    forms.DateInput(attrs={"class": _C, "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import User, UserRole
        self.fields["assigned_to"].queryset = User.objects.filter(
            role__in=[UserRole.RECEPTIONIST, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
        ).order_by("last_name", "first_name")


# ---------------------------------------------------------------------------
# ClientStatusForm
# ---------------------------------------------------------------------------

class ClientStatusForm(forms.Form):
    status = forms.ChoiceField(
        label=_("Статус"),
        choices=ClientProfile.ClientStatus.choices,
        widget=forms.Select(attrs={"class": _S}),
    )


# ---------------------------------------------------------------------------
# OrganizationForm
# ---------------------------------------------------------------------------

class OrganizationForm(forms.ModelForm):
    website = forms.CharField(
        label=_("сайт"),
        required=False,
        widget=forms.TextInput(attrs={
            "class": _C,
            "placeholder": "https://example.ru",
        }),
    )

    class Meta:
        model  = Organization
        fields = [
            "name", "short_name", "org_type",
            "inn", "kpp", "ogrn",
            "legal_address", "actual_address",
            "phone", "email", "website", "contact_person",
            "corporate_discount_pct", "credit_limit", "payment_terms_days",
            "assigned_manager", "notes", "is_active",
        ]
        widgets = {
            "name":                    forms.TextInput(attrs={"class": _C}),
            "short_name":              forms.TextInput(attrs={"class": _C}),
            "org_type":                forms.Select(attrs={"class": _S}),
            "inn":                     forms.TextInput(attrs={"class": _C}),
            "kpp":                     forms.TextInput(attrs={"class": _C}),
            "ogrn":                    forms.TextInput(attrs={"class": _C}),
            "legal_address":           forms.Textarea(attrs={"class": _C, "rows": 2}),
            "actual_address":          forms.Textarea(attrs={"class": _C, "rows": 2}),
            "phone":                   forms.TextInput(attrs={"class": _C}),
            "email":                   forms.EmailInput(attrs={"class": _C}),
            "contact_person":          forms.TextInput(attrs={"class": _C}),
            "corporate_discount_pct":  forms.NumberInput(attrs={"class": _C, "step": "0.01"}),
            "credit_limit":            forms.NumberInput(attrs={"class": _C, "step": "0.01"}),
            "payment_terms_days":      forms.NumberInput(attrs={"class": _C, "min": 0}),
            "assigned_manager":        forms.Select(attrs={"class": _S}),
            "notes":                   forms.Textarea(attrs={"class": _C, "rows": 3}),
            "is_active":               forms.CheckboxInput(attrs={"class": _K}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import User, UserRole
        self.fields["assigned_manager"].queryset = User.objects.filter(
            role__in=[UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
        )
        self.fields["assigned_manager"].required = False
        for field_name in ("inn", "kpp", "ogrn", "legal_address", "actual_address",
                           "phone", "email", "contact_person", "notes"):
            self.fields[field_name].required = False
        for field_name in ("corporate_discount_pct", "credit_limit", "payment_terms_days"):
            self.fields[field_name].required = False

    def clean_website(self):
        website = (self.cleaned_data.get("website") or "").strip()
        if not website:
            return ""
        if not website.startswith(("http://", "https://")):
            website = f"https://{website}"
        validator = URLValidator()
        try:
            validator(website)
        except ValidationError:
            raise forms.ValidationError(_("Введите корректный адрес сайта."))
        return website

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("corporate_discount_pct") in (None, ""):
            cleaned["corporate_discount_pct"] = 0
        if cleaned.get("credit_limit") in (None, ""):
            cleaned["credit_limit"] = 0
        if cleaned.get("payment_terms_days") in (None, ""):
            cleaned["payment_terms_days"] = 0
        return cleaned
