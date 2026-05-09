"""
reviews/urls.py

URL patterns для системы отзывов.
"""

from django.urls import path
from . import views

app_name = "reviews"

urlpatterns = [
    # Публичные страницы
    path("", views.ReviewListView.as_view(), name="list"),
    path("<uuid:pk>/", views.ReviewDetailView.as_view(), name="detail"),
    
    # Создание отзыва гостем
    path("create/<uuid:booking_id>/", views.create_review, name="create"),
    
    # Личный кабинет гостя
    path("my/", views.MyReviewsListView.as_view(), name="my_reviews"),
    
    # Модерация (для персонала)
    path("moderation/", views.ReviewModerationListView.as_view(), name="moderation_list"),
    path("moderation/<uuid:pk>/", views.moderate_review, name="moderate"),
    path("respond/<uuid:pk>/", views.respond_to_review, name="respond"),
]
