#!/usr/bin/env python
"""
Экспорт задач из crm.Task в CSV для импорта в Trello/Asana

Использование:
    python manage.py shell < scripts/migrations/export_tasks_to_csv.py
    
Или через management command:
    python manage.py export_tasks_to_csv
"""

import os
import sys
import csv
import django
from datetime import datetime

# Setup Django
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    django.setup()

from apps.crm.models import Task


def export_tasks_to_csv(output_file=None):
    """
    Экспортирует задачи в CSV файл
    
    Args:
        output_file: Путь к выходному файлу (по умолчанию: tasks_export_YYYYMMDD.csv)
    """
    
    print("=" * 80)
    print("ЭКСПОРТ ЗАДАЧ: crm.Task → CSV")
    print("=" * 80)
    
    # Получаем все задачи
    tasks = Task.objects.select_related(
        'created_by', 'assigned_to', 'client', 'booking'
    ).order_by('-created_at')
    
    total_count = tasks.count()
    
    if total_count == 0:
        print("✅ Нет задач для экспорта")
        return
    
    print(f"\n📊 Найдено задач: {total_count}")
    
    # Определяем имя файла
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"tasks_export_{timestamp}.csv"
    
    # Экспортируем в CSV
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            'ID',
            'Заголовок',
            'Описание',
            'Статус',
            'Приоритет',
            'Создал',
            'Исполниостиница',
            'Клиент',
            'Бронирование',
            'Срок',
            'Создано',
            'Выполнено',
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        exported = 0
        for task in tasks:
            writer.writerow({
                'ID': task.pk,
                'Заголовок': task.title,
                'Описание': task.description,
                'Статус': task.get_status_display(),
                'Приоритет': task.get_priority_display(),
                'Создал': task.created_by.get_full_name() if task.created_by else '',
                'Исполниостиница': task.assigned_to.get_full_name() if task.assigned_to else '',
                'Клиент': str(task.client.user) if task.client else '',
                'Бронирование': task.booking.confirmation_number if task.booking else '',
                'Срок': task.due_date.strftime('%d.%m.%Y') if task.due_date else '',
                'Создано': task.created_at.strftime('%d.%m.%Y %H:%M'),
                'Выполнено': task.completed_at.strftime('%d.%m.%Y %H:%M') if task.completed_at else '',
            })
            exported += 1
    
    # Итоги
    print("\n" + "=" * 80)
    print("ИТОГИ ЭКСПОРТА")
    print("=" * 80)
    print(f"✅ Экспортировано: {exported}")
    print(f"📄 Файл: {output_file}")
    
    print("\n📝 Следующие шаги:")
    print("1. Откройте файл в Excel/Google Sheets")
    print("2. Импортируйте задачи в Trello/Asana/Notion:")
    print("   - Trello: Board → Show Menu → More → Print and Export → Export as CSV")
    print("   - Asana: Project → ... → Import → CSV")
    print("   - Notion: Import → CSV")
    print("3. После успешного импорта можно удалить задачи из БД")
    
    # Статистика по статусам
    print("\n📊 Статистика по статусам:")
    from django.db.models import Count
    stats = Task.objects.values('status').annotate(count=Count('id')).order_by('-count')
    for stat in stats:
        status_display = dict(Task.TaskStatus.choices).get(stat['status'], stat['status'])
        print(f"   {status_display}: {stat['count']}")
    
    return output_file


if __name__ == "__main__":
    # Проверяем аргументы
    output_file = sys.argv[1] if len(sys.argv) > 1 else None
    
    export_tasks_to_csv(output_file=output_file)
