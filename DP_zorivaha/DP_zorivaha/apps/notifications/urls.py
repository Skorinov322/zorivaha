"""notifications/urls.py — mounted at /notifications/ in config/urls.py"""

from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("email-log/",          views.EmailLogListView.as_view(),   name="email_log"),
    path("email-log/<int:pk>/", views.EmailLogDetailView.as_view(), name="email_log_detail"),
]
