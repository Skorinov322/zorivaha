"""
crm/views.py

Staff CRM views (manager/admin only):
  CrmDashboardView        — метрики, задачи, последние клиенты
  ClientListView          — список клиентов с фильтрами
  ClientDetailView        — профиль клиента: история, комментарии, задачи
  ClientStatusUpdateView  — быстрая смена статуса
  InteractionCreateView   — добавить взаимодействие
  AdminCommentCreateView  — добавить комментарий
  AdminCommentDeleteView  — удалить комментарий
  AdminCommentPinView     — закрепить/открепить комментарий
  TaskListView            — список задач
  TaskCreateView          — создать задачу
  TaskCompleteView        — завершить задачу
  TaskCancelView          — отменить задачу
  OrganizationListView    — список организаций
  OrganizationCreateView  — создать организацию
  OrganizationDetailView  — детали организации
  OrganizationUpdateView  — редактировать организацию
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView, ListView

from apps.core.permissions import ManagerRequiredMixin
from .forms import (
    ClientProfileForm, AdminCommentForm, InteractionForm,
    TaskForm, ClientStatusForm, OrganizationForm,
)
from .models import ClientProfile, AdminComment, Task, Organization
from .selectors import (
    get_all_clients, get_client_profile_detail, get_client_stats,
    get_client_booking_history, get_open_tasks, get_all_tasks,
    get_all_organizations, get_organization_detail,
    get_crm_dashboard_metrics,
)
from .services import (
    update_client_profile, set_client_status,
    add_admin_comment, delete_admin_comment, toggle_pin_comment,
    create_interaction, resolve_interaction,
    create_task, complete_task, cancel_task,
    create_organization, update_organization,
)


# ===========================================================================
# Dashboard
# ===========================================================================

class CrmDashboardView(ManagerRequiredMixin, TemplateView):
    template_name = "crm/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["metrics"]        = get_crm_dashboard_metrics()
        ctx["my_tasks"]       = get_open_tasks(manager=self.request.user)[:8]
        ctx["recent_clients"] = get_all_clients()[:6]
        ctx["quick_links"] = [
            ("Клиенты",       "/crm/clients/",       "bi-people"),
            ("Задачи",        "/crm/tasks/",         "bi-list-task"),
            ("Организации",   "/crm/organizations/", "bi-building"),
            ("Бронирования",  "/bookings/staff/",    "bi-calendar-check"),
        ]
        return ctx


# ===========================================================================
# Clients
# ===========================================================================

class ClientListView(ManagerRequiredMixin, View):
    template_name = "crm/client_list.html"
    paginate_by   = 25

    def get(self, request):
        clients = get_all_clients(
            search=request.GET.get("q", ""),
            status=request.GET.get("status", ""),
            client_type=request.GET.get("client_type", ""),
            loyalty_tier=request.GET.get("loyalty_tier", ""),
        )
        # Manual pagination
        from django.core.paginator import Paginator
        paginator = Paginator(clients, self.paginate_by)
        page      = paginator.get_page(request.GET.get("page", 1))

        return render(request, self.template_name, {
            "page_obj":       page,
            "clients":        page.object_list,
            "is_paginated":   page.has_other_pages(),
            "status_choices": ClientProfile.ClientStatus.choices,
            "type_choices":   ClientProfile.ClientType.choices,
            "tier_choices":   ClientProfile.LoyaltyTier.choices,
            "filters": {
                "q":            request.GET.get("q", ""),
                "status":       request.GET.get("status", ""),
                "client_type":  request.GET.get("client_type", ""),
                "loyalty_tier": request.GET.get("loyalty_tier", ""),
            },
        })


class ClientDetailView(ManagerRequiredMixin, View):
    template_name = "crm/client_detail.html"

    def get(self, request, pk):
        profile = get_client_profile_detail(pk)
        stats   = get_client_stats(profile)

        profile_rows = [
            ("Тип клиента",    profile.get_client_type_display()),
            ("Тип гостя",      profile.get_guest_type_display()),
            ("Лояльность",     profile.get_loyalty_tier_display()),
            ("Баллы",          profile.loyalty_points),
            ("Первый заезд",   profile.first_stay_date.strftime("%d.%m.%Y") if profile.first_stay_date else "—"),
            ("Последний заезд",profile.last_stay_date.strftime("%d.%m.%Y") if profile.last_stay_date else "—"),
        ]
        stat_rows = [
            ("Всего броней",   stats["total"],     "#fff"),
            ("Активных",       stats["active"],    "#ffc107"),
            ("Завершённых",    stats["completed"], "#28a745"),
            ("Отменённых",     stats["cancelled"], "#ff6b6b"),
            ("Ночей",          profile.total_nights, "#6ea8fe"),
            ("Потрачено",      f"{profile.total_spent:,.0f} ₽", "var(--gold)"),
        ]
        tabs = [
            ("bookings",     "Бронирования"),
            ("comments",     "Комментарии"),
            ("interactions", "Взаимодействия"),
            ("tasks",        "Задачи"),
        ]

        return render(request, self.template_name, {
            "profile":          profile,
            "stats":            stats,
            "booking_history":  get_client_booking_history(pk),
            "comment_form":     AdminCommentForm(),
            "interaction_form": InteractionForm(),
            "task_form":        TaskForm(),
            "status_form":      ClientStatusForm(initial={"status": profile.status}),
            "profile_form":     ClientProfileForm(instance=profile),
            "profile_rows":     profile_rows,
            "stat_rows":        stat_rows,
            "tabs":             tabs,
        })

    def post(self, request, pk):
        """Route to the correct sub-action based on hidden 'action' field."""
        profile = get_client_profile_detail(pk)
        action  = request.POST.get("action", "")

        if action == "add_comment":
            form = AdminCommentForm(request.POST)
            if form.is_valid():
                add_admin_comment(
                    profile=profile,
                    author=request.user,
                    body=form.cleaned_data["body"],
                    is_pinned=form.cleaned_data.get("is_pinned", False),
                )
                messages.success(request, "Комментарий добавлен.")
            else:
                messages.error(request, "Ошибка при добавлении комментария.")

        elif action == "add_interaction":
            form = InteractionForm(request.POST)
            if form.is_valid():
                create_interaction(
                    client=profile,
                    staff=request.user,
                    interaction_type=form.cleaned_data["interaction_type"],
                    subject=form.cleaned_data["subject"],
                    body=form.cleaned_data["body"],
                    outcome=form.cleaned_data.get("outcome", ""),
                    follow_up_date=form.cleaned_data.get("follow_up_date"),
                )
                messages.success(request, "Взаимодействие записано.")
            else:
                messages.error(request, "Ошибка при записи взаимодействия.")

        elif action == "add_task":
            form = TaskForm(request.POST)
            if form.is_valid():
                create_task(
                    title=form.cleaned_data["title"],
                    description=form.cleaned_data.get("description", ""),
                    assigned_to=form.cleaned_data["assigned_to"],
                    created_by=request.user,
                    client=profile,
                    priority=form.cleaned_data["priority"],
                    due_date=form.cleaned_data.get("due_date"),
                )
                messages.success(request, "Задача создана.")

        elif action == "update_status":
            form = ClientStatusForm(request.POST)
            if form.is_valid():
                set_client_status(profile, form.cleaned_data["status"], actor=request.user)
                messages.success(request, "Статус клиента обновлён.")

        elif action == "update_profile":
            form = ClientProfileForm(request.POST, instance=profile)
            if form.is_valid():
                update_client_profile(profile, form.cleaned_data, actor=request.user)
                messages.success(request, "Профиль клиента обновлён.")
            else:
                messages.error(request, "Ошибка при обновлении профиля.")

        return redirect("crm:client_detail", pk=pk)


class ClientStatusUpdateView(ManagerRequiredMixin, View):
    """Quick status change from the client list."""

    def post(self, request, pk):
        profile    = get_object_or_404(ClientProfile, user_id=pk)
        new_status = request.POST.get("status", "")
        if new_status in dict(ClientProfile.ClientStatus.choices):
            set_client_status(profile, new_status, actor=request.user)
            messages.success(request, "Статус обновлён.")
        return redirect("crm:client_list")


# ===========================================================================
# Admin Comments
# ===========================================================================

class AdminCommentDeleteView(ManagerRequiredMixin, View):
    def post(self, request, pk, comment_pk):
        comment = get_object_or_404(AdminComment, pk=comment_pk, client__user_id=pk)
        # Only author or admin can delete
        if comment.author == request.user or request.user.is_admin:
            delete_admin_comment(comment_pk, actor=request.user)
            messages.success(request, "Комментарий удалён.")
        else:
            messages.error(request, "Нет прав для удаления этого комментария.")
        return redirect("crm:client_detail", pk=pk)


class AdminCommentPinView(ManagerRequiredMixin, View):
    def post(self, request, pk, comment_pk):
        get_object_or_404(AdminComment, pk=comment_pk, client__user_id=pk)
        toggle_pin_comment(comment_pk)
        return redirect("crm:client_detail", pk=pk)


# ===========================================================================
# Interactions
# ===========================================================================

class InteractionResolveView(ManagerRequiredMixin, View):
    def post(self, request, pk, interaction_pk):
        resolve_interaction(interaction_pk)
        messages.success(request, "Взаимодействие отмечено как решённое.")
        return redirect("crm:client_detail", pk=pk)


# ===========================================================================
# Tasks
# ===========================================================================

class TaskListView(ManagerRequiredMixin, View):
    template_name = "crm/task_list.html"

    def get(self, request):
        tasks = get_all_tasks(
            status=request.GET.get("status", ""),
            priority=request.GET.get("priority", ""),
        )
        return render(request, self.template_name, {
            "tasks":            tasks,
            "status_choices":   Task.TaskStatus.choices,
            "priority_choices": Task.Priority.choices,
            "status_filter":    request.GET.get("status", ""),
            "priority_filter":  request.GET.get("priority", ""),
        })


class TaskCreateView(ManagerRequiredMixin, View):
    template_name = "crm/task_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": TaskForm()})

    def post(self, request):
        form = TaskForm(request.POST)
        if form.is_valid():
            create_task(
                title=form.cleaned_data["title"],
                description=form.cleaned_data.get("description", ""),
                assigned_to=form.cleaned_data["assigned_to"],
                created_by=request.user,
                priority=form.cleaned_data["priority"],
                due_date=form.cleaned_data.get("due_date"),
            )
            messages.success(request, "Задача создана.")
            return redirect("crm:task_list")
        return render(request, self.template_name, {"form": form})


class TaskCompleteView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        complete_task(pk, actor=request.user)
        messages.success(request, "Задача выполнена.")
        return redirect(request.POST.get("next", "crm:task_list"))


class TaskCancelView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        cancel_task(pk, actor=request.user)
        messages.info(request, "Задача отменена.")
        return redirect(request.POST.get("next", "crm:task_list"))


# ===========================================================================
# Organizations
# ===========================================================================

class OrganizationListView(ManagerRequiredMixin, View):
    template_name = "crm/organization_list.html"

    def get(self, request):
        orgs = get_all_organizations(search=request.GET.get("q", ""))
        return render(request, self.template_name, {
            "organizations": orgs,
            "search_query":  request.GET.get("q", ""),
        })


class OrganizationCreateView(ManagerRequiredMixin, View):
    template_name = "crm/organization_form.html"

    def get(self, request):
        return render(request, self.template_name, {
            "form": OrganizationForm(), "title": "Новая организация",
        })

    def post(self, request):
        form = OrganizationForm(request.POST)
        if form.is_valid():
            org = create_organization(form.cleaned_data, actor=request.user)
            messages.success(request, f"Организация «{org.name}» создана.")
            return redirect("crm:organization_detail", pk=org.pk)
        return render(request, self.template_name, {"form": form, "title": "Новая организация"})


class OrganizationDetailView(ManagerRequiredMixin, View):
    template_name = "crm/organization_detail.html"

    def get(self, request, pk):
        org = get_organization_detail(pk)
        details = [
            ("Тип",             org.get_org_type_display()),
            ("ИНН",             org.inn),
            ("КПП",             org.kpp),
            ("ОГРН",            org.ogrn),
            ("Юр. адрес",       org.legal_address),
            ("Факт. адрес",     org.actual_address),
            ("Телефон",         org.phone),
            ("Email",           org.email),
            ("Сайт",            org.website),
            ("Контактное лицо", org.contact_person),
            ("Менеджер",        org.assigned_manager.get_full_name() if org.assigned_manager else "—"),
        ]
        return render(request, self.template_name, {"org": org, "details": details})


class OrganizationUpdateView(ManagerRequiredMixin, View):
    template_name = "crm/organization_form.html"

    def get(self, request, pk):
        org = get_object_or_404(Organization, pk=pk)
        return render(request, self.template_name, {
            "form": OrganizationForm(instance=org),
            "org":  org,
            "title": f"Редактировать: {org.name}",
        })

    def post(self, request, pk):
        org  = get_object_or_404(Organization, pk=pk)
        form = OrganizationForm(request.POST, instance=org)
        if form.is_valid():
            update_organization(org, form.cleaned_data, actor=request.user)
            messages.success(request, f"Организация «{org.name}» обновлена.")
            return redirect("crm:organization_detail", pk=pk)
        return render(request, self.template_name, {
            "form": form, "org": org, "title": f"Редактировать: {org.name}",
        })
