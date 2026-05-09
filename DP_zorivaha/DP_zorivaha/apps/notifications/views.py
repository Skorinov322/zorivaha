"""
notifications/views.py

Staff views for email log monitoring, in-app notifications, and contact messages.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

from apps.core.permissions import ManagerRequiredMixin, ReceptionistRequiredMixin
from .models import EmailLog, PushNotification, ContactMessage, ContactReply


# ---------------------------------------------------------------------------
# In-app notification actions
# ---------------------------------------------------------------------------

class MarkNotificationReadView(LoginRequiredMixin, View):
    """Mark a single notification as read and redirect to its action_url."""
    login_url = "/auth/login/"

    def get(self, request, pk):
        notif = get_object_or_404(PushNotification, pk=pk, recipient=request.user)
        notif.mark_read()
        return redirect(notif.action_url or "/dashboard/")


class MarkAllNotificationsReadView(LoginRequiredMixin, View):
    """Mark all unread notifications as read for the current user."""
    login_url = "/auth/login/"

    def post(self, request):
        PushNotification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return redirect(request.META.get("HTTP_REFERER", "/dashboard/"))


# ---------------------------------------------------------------------------
# Contact messages — staff dashboard
# ---------------------------------------------------------------------------

class ContactMessageListView(ReceptionistRequiredMixin, View):
    """Staff: list of all contact form messages."""
    template_name = "notifications/contact_messages.html"

    def get(self, request):
        status_filter = request.GET.get("status", "")
        qs = ContactMessage.objects.select_related("sender_user", "assigned_to").order_by("-created_at")
        if status_filter:
            qs = qs.filter(status=status_filter)

        counts = {
            "new":      ContactMessage.objects.filter(status="new").count(),
            "in_work":  ContactMessage.objects.filter(status="in_work").count(),
            "answered": ContactMessage.objects.filter(status="answered").count(),
            "closed":   ContactMessage.objects.filter(status="closed").count(),
            "total":    ContactMessage.objects.count(),
        }
        counts_list = [
            ("new",      "Новые",    "#dc3545", "envelope-exclamation", counts["new"]),
            ("in_work",  "В работе", "#0d6efd", "hourglass-split",      counts["in_work"]),
            ("answered", "Отвечено", "#28a745", "check-circle",         counts["answered"]),
            ("closed",   "Закрыто",  "#6c757d", "x-circle",             counts["closed"]),
        ]
        return render(request, self.template_name, {
            "messages_qs":    qs,
            "counts":         counts,
            "counts_list":    counts_list,
            "status_filter":  status_filter,
            "status_choices": ContactMessage.Status.choices,
        })


class ContactMessageDetailView(ReceptionistRequiredMixin, View):
    """Staff: view a contact message thread and reply."""
    template_name = "notifications/contact_message_detail.html"

    def get(self, request, pk):
        msg = get_object_or_404(ContactMessage.objects.select_related("sender_user", "assigned_to"), pk=pk)
        # Auto-assign and move to in_work if new
        if msg.status == ContactMessage.Status.NEW:
            msg.status = ContactMessage.Status.IN_WORK
            if not msg.assigned_to:
                msg.assigned_to = request.user
            msg.save(update_fields=["status", "assigned_to", "updated_at"])
        replies = msg.replies.select_related("author").all()
        return render(request, self.template_name, {"msg": msg, "replies": replies})

    def post(self, request, pk):
        msg = get_object_or_404(ContactMessage, pk=pk)
        body = request.POST.get("body", "").strip()
        action = request.POST.get("action", "reply")

        if body and action == "reply":
            # Save staff reply
            ContactReply.objects.create(
                message=msg,
                author=request.user,
                body=body,
                is_staff_reply=True,
            )
            msg.status = ContactMessage.Status.ANSWERED
            msg.save(update_fields=["status", "updated_at"])

            # Notify guest if they have an account
            if msg.sender_user:
                PushNotification.objects.create(
                    recipient=msg.sender_user,
                    notification_type=PushNotification.NotificationType.CONTACT_FORM,
                    title=f"Ответ на ваше обращение: {msg.subject or 'Без темы'}",
                    body=body[:200] + ("…" if len(body) > 200 else ""),
                    action_url=f"/cabinet/messages/{msg.pk}/",
                )
            messages.success(request, "Ответ отправлен.")

        elif action == "close":
            msg.status = ContactMessage.Status.CLOSED
            msg.save(update_fields=["status", "updated_at"])
            messages.info(request, "Обращение закрыто.")
            return redirect("notifications:contact_messages")

        elif action == "reopen":
            msg.status = ContactMessage.Status.IN_WORK
            msg.save(update_fields=["status", "updated_at"])
            messages.info(request, "Обращение переоткрыто.")

        return redirect("notifications:contact_message_detail", pk=pk)


# ---------------------------------------------------------------------------
# Contact messages — guest cabinet
# ---------------------------------------------------------------------------

class GuestContactMessagesView(LoginRequiredMixin, View):
    """Guest: list of their own contact messages."""
    template_name = "accounts/contact_messages.html"
    login_url = "/auth/login/"

    def get(self, request):
        msgs = ContactMessage.objects.filter(
            sender_user=request.user
        ).prefetch_related("replies").order_by("-created_at")
        return render(request, self.template_name, {"messages_qs": msgs})


class GuestContactMessageDetailView(LoginRequiredMixin, View):
    """Guest: view their message thread."""
    template_name = "accounts/contact_message_detail.html"
    login_url = "/auth/login/"

    def get(self, request, pk):
        msg = get_object_or_404(ContactMessage, pk=pk, sender_user=request.user)
        replies = msg.replies.select_related("author").all()
        # Mark staff replies as read
        replies.filter(is_staff_reply=True, is_read_by_guest=False).update(is_read_by_guest=True)
        return render(request, self.template_name, {"msg": msg, "replies": replies})


# ---------------------------------------------------------------------------
# Email log (staff)
# ---------------------------------------------------------------------------

class EmailLogListView(ManagerRequiredMixin, View):
    """Staff: list of all sent emails with status and filters."""
    template_name = "notifications/email_log.html"

    def get(self, request):
        qs = (
            EmailLog.objects
            .select_related("booking")
            .order_by("-created_at")
        )
        status     = request.GET.get("status", "")
        email_type = request.GET.get("type", "")
        search     = request.GET.get("q", "")
        if status:     qs = qs.filter(status=status)
        if email_type: qs = qs.filter(email_type=email_type)
        if search:     qs = qs.filter(recipient_email__icontains=search)

        from django.core.paginator import Paginator
        paginator = Paginator(qs, 30)
        page      = paginator.get_page(request.GET.get("page", 1))

        return render(request, self.template_name, {
            "page_obj": page, "logs": page.object_list,
            "is_paginated": page.has_other_pages(),
            "status_choices": EmailLog.EmailStatus.choices,
            "type_choices":   EmailLog.EmailType.choices,
            "filters": {"status": status, "type": email_type, "q": search},
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
            EmailLog.objects.select_related("booking", "recipient_user"), pk=pk,
        )
        meta_rows = [
            ("ID", log.pk), ("Тип", log.get_email_type_display()),
            ("Получатель", log.recipient_email), ("Имя", log.recipient_name or "—"),
            ("Тема", log.subject), ("Статус", log.get_status_display()),
            ("Создано", log.created_at.strftime("%d.%m.%Y %H:%M:%S")),
            ("Отправлено", log.sent_at.strftime("%d.%m.%Y %H:%M:%S") if log.sent_at else "—"),
            ("Попыток", log.retry_count), ("Celery task", log.task_id or "—"),
        ]
        return render(request, self.template_name, {"log": log, "meta_rows": meta_rows})


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
