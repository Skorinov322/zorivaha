"""
Cabinet + user management URL patterns.
Mounted at /cabinet/ in config/urls.py.
"""

from django.urls import path

from . import views, admin_views

app_name = "accounts"

urlpatterns = [
    # ---- Personal cabinet ----
    path("",                          views.CabinetDashboardView.as_view(),  name="cabinet"),
    path("profile/",                  views.ProfileUpdateView.as_view(),     name="profile"),
    path("password/",                 views.PasswordChangeView.as_view(),    name="password_change"),
    path("bookings/",                 views.MyBookingsView.as_view(),        name="my_bookings"),
    path("bookings/<uuid:pk>/",       views.MyBookingDetailView.as_view(),   name="my_booking_detail"),
    path("history/",                  views.StayHistoryView.as_view(),       name="stay_history"),

    # ---- User management (ADMIN+) ----
    path("users/",                    admin_views.UserListView.as_view(),         name="user_list"),
    path("users/<int:pk>/",           admin_views.UserDetailView.as_view(),       name="user_detail"),
    path("users/<int:pk>/assign-role/", admin_views.AssignRoleView.as_view(),     name="assign_role"),
    path("users/<int:pk>/toggle/",    admin_views.ToggleUserActiveView.as_view(), name="toggle_user"),
]
