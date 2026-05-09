"""
Setup app URL configuration.

/setup/           → SetupIndexView  (GET: form, POST: create superuser)
/setup/complete/  → SetupCompleteView (success page)

Both views return 404 once a superuser exists.
"""

from django.urls import path

from . import views

app_name = "setup"

urlpatterns = [
    path("", views.SetupIndexView.as_view(), name="index"),
    path("complete/", views.SetupCompleteView.as_view(), name="complete"),
]
