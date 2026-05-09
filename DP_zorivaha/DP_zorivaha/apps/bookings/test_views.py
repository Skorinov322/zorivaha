"""
Простые представления для тестирования функциональности
"""

from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required


def test_ajax_page(request):
    """Страница для тестирования AJAX-запросов"""
    with open('test_ajax.html', 'r', encoding='utf-8') as f:
        content = f.read()
    return HttpResponse(content)


@login_required
def debug_price_calculation(request):
    """Отладочная страница для проверки расчета цен"""
    from datetime import date, timedelta
    from .price_calculator import PriceCalculator
    from apps.hotel.models import RoomCategory
    
    debug_info = []
    
    try:
        # Получаем категории
        categories = RoomCategory.objects.filter(is_active=True)
        debug_info.append(f"Найдено активных категорий: {categories.count()}")
        
        if categories.exists():
            category = categories.first()
            debug_info.append(f"Тестируем категорию: {category.name}")
            debug_info.append(f"Базовая цена: {category.base_price_per_night} ₽")
            
            # Тестовые даты
            check_in = date.today() + timedelta(days=1)
            check_out = check_in + timedelta(days=2)
            
            debug_info.append(f"Даты: {check_in} - {check_out}")
            
            # Создаем калькулятор
            calculator = PriceCalculator(category)
            result = calculator.calculate_total_price(check_in, check_out, 2, 0)
            
            debug_info.append("✅ Расчет успешен!")
            debug_info.append(f"Ночей: {result['nights']}")
            debug_info.append(f"Цена за ночь: {result['price_per_night']} ₽")
            debug_info.append(f"Итого: {result['final_total']} ₽")
            
            # Тест метода для всех категорий
            debug_info.append("\n--- Тест для всех категорий ---")
            prices = PriceCalculator.get_category_prices_for_dates(check_in, check_out, 2, 0)
            
            for cat_id, price_data in prices.items():
                if 'error' in price_data:
                    debug_info.append(f"❌ {price_data['category_name']}: {price_data['error']}")
                else:
                    debug_info.append(f"✅ {price_data['category_name']}: {price_data['total_price']} ₽")
        else:
            debug_info.append("❌ Нет активных категорий номеров")
            
    except Exception as e:
        debug_info.append(f"❌ Ошибка: {e}")
        import traceback
        debug_info.append(traceback.format_exc())
    
    return HttpResponse(
        f"<h1>Отладка расчета цен</h1><pre>{'<br>'.join(debug_info)}</pre>",
        content_type="text/html; charset=utf-8"
    )