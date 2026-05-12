from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("",                                    views.DashboardView.as_view(),         name="index"),
    path("bookings/",                           views.BookingManagementView.as_view(), name="bookings"),
    path("bookings/<uuid:pk>/check-in/",        views.CheckInView.as_view(),           name="check_in"),
    path("bookings/<uuid:pk>/check-out/",       views.CheckOutView.as_view(),          name="check_out"),
    path("rooms/",                              views.RoomManagementView.as_view(),    name="rooms"),
    path("calendar/",                           views.OccupancyCalendarView.as_view(), name="calendar"),
    path("statistics/",                         views.StatisticsView.as_view(),        name="statistics"),
    path("metrics/",                            views.MetricsView.as_view(),           name="metrics"),
    path("gallery/",                            views.GalleryManagementView.as_view(), name="gallery"),
    path("reviews/",                            views.ReviewModerationView.as_view(), name="reviews"),
    path("faq/",                                views.FAQManagementView.as_view(),     name="faq"),
    path("site-content/",                       views.SiteContentPolicyView.as_view(), name="site_content"),
    path("run-migrations/",                     views.RunMigrationsView.as_view(),     name="run_migrations"),
]
