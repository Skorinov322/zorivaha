"""
hotel/urls.py

Public:
  /                          → IndexView
  /rooms/                    → RoomListView
  /rooms/<slug>/             → RoomCategoryDetailView
  /about/                    → AboutView
  /contacts/                 → ContactsView

Staff (prefix /rooms/manage/):
  categories/                → CategoryListView
  categories/create/         → CategoryCreateView
  categories/<pk>/edit/      → CategoryUpdateView
  categories/<pk>/delete/    → CategoryDeleteView
  categories/<pk>/images/    → CategoryImageUploadView
  categories/<pk>/images/<image_pk>/delete/ → CategoryImageDeleteView

  rooms/                     → RoomListStaffView
  rooms/create/              → RoomCreateView
  rooms/<pk>/edit/           → RoomUpdateView
  rooms/<pk>/delete/         → RoomDeleteView
  rooms/<pk>/status/         → RoomStatusUpdateView
"""

from django.urls import path
from . import views

app_name = "hotel"

urlpatterns = [
    # ---- Public ----
    path("",                          views.IndexView.as_view(),              name="index"),
    path("rooms/",                    views.RoomListView.as_view(),           name="room_list"),
    path("rooms/<slug:slug>/",        views.RoomCategoryDetailView.as_view(), name="room_category_detail"),
    path("about/",                    views.AboutView.as_view(),              name="about"),
    path("contacts/",                 views.ContactsView.as_view(),           name="contacts"),

    # ---- Staff: categories ----
    path("manage/categories/",
         views.CategoryListView.as_view(),        name="staff_category_list"),
    path("manage/categories/create/",
         views.CategoryCreateView.as_view(),      name="staff_category_create"),
    path("manage/categories/<int:pk>/edit/",
         views.CategoryUpdateView.as_view(),      name="staff_category_edit"),
    path("manage/categories/<int:pk>/delete/",
         views.CategoryDeleteView.as_view(),      name="staff_category_delete"),
    path("manage/categories/<int:pk>/images/",
         views.CategoryImageUploadView.as_view(), name="staff_category_images"),
    path("manage/categories/<int:pk>/images/<int:image_pk>/delete/",
         views.CategoryImageDeleteView.as_view(), name="staff_image_delete"),

    # ---- Staff: rooms ----
    path("manage/rooms/",
         views.RoomListStaffView.as_view(),       name="staff_room_list"),
    path("manage/rooms/create/",
         views.RoomCreateView.as_view(),          name="staff_room_create"),
    path("manage/rooms/<int:pk>/edit/",
         views.RoomUpdateView.as_view(),          name="staff_room_edit"),
    path("manage/rooms/<int:pk>/delete/",
         views.RoomDeleteView.as_view(),          name="staff_room_delete"),
    path("manage/rooms/<int:pk>/status/",
         views.RoomStatusUpdateView.as_view(),    name="staff_room_status"),
]
