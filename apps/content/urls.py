"""
content/urls.py

Public URLs for content pages (FAQ, gallery, etc.)
"""

from django.urls import path
from . import views

app_name = "content"

urlpatterns = [
    path("faq/", views.FAQListView.as_view(), name="faq"),
]
