#!/usr/bin/env python
"""
Простой тест для проверки расчета цен
Запуск: python test_price_calculation.py
"""

import os
import sys
import django
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.bookings.price_calculator import PriceCalculator
from apps.hotel.models import RoomCategory

def test_price_calculation():
    print("=== Тест расчета цен ===")
    
    try:
        # Получаем первую активную категорию
        category = RoomCategory.objects.filter(is_active=True).first()
        if not category:
            print("❌ Нет активных категорий номеров")
            return
            
        print(f"✅ Найдена категория: {category.name}")
        print(f"   Базовая цена: {category.base_price_per_night} ₽")
        
        # Тестовые даты
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=3)
        
        print(f"   Даты: {check_in} - {check_out}")
        
        # Создаем калькулятор
        calculator = PriceCalculator(category)
        
        # Рассчитываем цену
        result = calculator.calculate_total_price(check_in, check_out, 2, 0)
        
        print(f"✅ Расчет успешен:")
        print(f"   Ночей: {result['nights']}")
        print(f"   Цена за ночь: {result['price_per_night']} ₽")
        print(f"   Итого: {result['final_total']} ₽")
        
        if result['discount_amount'] > 0:
            print(f"   Скидка: {result['discount_amount']} ₽ ({result['discount_reason']})")
            
        # Тест метода для всех категорий
        print("\n=== Тест для всех категорий ===")
        prices = PriceCalculator.get_category_prices_for_dates(check_in, check_out, 2, 0)
        
        for cat_id, price_data in prices.items():
            if 'error' in price_data:
                print(f"❌ {price_data['category_name']}: {price_data['error']}")
            else:
                print(f"✅ {price_data['category_name']}: {price_data['total_price']} ₽")
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_price_calculation()