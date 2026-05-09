"""
apps/bookings/price_calculator.py — Advanced pricing logic.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from django.db.models import Q
from django.utils import timezone

from apps.hotel.models import RoomCategory, SeasonalPrice
from .models import Booking, BookingStatus


class PriceCalculator:
    """
    Advanced price calculation service with dynamic pricing support.
    """
    
    def __init__(self, room_category: RoomCategory):
        self.room_category = room_category
        
    def calculate_total_price(
        self, 
        check_in: date, 
        check_out: date,
        adults: int = 1,
        children: int = 0,
        organization=None
    ) -> Dict:
        """
        Calculate total price for a booking period with detailed breakdown.
        
        Returns:
            {
                'nights': int,
                'price_per_night': Decimal,
                'base_total': Decimal,
                'weekend_surcharge': Decimal,
                'seasonal_adjustments': List[Dict],
                'occupancy_multiplier': float,
                'total_before_discount': Decimal,
                'discount_amount': Decimal,
                'discount_reason': str,
                'final_total': Decimal,
                'daily_breakdown': List[Dict]
            }
        """
        if check_in >= check_out:
            raise ValueError("Дата выезда должна быть позже даты заезда")
            
        nights = (check_out - check_in).days
        if nights <= 0:
            raise ValueError("Минимальный срок бронирования - 1 ночь")
            
        # Calculate daily prices
        daily_breakdown = []
        total_amount = Decimal('0')
        weekend_surcharge = Decimal('0')
        seasonal_adjustments = []
        
        current_date = check_in
        while current_date < check_out:
            daily_price = self._get_daily_price(current_date)
            is_weekend = current_date.weekday() >= 5  # Saturday=5, Sunday=6
            
            # Apply weekend surcharge if applicable
            if is_weekend and self.room_category.weekend_price_per_night:
                weekend_price = self.room_category.weekend_price_per_night
                weekend_surcharge += weekend_price - daily_price
                daily_price = weekend_price
                
            # Check for seasonal pricing
            seasonal_price = self._get_seasonal_price(current_date)
            if seasonal_price:
                seasonal_adjustments.append({
                    'date': current_date,
                    'original_price': daily_price,
                    'seasonal_price': seasonal_price.price_per_night,
                    'reason': seasonal_price.name
                })
                daily_price = seasonal_price.price_per_night
                
            daily_breakdown.append({
                'date': current_date,
                'price': daily_price,
                'is_weekend': is_weekend,
                'is_seasonal': seasonal_price is not None
            })
            
            total_amount += daily_price
            current_date += timedelta(days=1)
            
        # Apply occupancy-based dynamic pricing
        occupancy_multiplier = self._calculate_occupancy_multiplier(check_in, check_out)
        if occupancy_multiplier != 1.0:
            total_amount = total_amount * Decimal(str(occupancy_multiplier))
            
        # Calculate average price per night
        avg_price_per_night = total_amount / nights if nights > 0 else Decimal('0')
        
        # Apply discounts
        discount_amount = Decimal('0')
        discount_reason = ""
        
        # Corporate discount
        if organization and organization.corporate_discount_pct:
            corp_discount = total_amount * organization.corporate_discount_pct / 100
            discount_amount = corp_discount
            discount_reason = f"Корпоративная скидка {organization.corporate_discount_pct}%"
            
        # Long stay discount (7+ nights)
        elif nights >= 7:
            long_stay_discount = total_amount * Decimal('0.10')  # 10% discount
            discount_amount = long_stay_discount
            discount_reason = f"Скидка за длительное проживание ({nights} ночей)"
            
        # Early booking discount (30+ days in advance)
        elif (check_in - timezone.localdate()).days >= 30:
            early_discount = total_amount * Decimal('0.05')  # 5% discount
            discount_amount = early_discount
            discount_reason = "Скидка за раннее бронирование"
            
        final_total = total_amount - discount_amount
        
        return {
            'nights': nights,
            'price_per_night': avg_price_per_night,
            'base_total': total_amount,
            'weekend_surcharge': weekend_surcharge,
            'seasonal_adjustments': seasonal_adjustments,
            'occupancy_multiplier': occupancy_multiplier,
            'total_before_discount': total_amount,
            'discount_amount': discount_amount,
            'discount_reason': discount_reason,
            'final_total': final_total,
            'daily_breakdown': daily_breakdown
        }
        
    def _get_daily_price(self, date: date) -> Decimal:
        """Get base price for a specific date."""
        return self.room_category.get_effective_price(date)
        
    def _get_seasonal_price(self, date: date):
        """Get seasonal price override for a specific date."""
        return SeasonalPrice.objects.filter(
            category=self.room_category,
            start_date__lte=date,
            end_date__gte=date
        ).first()
        
    def _calculate_occupancy_multiplier(self, check_in: date, check_out: date) -> float:
        """
        Calculate dynamic pricing multiplier based on occupancy.
        Higher occupancy = higher prices.
        """
        # Import here to avoid circular imports
        from apps.hotel.models import Room
        
        # Get total rooms for this category
        total_rooms = Room.objects.filter(
            category=self.room_category,
            status__in=['available', 'occupied']
        ).count()
        
        if total_rooms == 0:
            return 1.0
            
        # Calculate average occupancy for the period
        occupied_rooms = Booking.objects.filter(
            room_category=self.room_category,
            status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN],
            check_in__lt=check_out,
            check_out__gt=check_in
        ).count()
        
        occupancy_rate = occupied_rooms / total_rooms
        
        # Apply multiplier based on occupancy
        if occupancy_rate >= 0.9:  # 90%+ occupancy
            return 1.3  # 30% surcharge
        elif occupancy_rate >= 0.8:  # 80%+ occupancy
            return 1.2  # 20% surcharge
        elif occupancy_rate >= 0.7:  # 70%+ occupancy
            return 1.1  # 10% surcharge
        elif occupancy_rate <= 0.3:  # Low occupancy
            return 0.9  # 10% discount
        else:
            return 1.0  # No change
            
    @classmethod
    def get_category_prices_for_dates(
        cls, 
        check_in: date, 
        check_out: date,
        adults: int = 1,
        children: int = 0
    ) -> Dict[int, Dict]:
        """
        Get prices for all active room categories for given dates.
        Used for AJAX price updates in booking form.
        """
        try:
            categories = RoomCategory.objects.filter(is_active=True)
            prices = {}
            
            for category in categories:
                calculator = cls(category)
                try:
                    price_info = calculator.calculate_total_price(
                        check_in, check_out, adults, children
                    )
                    prices[category.id] = {
                        'category_name': category.name,
                        'nights': price_info['nights'],
                        'price_per_night': float(price_info['price_per_night']),
                        'total_price': float(price_info['final_total']),
                        'discount_amount': float(price_info['discount_amount']),
                        'discount_reason': price_info['discount_reason'],
                        'occupancy_multiplier': price_info['occupancy_multiplier']
                    }
                except ValueError as e:
                    # Invalid date range or other validation error
                    prices[category.id] = {
                        'category_name': category.name,
                        'error': str(e)
                    }
                except Exception as e:
                    # Other errors
                    prices[category.id] = {
                        'category_name': category.name,
                        'error': 'Ошибка расчета цены'
                    }
                    
            return prices
        except Exception as e:
            # If we can't even get categories, return empty dict
            return {}