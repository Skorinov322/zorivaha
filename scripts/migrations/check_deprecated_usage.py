#!/usr/bin/env python
"""
Проверка использования deprecated моделей в коде и БД

Использование:
    python scripts/migrations/check_deprecated_usage.py
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from apps.hotel.models import RoomReview
from apps.analytics.models import PageView, BookingFunnel, RevenueSnapshot
from apps.crm.models import Interaction, Task, Message


def check_database_usage():
    """Проверяет количество записей в deprecated таблицах"""
    
    print("=" * 80)
    print("ПРОВЕРКА ИСПОЛЬЗОВАНИЯ DEPRECATED МОДЕЛЕЙ В БД")
    print("=" * 80)
    
    deprecated_models = [
        ('hotel.RoomReview', RoomReview, 'reviews.Review'),
        ('analytics.PageView', PageView, 'Google Analytics'),
        ('analytics.BookingFunnel', BookingFunnel, 'Google Analytics Goals'),
        ('analytics.RevenueSnapshot', RevenueSnapshot, 'DailyMetrics.aggregate()'),
        ('crm.Interaction', Interaction, 'BookingHistory + AdminComment'),
        ('crm.Task', Task, 'Trello/Asana/Notion'),
        ('crm.Message', Message, 'notifications.ContactMessage'),
    ]
    
    total_records = 0
    has_data = []
    
    for model_name, model_class, alternative in deprecated_models:
        try:
            count = model_class.objects.count()
            total_records += count
            
            status = "✅" if count == 0 else "⚠️ "
            print(f"\n{status} {model_name}")
            print(f"   Записей в БД: {count}")
            print(f"   Альтернатива: {alternative}")
            
            if count > 0:
                has_data.append((model_name, count, alternative))
                
                # Показываем последние записи
                recent = model_class.objects.order_by('-created_at')[:3] if hasattr(model_class, 'created_at') else model_class.objects.all()[:3]
                if recent:
                    print(f"   Последние записи:")
                    for obj in recent:
                        print(f"      - {obj}")
        
        except Exception as e:
            print(f"❌ {model_name}: Ошибка проверки - {e}")
    
    print("\n" + "=" * 80)
    print("ИТОГИ")
    print("=" * 80)
    print(f"📊 Всего записей в deprecated таблицах: {total_records}")
    
    if has_data:
        print(f"\n⚠️  Найдены данные в {len(has_data)} deprecated таблицах:")
        for model_name, count, alternative in has_data:
            print(f"   • {model_name}: {count} записей → {alternative}")
        
        print("\n📝 Рекомендации:")
        print("1. Запустите скрипты миграции для переноса данных")
        print("2. Перестаньте использовать deprecated модели в новом коде")
        print("3. Через 6-12 месяцев удалите deprecated модели")
    else:
        print("\n✅ Отлично! Нет данных в deprecated таблицах")
        print("   Можно безопасно удалить deprecated модели")
    
    return has_data


def check_code_usage():
    """Проверяет использование deprecated моделей в коде"""
    
    print("\n" + "=" * 80)
    print("ПРОВЕРКА ИСПОЛЬЗОВАНИЯ DEPRECATED МОДЕЛЕЙ В КОДЕ")
    print("=" * 80)
    
    # Паттерны для поиска
    patterns = {
        'RoomReview': ['from apps.hotel.models import RoomReview', 'hotel.RoomReview', 'RoomReview.objects'],
        'PageView': ['from apps.analytics.models import PageView', 'analytics.PageView', 'PageView.objects'],
        'BookingFunnel': ['from apps.analytics.models import BookingFunnel', 'analytics.BookingFunnel', 'BookingFunnel.objects'],
        'RevenueSnapshot': ['from apps.analytics.models import RevenueSnapshot', 'analytics.RevenueSnapshot', 'RevenueSnapshot.objects'],
        'Interaction': ['from apps.crm.models import Interaction', 'crm.Interaction', 'Interaction.objects'],
        'Task': ['from apps.crm.models import Task', 'crm.Task', 'Task.objects'],
        'crm.Message': ['from apps.crm.models import Message', 'crm.Message', 'Message.objects'],
    }
    
    # Директории для поиска
    search_dirs = ['apps/', 'scripts/']
    
    found_usage = {}
    
    for model_name, search_patterns in patterns.items():
        found_usage[model_name] = []
        
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue
            
            for py_file in Path(search_dir).rglob('*.py'):
                # Пропускаем файлы миграций и сами deprecated модели
                if 'migrations' in str(py_file) or 'models.py' in str(py_file):
                    continue
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        for pattern in search_patterns:
                            if pattern in content:
                                # Находим строки с использованием
                                lines = content.split('\n')
                                for i, line in enumerate(lines, 1):
                                    if pattern in line:
                                        found_usage[model_name].append({
                                            'file': str(py_file),
                                            'line': i,
                                            'code': line.strip()
                                        })
                except Exception as e:
                    pass
    
    # Выводим результаты
    total_usages = sum(len(usages) for usages in found_usage.values())
    
    if total_usages == 0:
        print("\n✅ Отлично! Deprecated модели не используются в коде")
    else:
        print(f"\n⚠️  Найдено использований deprecated моделей: {total_usages}")
        
        for model_name, usages in found_usage.items():
            if usages:
                print(f"\n📄 {model_name} ({len(usages)} использований):")
                for usage in usages[:5]:  # Показываем первые 5
                    print(f"   {usage['file']}:{usage['line']}")
                    print(f"      {usage['code']}")
                
                if len(usages) > 5:
                    print(f"   ... и ещё {len(usages) - 5} использований")
        
        print("\n📝 Рекомендации:")
        print("1. Обновите код, заменив deprecated модели на альтернативы")
        print("2. Используйте IDE для поиска всех использований (Ctrl+Shift+F)")
        print("3. Запустите тесты после изменений")
    
    return found_usage


def main():
    """Главная функция"""
    
    print("\n🔍 ПРОВЕРКА DEPRECATED МОДЕЛЕЙ\n")
    
    # Проверяем БД
    db_usage = check_database_usage()
    
    # Проверяем код
    code_usage = check_code_usage()
    
    # Финальные рекомендации
    print("\n" + "=" * 80)
    print("ФИНАЛЬНЫЕ РЕКОМЕНДАЦИИ")
    print("=" * 80)
    
    if db_usage or any(code_usage.values()):
        print("\n⚠️  Требуются действия:")
        
        if db_usage:
            print("\n1️⃣  Миграция данных:")
            print("   python scripts/migrations/migrate_room_reviews.py --dry-run")
            print("   python scripts/migrations/export_tasks_to_csv.py")
        
        if any(code_usage.values()):
            print("\n2️⃣  Обновление кода:")
            print("   - Замените deprecated модели на альтернативы")
            print("   - Запустите тесты")
        
        print("\n3️⃣  Через 6-12 месяцев:")
        print("   - Удалите deprecated модели из models.py")
        print("   - Создайте миграцию Django для удаления таблиц")
    else:
        print("\n✅ Всё готово к удалению deprecated моделей!")
        print("\n📝 Следующие шаги:")
        print("1. Удалите deprecated классы из models.py")
        print("2. Создайте миграцию: python manage.py makemigrations")
        print("3. Примените миграцию: python manage.py migrate")
        print("4. Обновите документацию")
    
    print("\n📚 Документация: docs/DEPRECATION_PLAN.md")
    print()


if __name__ == "__main__":
    main()
