"""
Management command для проверки использования deprecated моделей

Использование:
    python manage.py check_deprecated_usage
"""

from django.core.management.base import BaseCommand
from apps.hotel.models import RoomReview
from apps.analytics.models import PageView, BookingFunnel, RevenueSnapshot
from apps.crm.models import Interaction, Task, Message


class Command(BaseCommand):
    help = 'Проверяет использование deprecated моделей в БД'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("ПРОВЕРКА DEPRECATED МОДЕЛЕЙ В БД"))
        self.stdout.write("=" * 80)
        
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
                
                if count == 0:
                    self.stdout.write(
                        self.style.SUCCESS(f"\n✅ {model_name}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"\n⚠️  {model_name}")
                    )
                    has_data.append((model_name, count, alternative))
                
                self.stdout.write(f"   Записей в БД: {count}")
                self.stdout.write(f"   Альтернатива: {alternative}")
                
                if count > 0:
                    # Показываем последние записи
                    recent = model_class.objects.order_by('-created_at')[:3] if hasattr(model_class, 'created_at') else model_class.objects.all()[:3]
                    if recent:
                        self.stdout.write(f"   Последние записи:")
                        for obj in recent:
                            self.stdout.write(f"      - {obj}")
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ {model_name}: Ошибка проверки - {e}")
                )
        
        # Итоги
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("ИТОГИ"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"📊 Всего записей в deprecated таблицах: {total_records}")
        
        if has_data:
            self.stdout.write(
                self.style.WARNING(f"\n⚠️  Найдены данные в {len(has_data)} deprecated таблицах:")
            )
            for model_name, count, alternative in has_data:
                self.stdout.write(f"   • {model_name}: {count} записей → {alternative}")
            
            self.stdout.write("\n📝 Рекомендации:")
            self.stdout.write("1. Запустите скрипты миграции для переноса данных:")
            self.stdout.write("   python manage.py migrate_room_reviews --dry-run")
            self.stdout.write("2. Перестаньте использовать deprecated модели в новом коде")
            self.stdout.write("3. Через 6-12 месяцев удалите deprecated модели")
        else:
            self.stdout.write(
                self.style.SUCCESS("\n✅ Отлично! Нет данных в deprecated таблицах")
            )
            self.stdout.write("   Можно безопасно удалить deprecated модели")
        
        self.stdout.write("\n📚 Документация: docs/DEPRECATION_PLAN.md")
