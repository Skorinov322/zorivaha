"""
apps/reports/views.py

Report views — all require manager/admin role.

PDF endpoints:
  /reports/pdf/bookings/    — бронирования за период
  /reports/pdf/clients/     — список клиентов
  /reports/pdf/occupancy/   — загрузка номеров

Excel endpoints:
  /reports/excel/bookings/  — бронирования (xlsx)

HTML views:
  /reports/                 — индекс отчётов
  /reports/revenue/         — выручка по месяцам
  /reports/occupancy/       — загрузка по категориям
"""

from datetime import date

from django.views.generic import TemplateView
from django.views import View

from apps.core.permissions import ManagerRequiredMixin
from .selectors import get_revenue_by_month, get_occupancy_by_category
from .services import (
    generate_bookings_pdf,
    generate_clients_pdf,
    generate_occupancy_pdf,
    generate_bookings_excel,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date_range(request) -> tuple[date, date]:
    """Parse start/end from GET params, default to current month."""
    today = date.today()
    try:
        start = date.fromisoformat(request.GET.get("start", "")) if request.GET.get("start") else today.replace(day=1)
        end   = date.fromisoformat(request.GET.get("end",   "")) if request.GET.get("end")   else today
    except ValueError:
        start = today.replace(day=1)
        end   = today
    return start, end


# ---------------------------------------------------------------------------
# HTML views
# ---------------------------------------------------------------------------

class ReportIndexView(ManagerRequiredMixin, TemplateView):
    template_name = "reports/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_year"] = date.today().year
        ctx["year_range"]   = range(date.today().year, date.today().year - 5, -1)
        return ctx


class RevenueReportView(ManagerRequiredMixin, TemplateView):
    template_name = "reports/revenue.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        year = int(self.request.GET.get("year", date.today().year))
        ctx["year"]         = year
        ctx["monthly_data"] = get_revenue_by_month(year)
        ctx["year_range"]   = range(date.today().year, date.today().year - 5, -1)
        return ctx


class OccupancyReportView(ManagerRequiredMixin, TemplateView):
    template_name = "reports/occupancy.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = _parse_date_range(self.request)
        ctx["start"]          = start
        ctx["end"]            = end
        ctx["occupancy_data"] = get_occupancy_by_category(start, end)
        return ctx


# ---------------------------------------------------------------------------
# PDF views
# ---------------------------------------------------------------------------

class BookingReportPDFView(ManagerRequiredMixin, View):
    """PDF: бронирования за период."""

    def get(self, request):
        start, end = _parse_date_range(request)
        return generate_bookings_pdf(start, end)


class ClientReportPDFView(ManagerRequiredMixin, View):
    """PDF: список клиентов с фильтрами."""

    def get(self, request):
        return generate_clients_pdf(
            search=request.GET.get("q", ""),
            loyalty_tier=request.GET.get("loyalty_tier", ""),
            status=request.GET.get("status", ""),
        )


class OccupancyReportPDFView(ManagerRequiredMixin, View):
    """PDF: загрузка номеров за период."""

    def get(self, request):
        start, end = _parse_date_range(request)
        return generate_occupancy_pdf(start, end)


# ---------------------------------------------------------------------------
# Excel views
# ---------------------------------------------------------------------------

class BookingReportExcelView(ManagerRequiredMixin, View):
    """Excel: бронирования за период."""

    def get(self, request):
        start, end = _parse_date_range(request)
        return generate_bookings_excel(start, end)
