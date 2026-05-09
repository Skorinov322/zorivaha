"""
crm/urls.py — mounted at /crm/ in config/urls.py
"""

from django.urls import path
from . import views

app_name = "crm"

urlpatterns = [
    # Dashboard
    path("",                                    views.CrmDashboardView.as_view(),       name="dashboard"),

    # Clients
    path("clients/",                            views.ClientListView.as_view(),         name="client_list"),
    path("clients/<int:pk>/",                   views.ClientDetailView.as_view(),       name="client_detail"),
    path("clients/<int:pk>/status/",            views.ClientStatusUpdateView.as_view(), name="client_status"),

    # Comments
    path("clients/<int:pk>/comments/<int:comment_pk>/delete/",
         views.AdminCommentDeleteView.as_view(), name="comment_delete"),
    path("clients/<int:pk>/comments/<int:comment_pk>/pin/",
         views.AdminCommentPinView.as_view(),    name="comment_pin"),

    # Interactions
    path("clients/<int:pk>/interactions/<int:interaction_pk>/resolve/",
         views.InteractionResolveView.as_view(), name="interaction_resolve"),

    # Tasks
    path("tasks/",                              views.TaskListView.as_view(),    name="task_list"),
    path("tasks/create/",                       views.TaskCreateView.as_view(),  name="task_create"),
    path("tasks/<int:pk>/complete/",            views.TaskCompleteView.as_view(),name="task_complete"),
    path("tasks/<int:pk>/cancel/",              views.TaskCancelView.as_view(),  name="task_cancel"),

    # Organizations
    path("organizations/",                      views.OrganizationListView.as_view(),   name="organization_list"),
    path("organizations/create/",               views.OrganizationCreateView.as_view(), name="organization_create"),
    path("organizations/<int:pk>/",             views.OrganizationDetailView.as_view(), name="organization_detail"),
    path("organizations/<int:pk>/edit/",        views.OrganizationUpdateView.as_view(), name="organization_edit"),
]
