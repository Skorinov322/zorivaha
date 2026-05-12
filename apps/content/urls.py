"""
content/urls.py

Public URLs for content pages (FAQ, gallery, etc.)
"""

from django.urls import path
from . import views

app_name = "content"

urlpatterns = [
    path("faq/", views.FAQListView.as_view(), name="faq"),
    # Legal pages
    path("docs/terms/", views.legal_page, {"page_type": "terms"}, name="terms"),
    path("docs/privacy/", views.legal_page, {"page_type": "privacy"}, name="privacy"),
    path("docs/accommodation/", views.legal_page, {"page_type": "accommodation"}, name="accommodation_policy"),
]
