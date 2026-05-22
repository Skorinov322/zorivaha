"""
apps/bookings/price_calculator.py — Advanced pricing logic.

Правила ценообразования:
  Эконом:
    - 1 гость  → базовая цена × 1
    - 2 гостя  → базовая цена × 2

  Полу-люкс:
    - Молодожёны (одна кровать) → базовая цена × 1.5
    - Друзья (две кровати)      → базовая цена × 2

  Грудничок (до 1 года) → бесплатно (не влияет на цену)
  Ранний заезд (до 12:00) → +50% стоимости суток
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict

from apps.hotel.models import RoomCategory, SeasonalPrice
from .models import Booking, BookingStatus


# Множители по типу размещения
OCCUPANCY_MULTIPLIERS = {
    "solo":       Decimal("1.0"),
    "two_guests": Decimal("2.0"),
    "newlyweds":  Decimal("1.5"),
    "friends":    Decimal("2.0"),
}


def calculate_paid_persons(adults: int, children: int) -> int:
    """
    Возвращает количество платных персон.
    Взрослые и дети платят по полной ставке, инфанты — бесплатно.
    """
    return adults + children


class PriceCalculator:

    def __init__(self, room_category: RoomCategory):
        self.room_category = room_category

    def calculate_total_price(
        self,
        check_in: date,
        check_out: date,
        adults: int = 1,
        children: int = 0,
        occupancy_type: str = "solo",
        early_check_in: bool = False,
        organization=None,
    ) -> Dict:
        if check_in >= check_out:
            raise ValueError("Дата выезда должна быть позже даты заезда")

        nights = (check_out - check_in).days
        if nights <= 0:
            raise ValueError("Минимальный срок бронирования — 1 ночь")

        daily_breakdown = []
        total_amount = Decimal("0")
        weekend_surcharge = Decimal("0")
        seasonal_adjustments = []

        current_date = check_in
        while current_date < check_out:
            daily_price = self._get_daily_price(current_date)
            is_weekend = current_date.weekday() >= 5

            if is_weekend and self.room_category.weekend_price_per_night:
                weekend_price = self.room_category.weekend_price_per_night
                weekend_surcharge += weekend_price - daily_price
                daily_price = weekend_price

            seasonal_price = self._get_seasonal_price(current_date)
            if seasonal_price:
                seasonal_adjustments.append({
                    "date": current_date,
                    "original_price": daily_price,
                    "seasonal_price": seasonal_price.price_per_night,
                    "reason": seasonal_price.name,
                })
                daily_price = seasonal_price.price_per_night

            daily_breakdown.append({
                "date": current_date,
                "price": daily_price,
                "is_weekend": is_weekend,
                "is_seasonal": seasonal_price is not None,
            })
            total_amount += daily_price
            current_date += timedelta(days=1)

        # Occupancy type multiplier
        occ_multiplier = OCCUPANCY_MULTIPLIERS.get(occupancy_type, Decimal("1.0"))

        # Дети со спальным местом считаются отдельными оплачиваемыми персонами.
        # Исключение: спец-тариф "молодожёны" для двух гостей на одной кровати.
        paid_persons = calculate_paid_persons(adults, children)
        if paid_persons > 1 and occupancy_type != "newlyweds":
            occ_multiplier = Decimal(str(paid_persons))

        total_amount = total_amount * occ_multiplier
        base_total = total_amount

        # Early check-in: +50% of one room night, not multiplied by guests.
        early_checkin_surcharge = Decimal("0")
        if early_check_in:
            early_checkin_surcharge = self._get_daily_price(check_in) * Decimal("0.5")
            total_amount += early_checkin_surcharge

        # Keep booking totals aligned with the prices configured by the admin.
        # Discounts/surcharges should be explicit, not inferred from occupancy.
        dyn_multiplier = 1.0

        avg_price_per_night = base_total / nights if nights > 0 else Decimal("0")

        return {
            "nights": nights,
            "price_per_night": avg_price_per_night,
            "base_total": base_total,
            "weekend_surcharge": weekend_surcharge,
            "seasonal_adjustments": seasonal_adjustments,
            "occupancy_multiplier": float(occ_multiplier),
            "dynamic_multiplier": dyn_multiplier,
            "early_checkin_surcharge": early_checkin_surcharge,
            "total_before_discount": total_amount,
            "discount_amount": Decimal("0"),
            "discount_reason": "",
            "final_total": total_amount,
            "daily_breakdown": daily_breakdown,
        }

    def _get_daily_price(self, d: date) -> Decimal:
        return self.room_category.get_effective_price(d)

    def _get_seasonal_price(self, d: date):
        return SeasonalPrice.objects.filter(
            category=self.room_category,
            start_date__lte=d,
            end_date__gte=d,
        ).first()

    def _calculate_occupancy_multiplier(self, check_in: date, check_out: date) -> float:
        from apps.hotel.models import Room

        total_rooms = Room.objects.filter(
            category=self.room_category,
            status__in=["available", "occupied"],
        ).count()

        if total_rooms == 0:
            return 1.0

        occupied_rooms = Booking.objects.filter(
            room_category=self.room_category,
            status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN],
            check_in__lt=check_out,
            check_out__gt=check_in,
        ).count()

        rate = occupied_rooms / total_rooms
        if rate >= 0.9:
            return 1.3
        elif rate >= 0.8:
            return 1.2
        elif rate >= 0.7:
            return 1.1
        elif rate <= 0.3:
            return 0.9
        return 1.0

    def calculate_group_booking_price(
        self,
        check_in: date,
        check_out: date,
        paid_persons: int,
        early_check_in: bool = False,
    ) -> dict:
        """
        Новая формула ценообразования для групповых броней:
          total = base_price_per_night × paid_persons × nights
          early_check_in surcharge = base_price × 0.5

        paid_persons = adults + children (инфанты не учитываются).
        """
        if check_in >= check_out:
            raise ValueError("Дата выезда должна быть позже даты заезда")
        if paid_persons < 1:
            raise ValueError("Количество платных персон должно быть не менее 1")

        nights = (check_out - check_in).days
        base_price = self.room_category.get_effective_price(check_in)

        total = base_price * Decimal(paid_persons) * Decimal(nights)

        early_surcharge = Decimal("0")
        if early_check_in:
            early_surcharge = base_price * Decimal("0.5")
            total += early_surcharge

        return {
            "nights": nights,
            "paid_persons": paid_persons,
            "base_price_per_night": base_price,
            "price_per_night": base_price * Decimal(paid_persons),
            "early_checkin_surcharge": early_surcharge,
            "total_price": total,
            "final_total": total,
            "discount_amount": Decimal("0"),
            "discount_reason": "",
        }

    @classmethod
    def get_category_prices_for_dates(
        cls,
        check_in: date,
        check_out: date,
        adults: int = 1,
        children: int = 0,
        occupancy_type: str = "solo",
        early_check_in: bool = False,
    ) -> Dict[int, Dict]:
        try:
            prices = {}
            for category in RoomCategory.objects.filter(is_active=True):
                calc = cls(category)
                try:
                    info = calc.calculate_total_price(
                        check_in, check_out, adults, children,
                        occupancy_type, early_check_in,
                    )
                    prices[category.id] = {
                        "category_name":          category.name,
                        "nights":                 info["nights"],
                        "price_per_night":        float(info["price_per_night"]),
                        "total_price":            float(info["final_total"]),
                        "discount_amount":        float(info["discount_amount"]),
                        "discount_reason":        info["discount_reason"],
                        "occupancy_multiplier":   info["occupancy_multiplier"],
                        "early_checkin_surcharge":float(info["early_checkin_surcharge"]),
                    }
                except ValueError as e:
                    prices[category.id] = {"category_name": category.name, "error": str(e)}
                except Exception:
                    prices[category.id] = {"category_name": category.name, "error": "Ошибка расчёта цены"}
            return prices
        except Exception:
            return {}
