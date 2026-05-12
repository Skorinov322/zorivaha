"""
reviews/views.py

Views для работы с отзывами.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Avg
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from apps.bookings.models import Booking, BookingStatus
from apps.core.mixins import LoginRequiredMixin, StaffRequiredMixin
from .models import Review, ReviewResponse, ReviewStatus
from .forms import ReviewForm, ReviewModerationForm, ReviewResponseForm


# ---------------------------------------------------------------------------
# Public views
# ---------------------------------------------------------------------------

class ReviewListView(ListView):
    """Список опубликованных отзывов (публичная страница)"""
    model = Review
    template_name = "reviews/review_list.html"
    context_object_name = "reviews"
    paginate_by = 10

    def get_queryset(self):
        # Только одобренные отзывы
        qs = Review.objects.filter(
            status=ReviewStatus.APPROVED
        ).select_related(
            "booking__room_category",
            "author"
        ).prefetch_related("response")
        
        # Сортировка
        sort = self.request.GET.get("sort", "-created_at")
        if sort in ["-created_at", "-overall_rating", "overall_rating"]:
            qs = qs.order_by(sort)
        
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Статистика
        approved_reviews = Review.objects.filter(status=ReviewStatus.APPROVED)
        context["total_reviews"] = approved_reviews.count()
        context["average_rating"] = approved_reviews.aggregate(
            avg=Avg("overall_rating")
        )["avg"] or 0
        
        # Избранные отзывы
        context["featured_reviews"] = Review.objects.filter(
            status=ReviewStatus.APPROVED,
            is_featured=True
        )[:3]
        
        return context


class ReviewDetailView(DetailView):
    """Детальная страница отзыва"""
    model = Review
    template_name = "reviews/review_detail.html"
    context_object_name = "review"

    def get_queryset(self):
        # Публично доступны только одобренные отзывы
        return Review.objects.filter(
            status=ReviewStatus.APPROVED
        ).select_related(
            "booking__room_category",
            "author",
            "moderated_by"
        ).prefetch_related("response")


# ---------------------------------------------------------------------------
# Guest views (создание отзыва)
# ---------------------------------------------------------------------------

@login_required
def create_review(request, booking_id):
    """Создание отзыва на завершенное бронирование"""
    
    # Проверяем бронирование
    booking = get_object_or_404(
        Booking,
        id=booking_id,
        guest=request.user
    )
    
    # Проверяем, что бронирование завершено
    if booking.status != BookingStatus.CHECKED_OUT:
        messages.error(request, "Отзыв можно оставить только на завершенное бронирование.")
        return redirect("bookings:detail", pk=booking.id)
    
    # Проверяем, что отзыв еще не оставлен
    if hasattr(booking, "review"):
        messages.info(request, "Вы уже оставили отзыв на это бронирование.")
        return redirect("reviews:detail", pk=booking.review.id)
    
    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.booking = booking
            review.author = request.user
            review.guest_name = request.user.get_full_name() or request.user.email
            
            # Сохраняем IP и User-Agent
            review.ip_address = get_client_ip(request)
            review.user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
            
            review.save()
            
            messages.success(
                request,
                "Спасибо за ваш отзыв! Он будет опубликован после модерации."
            )
            return redirect("bookings:detail", pk=booking.id)
    else:
        form = ReviewForm()
    
    context = {
        "form": form,
        "booking": booking,
    }
    return render(request, "reviews/review_create.html", context)


# ---------------------------------------------------------------------------
# Staff views (модерация)
# ---------------------------------------------------------------------------

class ReviewModerationListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    """Список отзывов для модерации (для персонала)"""
    model = Review
    template_name = "reviews/moderation_list.html"
    context_object_name = "reviews"
    paginate_by = 20

    def get_queryset(self):
        qs = Review.objects.select_related(
            "booking__room_category",
            "author",
            "moderated_by"
        ).prefetch_related("response")
        
        # Фильтр по статусу
        status = self.request.GET.get("status", "pending")
        if status in ["pending", "approved", "rejected"]:
            qs = qs.filter(status=status)
        
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Счетчики
        context["pending_count"] = Review.objects.filter(
            status=ReviewStatus.PENDING
        ).count()
        context["approved_count"] = Review.objects.filter(
            status=ReviewStatus.APPROVED
        ).count()
        context["rejected_count"] = Review.objects.filter(
            status=ReviewStatus.REJECTED
        ).count()
        
        context["current_status"] = self.request.GET.get("status", "pending")
        
        return context


@login_required
def moderate_review(request, pk):
    """Модерация отзыва (одобрение/отклонение)"""
    
    # Проверяем права (ресепшн или выше)
    if not request.user.has_role("receptionist"):
        raise PermissionDenied
    
    review = get_object_or_404(Review, pk=pk)
    
    # Проверяем, что отзыв на модерации
    if not review.can_be_moderated:
        messages.error(request, "Этот отзыв уже прошел модерацию.")
        return redirect("reviews:moderation_list")
    
    if request.method == "POST":
        form = ReviewModerationForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data["action"]
            comment = form.cleaned_data["comment"]
            
            if action == "approve":
                review.approve(moderator=request.user, comment=comment)
                messages.success(request, "Отзыв одобрен и опубликован.")
            elif action == "reject":
                review.reject(moderator=request.user, reason=comment)
                messages.success(request, "Отзыв отклонен.")
            
            return redirect("reviews:moderation_list")
    else:
        form = ReviewModerationForm()
    
    context = {
        "form": form,
        "review": review,
    }
    return render(request, "reviews/moderate_review.html", context)


@login_required
def respond_to_review(request, pk):
    """Ответ администрации на отзыв"""
    
    # Проверяем права (менеджер или выше)
    if not request.user.has_role("manager"):
        raise PermissionDenied
    
    review = get_object_or_404(Review, pk=pk)
    
    # Проверяем, что отзыв одобрен
    if not review.is_approved:
        messages.error(request, "Отвечать можно только на одобренные отзывы.")
        return redirect("reviews:moderation_list")
    
    # Проверяем, что ответа еще нет
    if review.has_response:
        messages.info(request, "На этот отзыв уже есть ответ.")
        return redirect("reviews:detail", pk=review.id)
    
    if request.method == "POST":
        form = ReviewResponseForm(request.POST)
        if form.is_valid():
            response = form.save(commit=False)
            response.review = review
            response.author = request.user
            response.author_name = request.user.get_full_name() or request.user.email
            response.save()
            
            messages.success(request, "Ответ на отзыв опубликован.")
            return redirect("reviews:detail", pk=review.id)
    else:
        # Предзаполняем должность
        initial = {}
        if request.user.is_admin:
            initial["author_position"] = "Администратор"
        elif request.user.is_manager:
            initial["author_position"] = "Менеджер"
        
        form = ReviewResponseForm(initial=initial)
    
    context = {
        "form": form,
        "review": review,
    }
    return render(request, "reviews/respond_to_review.html", context)


# ---------------------------------------------------------------------------
# My reviews (личный кабинет гостя)
# ---------------------------------------------------------------------------

class MyReviewsListView(LoginRequiredMixin, ListView):
    """Мои отзывы (личный кабинет гостя)"""
    model = Review
    template_name = "reviews/my_reviews.html"
    context_object_name = "reviews"
    paginate_by = 10

    def get_queryset(self):
        return Review.objects.filter(
            author=self.user
        ).select_related(
            "booking__room_category",
            "moderated_by"
        ).prefetch_related("response").order_by("-created_at")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_client_ip(request):
    """Получить IP адрес клиента"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip
