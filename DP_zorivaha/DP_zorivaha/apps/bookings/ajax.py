"""AJAX endpoints for the booking form."""

from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.hotel.models import Room
from .price_calculator import PriceCalculator


@login_required
def rooms_for_category(request):
    """Return available rooms for a given category (used by booking form JS)."""
    category_id = request.GET.get("category")
    if not category_id:
        return JsonResponse({"rooms": []})

    try:
        rooms = Room.objects.filter(
            category_id=category_id,
            status=Room.RoomStatus.AVAILABLE,
        ).order_by("floor", "number", "subdivision")

        room_list = []
        for room in rooms:
            occupancy_info = ""
            if room.max_concurrent_bookings > 1:
                current = room.get_current_occupancy_count()
                occupancy_info = f" ({current}/{room.max_concurrent_bookings})"
            
            room_list.append({
                "id": room.id,
                "number": room.number,
                "subdivision": room.subdivision or "",
                "full_number": room.full_number,
                "floor": room.floor,
                "display_name": f"{room.full_number}{occupancy_info}"
            })

        return JsonResponse({"rooms": room_list})
    
    except Exception as e:
        return JsonResponse({"error": "Ошибка загрузки номеров"}, status=500)


@login_required
@require_http_methods(["GET"])
def calculate_prices(request):
    """Calculate prices for all categories for given dates."""
    try:
        check_in_str = request.GET.get("check_in")
        check_out_str = request.GET.get("check_out")
        adults = int(request.GET.get("adults", 1))
        children = int(request.GET.get("children", 0))
        
        if not check_in_str or not check_out_str:
            return JsonResponse({"error": "Укажите даты заезда и выезда"}, status=400)
            
        check_in = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        check_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()
        
        if check_in >= check_out:
            return JsonResponse({"error": "Дата выезда должна быть позже даты заезда"}, status=400)
        
        prices = PriceCalculator.get_category_prices_for_dates(
            check_in, check_out, adults, children
        )
        
        return JsonResponse({"prices": prices})
        
    except ValueError as e:
        return JsonResponse({"error": f"Ошибка в данных: {str(e)}"}, status=400)
    except Exception as e:
        # Log the actual error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Price calculation error: {str(e)}", exc_info=True)
        return JsonResponse({"error": "Ошибка расчета цен. Попробуйте позже."}, status=500)
