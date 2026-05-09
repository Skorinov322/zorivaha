"""
notifications/views.py

Staff views for email log monitoring.
"""

from django.shortcuts import get_object_or_404, render
from django.views import View

from apps.core.permissions import ManagerRequiredMixin
from .models import EmailLog


class EmailLogListView(ManagerRequiredMixin, View):
    """Staff: list of all sent emails with status and filters."""
    template_name = "notifications/email_log.html"

    def get(self, request):
        qs = (
            EmailLog.objects
            .select_related("booking")
            .order_by("-created_at")
        )

        # Filters
        status     = request.GET.get("status", "")
        email_type = request.GET.get("type", "")
        search     = request.GET.get("q", "")

        if status:
            qs = qs.filter(status=status)
        if email_type:
            qs = qs.filter(email_type=email_type)
        if search:
            qs = qs.filter(recipient_email__icontains=search)

        # Pagination
        from django.core.paginator import Paginator
        paginator = Paginator(qs, 30)
        page      = paginator.get_page(request.GET.get("page", 1))

        return render(request, self.template_name, {
            "page_obj":     page,
            "logs":         page.object_list,
            "is_paginated": page.has_other_pages(),
            "status_choices":     EmailLog.EmailStatus.choices,
            "type_choices":       EmailLog.EmailType.choices,
            "filters": {
                "status": status,
                "type":   email_type,
                "q":      search,
            },
            # Summary counts
            "counts": {
                "total":   EmailLog.objects.count(),
                "sent":    EmailLog.objects.filter(status="sent").count(),
                "failed":  EmailLog.objects.filter(status="failed").count(),
                "pending": EmailLog.objects.filter(status="pending").count(),
            },
        })


class EmailLogDetailView(ManagerRequiredMixin, View):
    """Staff: single email log entry with HTML preview."""
    template_name = "notifications/email_log_detail.html"

    def get(self, request, pk):
        log = get_object_or_404(
            EmailLog.objects.select_related("booking", "recipient_user"),
            pk=pk,
        )
        meta_rows = [
            ("ID",           log.pk),
            ("Тип",          log.get_email_type_display()),
            ("Получатель",   log.recipient_email),
            ("Имя",          log.recipient_name or "—"),
            ("Тема",         log.subject),
            ("Статус",       log.get_status_display()),
            ("Создано",      log.created_at.strftime("%d.%m.%Y %H:%M:%S")),
            ("Отправлено",   log.sent_at.strftime("%d.%m.%Y %H:%M:%S") if log.sent_at else "—"),
            ("Попыток",      log.retry_count),
            ("Celery task",  log.task_id or "—"),
        ]
        return render(request, self.template_name, {"log": log, "meta_rows": meta_rows})
