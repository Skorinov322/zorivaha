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
        return JsonResponse({"rooms": [], "max_guests": 0})

    try:
        from apps.hotel.models import RoomCategory
        category = RoomCategory.objects.get(pk=category_id)
        check_in = None
        check_out = None
        check_in_str = request.GET.get("check_in")
        check_out_str = request.GET.get("check_out")
        if check_in_str and check_out_str:
            check_in = datetime.strptime(check_in_str, "%Y-%m-%d").date()
            check_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()

        from apps.hotel.selectors import get_bookable_rooms
        rooms = get_bookable_rooms(int(category_id))

        room_list = []
        for room in rooms:
            available_capacity = room.max_guests_per_room
            if check_in and check_out:
                available_capacity = room.available_capacity(check_in, check_out)
            if available_capacity <= 0:
                continue

            occupancy_info = ""
            if room.max_guests_per_room > 1:
                current = room.max_guests_per_room - available_capacity
                occupancy_info = f" ({current}/{room.max_guests_per_room})"

            room_list.append({
                "id": room.id,
                "number": room.number,
                "subdivision": room.subdivision or "",
                "full_number": room.full_number,
                "floor": room.floor,
                "display_name": f"{room.full_number}{(' / ' + room.subdivision) if room.subdivision else ''}{occupancy_info}",
                "max_guests": available_capacity,
            })

        max_guests = sum(room["max_guests"] for room in room_list)
        return JsonResponse({
            "rooms": room_list,
            "max_guests": max_guests,
            "category_max_guests": category.max_guests,
            "availability_message": (
                "В данной категории свободных номеров нет."
                if check_in and check_out and max_guests <= 0
                else ""
            ),
        })

    except Exception:
        return JsonResponse({"error": "Ошибка загрузки номеров"}, status=500)


@login_required
@require_http_methods(["GET"])
def calculate_prices(request):
    """Calculate prices for all categories for given dates."""
    try:
        check_in_str = request.GET.get("check_in")
        check_out_str = request.GET.get("check_out")
        adults        = int(request.GET.get("adults", 1))
        children      = int(request.GET.get("children", 0))
        occupancy_type  = request.GET.get("occupancy_type", "solo")
        early_check_in  = request.GET.get("early_check_in", "false").lower() == "true"

        if not check_in_str or not check_out_str:
            return JsonResponse({"error": "Укажите даты заезда и выезда"}, status=400)

        check_in  = datetime.strptime(check_in_str,  "%Y-%m-%d").date()
        check_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()

        if check_in >= check_out:
            return JsonResponse({"error": "Дата выезда должна быть позже даты заезда"}, status=400)

        prices = PriceCalculator.get_category_prices_for_dates(
            check_in, check_out, adults, children, occupancy_type, early_check_in
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
