"""notifications/urls.py — mounted at /notifications/ in config/urls.py"""

from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    # In-app notification actions
    path("read/<int:pk>/",  views.MarkNotificationReadView.as_view(),     name="mark_read"),
    path("read-all/",       views.MarkAllNotificationsReadView.as_view(), name="mark_all_read"),

    # Contact messages (staff dashboard)
    path("messages/",           views.ContactMessageListView.as_view(),   name="contact_messages"),
    path("messages/<int:pk>/",  views.ContactMessageDetailView.as_view(), name="contact_message_detail"),

    # Email log (staff)
    path("email-log/",          views.EmailLogListView.as_view(),         name="email_log"),
    path("email-log/<int:pk>/", views.EmailLogDetailView.as_view(),       name="email_log_detail"),
]
