"""
reviews/selectors.py

Селекторы для получения данных отзывов.
"""

from django.db.models import Avg, Count, Q
from .models import Review, ReviewStatus


def get_published_reviews():
    """Получить все опубликованные отзывы"""
    return Review.objects.filter(
        status=ReviewStatus.APPROVED
    ).select_related(
        "booking__room_category",
        "author"
    ).prefetch_related("response")


def get_featured_reviews(limit=5):
    """Получить избранные отзывы для главной страницы"""
    return Review.objects.filter(
        status=ReviewStatus.APPROVED,
        is_featured=True
    ).select_related(
        "booking__room_category",
        "author"
    ).prefetch_related("response").order_by("-created_at")[:limit]


def get_pending_reviews():
    """Получить отзывы на модерации"""
    return Review.objects.filter(
        status=ReviewStatus.PENDING
    ).select_related(
        "booking__room_category",
        "author"
    ).order_by("-created_at")


def get_review_statistics():
    """Получить статистику по отзывам"""
    approved_reviews = Review.objects.filter(status=ReviewStatus.APPROVED)
    
    stats = approved_reviews.aggregate(
        total_count=Count("id"),
        average_overall=Avg("overall_rating"),
        average_cleanliness=Avg("cleanliness_rating"),
        average_comfort=Avg("comfort_rating"),
        average_staff=Avg("staff_rating"),
        average_value=Avg("value_rating"),
        average_location=Avg("location_rating"),
    )
    
    # Распределение по оценкам
    rating_distribution = {}
    for rating in range(1, 6):
        rating_distribution[rating] = approved_reviews.filter(
            overall_rating=rating
        ).count()
    
    stats["rating_distribution"] = rating_distribution
    
    return stats


def get_user_reviews(user):
    """Получить все отзывы пользователя"""
    return Review.objects.filter(
        author=user
    ).select_related(
        "booking__room_category",
        "moderated_by"
    ).prefetch_related("response").order_by("-created_at")


def can_user_review_booking(user, booking):
    """Проверить, может ли пользователь оставить отзыв на бронирование"""
    from apps.bookings.models import BookingStatus
    
    # Бронирование должно быть завершено
    if booking.status != BookingStatus.CHECKED_OUT:
        return False, "Отзыв можно оставить только на завершенное бронирование"
    
    # Пользователь должен быть гостем этого бронирования
    if booking.guest != user:
        return False, "Вы не можете оставить отзыв на чужое бронирование"
    
    # Отзыв еще не оставлен
    if hasattr(booking, "review"):
        return False, "Вы уже оставили отзыв на это бронирование"
    
    return True, ""


def get_moderation_counts():
    """Получить счетчики для модерации"""
    return {
        "pending": Review.objects.filter(status=ReviewStatus.PENDING).count(),
        "approved": Review.objects.filter(status=ReviewStatus.APPROVED).count(),
        "rejected": Review.objects.filter(status=ReviewStatus.REJECTED).count(),
    }
