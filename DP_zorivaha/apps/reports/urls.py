"""
apps/reports/urls.py — mounted at /reports/ in config/urls.py
"""

from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    # ── HTML views ──────────────────────────────────────────────
    path("",                    views.ReportIndexView.as_view(),    name="index"),
    path("revenue/",            views.RevenueReportView.as_view(),  name="revenue"),
    path("occupancy/",          views.OccupancyReportView.as_view(),name="occupancy"),

    # ── PDF downloads ────────────────────────────────────────────
    path("pdf/bookings/",       views.BookingReportPDFView.as_view(),   name="bookings_pdf"),
    path("pdf/clients/",        views.ClientReportPDFView.as_view(),    name="clients_pdf"),
    path("pdf/occupancy/",      views.OccupancyReportPDFView.as_view(), name="occupancy_pdf"),

    # ── Excel downloads ──────────────────────────────────────────
    path("excel/bookings/",     views.BookingReportExcelView.as_view(), name="bookings_excel"),
]
