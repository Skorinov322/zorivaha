"""
bookings/urls.py

Guest:
  /bookings/                    → BookingCreateView
  /bookings/<pk>/               → BookingDetailView
  /bookings/<pk>/cancel/        → BookingCancelView
  /bookings/success/<pk>/       → BookingSuccessView

Staff:
  /bookings/staff/              → BookingListStaffView
  /bookings/staff/create/       → BookingCreateStaffView
  /bookings/staff/<pk>/         → BookingDetailStaffView
  /bookings/staff/<pk>/confirm/ → BookingConfirmView
  /bookings/staff/<pk>/checkin/ → BookingCheckInView
  /bookings/staff/<pk>/checkout/→ BookingCheckOutView
  /bookings/staff/<pk>/noshow/  → BookingNoShowView
  /bookings/staff/<pk>/cancel/  → BookingCancelStaffView
  /bookings/staff/<pk>/undo-checkin/  → BookingUndoCheckInView
  /bookings/staff/<pk>/undo-checkout/ → BookingUndoCheckOutView
"""

from django.urls import path
from . import views, ajax, test_views

app_name = "bookings"

urlpatterns = [
    # ---- Guest ----
    path("",                          views.BookingCreateView.as_view(),     name="create"),
    path("<uuid:pk>/",                views.BookingDetailView.as_view(),     name="detail"),
    path("<uuid:pk>/cancel/",         views.BookingCancelView.as_view(),     name="cancel"),
    path("success/<uuid:pk>/",        views.BookingSuccessView.as_view(),    name="success"),
    path("group/<uuid:group_id>/",    views.BookingGroupSuccessView.as_view(), name="group_success"),

    # ---- AJAX ----
    path("rooms-for-category/",       ajax.rooms_for_category,               name="rooms_for_category"),
    path("calculate-prices/",         ajax.calculate_prices,                 name="calculate_prices"),
    
    # ---- Debug/Test ----
    path("test-ajax/",                test_views.test_ajax_page,             name="test_ajax"),
    path("debug-prices/",             test_views.debug_price_calculation,    name="debug_prices"),

    # ---- Staff ----
    path("staff/",                    views.BookingListStaffView.as_view(),         name="staff_list"),
    path("staff/create/",             views.BookingCreateStaffView.as_view(),       name="staff_create"),
    path("staff/<uuid:pk>/",          views.BookingDetailStaffView.as_view(),       name="staff_detail"),
    path("staff/<uuid:pk>/confirm/",  views.BookingConfirmView.as_view(),           name="confirm"),
    path("staff/<uuid:pk>/checkin/",  views.BookingCheckInView.as_view(),           name="checkin"),
    path("staff/<uuid:pk>/checkout/", views.BookingCheckOutView.as_view(),          name="checkout"),
    path("staff/<uuid:pk>/noshow/",   views.BookingNoShowView.as_view(),            name="noshow"),
    path("staff/<uuid:pk>/cancel/",   views.BookingCancelStaffView.as_view(),       name="staff_cancel"),
    path("staff/<uuid:pk>/delete/",   views.BookingDeleteStaffView.as_view(),       name="staff_delete"),
    path("staff/<uuid:pk>/undo-checkin/",  views.BookingUndoCheckInView.as_view(),  name="undo_checkin"),
    path("staff/<uuid:pk>/undo-checkout/", views.BookingUndoCheckOutView.as_view(), name="undo_checkout"),
]
