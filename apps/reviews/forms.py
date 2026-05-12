"""
reviews/forms.py

Формы для работы с отзывами.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Review, ReviewResponse


class ReviewForm(forms.ModelForm):
    """Форма создания отзыва гостем"""

    class Meta:
        model = Review
        fields = [
            "room_category",
            "overall_rating",
            "cleanliness_rating",
            "comfort_rating",
            "staff_rating",
            "value_rating",
            "location_rating",
            "title",
            "text",
            "pros",
            "cons",
        ]
        widgets = {
            "overall_rating": forms.RadioSelect(),
            "cleanliness_rating": forms.RadioSelect(),
            "comfort_rating": forms.RadioSelect(),
            "staff_rating": forms.RadioSelect(),
            "value_rating": forms.RadioSelect(),
            "location_rating": forms.RadioSelect(),
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Краткое описание вашего впечатления",
            }),
            "text": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Расскажите подробнее о вашем проживании...",
            }),
            "pros": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Что вам понравилось?",
            }),
            "cons": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Что можно улучшить?",
            }),
        }

    def __init__(self, *args, available_categories=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room_category"].required = False
        self.fields["room_category"].empty_label = _("Общий отзыв о гостинице")
        if available_categories is not None:
            self.fields["room_category"].queryset = available_categories

        # Добавляем классы для звездочек
        rating_fields = [
            "overall_rating",
            "cleanliness_rating",
            "comfort_rating",
            "staff_rating",
            "value_rating",
            "location_rating",
        ]
        for field_name in rating_fields:
            self.fields[field_name].widget.attrs.update({
                "class": "rating-input"
            })


class ReviewModerationForm(forms.Form):
    """Форма модерации отзыва"""

    action = forms.ChoiceField(
        label=_("Действие"),
        choices=[
            ("approve", _("Одобрить")),
            ("reject", _("Отклонить")),
        ],
        widget=forms.RadioSelect(),
    )
    comment = forms.CharField(
        label=_("Комментарий"),
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Причина отклонения или заметки...",
        }),
    )


class ReviewResponseForm(forms.ModelForm):
    """Форма ответа администрации на отзыв"""

    class Meta:
        model = ReviewResponse
        fields = ["text", "author_position"]
        widgets = {
            "text": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Ваш ответ на отзыв...",
            }),
            "author_position": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Например: Администратор, Менеджер",
            }),
        }
