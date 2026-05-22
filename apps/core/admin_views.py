"""
Дополниостиницаные view для админ-панели
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.bookings.models import Booking
from apps.accounts.models import User
from apps.hotel.models import Room
from apps.crm.models import Organization


@staff_member_required
def admin_dashboard_stats(request):
    """
    Возвращает статистику для главной страницы админки
    """
    # Статистика бронирований
    total_bookings = Booking.objects.count()
    active_bookings = Booking.objects.filter(
        status__in=['confirmed', 'checked_in']
    ).count()
    
    # Статистика пользователей
    total_users = User.objects.count()
    
    # Статистика номеров
    total_rooms = Room.objects.count()
    occupied_rooms = Room.objects.filter(status='occupied').count()
    occupancy_rate = round((occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0, 1)
    
    # Организации на подтверждении
    pending_orgs = Organization.objects.filter(is_approved=False).count()
    
    # Статистика за последние 30 дней
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_bookings = Booking.objects.filter(created_at__gte=thirty_days_ago).count()
    
    context = {
        'total_bookings': total_bookings,
        'active_bookings': active_bookings,
        'total_users': total_users,
        'total_rooms': total_rooms,
        'occupancy_rate': occupancy_rate,
        'pending_orgs': pending_orgs,
        'recent_bookings': recent_bookings,
    }
    
    return context