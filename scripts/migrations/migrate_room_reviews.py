#!/usr/bin/env python
"""
Миграция отзывов из hotel.RoomReview в reviews.Review

Использование:
    python manage.py shell < scripts/migrations/migrate_room_reviews.py
    
Или через management command:
    python manage.py migrate_room_reviews
"""

import os
import sys
import django

# Setup Django
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    django.setup()

from django.db import transaction
from apps.hotel.models import RoomReview as OldReview
from apps.reviews.models import Review as NewReview
from django.utils import timezone


def migrate_room_reviews(dry_run=False):
    """
    Мигрирует отзывы из hotel.RoomReview в reviews.Review
    
    Args:
        dry_run: Если True, только показывает что будет сделано, не сохраняет
    """
    
    print("=" * 80)
    print("МИГРАЦИЯ ОТЗЫВОВ: hotel.RoomReview → reviews.Review")
    print("=" * 80)
    
    # Проверяем наличие старых отзывов
    old_reviews = OldReview.objects.all()
    total_count = old_reviews.count()
    
    if total_count == 0:
        print("✅ Нет отзывов для миграции в hotel.RoomReview")
        return
    
    print(f"\n📊 Найдено отзывов для миграции: {total_count}")
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - изменения не будут сохранены\n")
    
    migrated = 0
    skipped = 0
    errors = 0
    
    with transaction.atomic():
        for old_review in old_reviews:
            try:
                # Проверяем, не мигрирован ли уже этот отзыв
                if old_review.booking and NewReview.objects.filter(booking=old_review.booking).exists():
                    print(f"⏭️  Пропущен (уже существует): бронь {old_review.booking.confirmation_number}")
                    skipped += 1
                    continue
                
                # Создаем новый отзыв
                new_review = NewReview(
                    booking=old_review.booking,
                    author=old_review.guest,
                    
                    # Ratings - используем общую оценку для всех категорий
                    overall_rating=old_review.rating,
                    cleanliness_rating=old_review.cleanliness_rating or old_review.rating,
                    comfort_rating=old_review.comfort_rating or old_review.rating,
                    staff_rating=old_review.service_rating or old_review.rating,
                    value_rating=old_review.rating,  # Новое поле
                    location_rating=old_review.rating,  # Новое поле
                    
                    # Content
                    title=old_review.title or f"Отзыв о {old_review.category.name}",
                    text=old_review.body,
                    pros="",  # Старая модель не имела этого поля
                    cons="",  # Старая модель не имела этого поля
                    
                    # Moderation
                    status="approved" if old_review.is_approved else "pending",
                    moderated_by=old_review.approved_by,
                    moderated_at=old_review.approved_at,
                    moderation_comment="",
                    
                    # Publication
                    is_featured=False,
                    published_at=old_review.approved_at if old_review.is_approved else None,
                    
                    # Guest info
                    guest_name=old_review.guest.get_full_name() if old_review.guest else "Гость",
                    
                    # Timestamps
                    created_at=old_review.created_at,
                    updated_at=old_review.updated_at,
                )
                
                if not dry_run:
                    new_review.save()
                
                print(f"✅ Мигрирован: {old_review.guest} → {old_review.category.name} ({old_review.rating}★)")
                migrated += 1
                
            except Exception as e:
                print(f"❌ Ошибка при миграции отзыва #{old_review.pk}: {e}")
                errors += 1
                if not dry_run:
                    raise  # В production режиме откатываем всю транзакцию при ошибке
        
        if dry_run:
            print("\n⚠️  DRY RUN - откатываем транзакцию")
            transaction.set_rollback(True)
    
    # Итоги
    print("\n" + "=" * 80)
    print("ИТОГИ МИГРАЦИИ")
    print("=" * 80)
    print(f"✅ Мигрировано:  {migrated}")
    print(f"⏭️  Пропущено:    {skipped}")
    print(f"❌ Ошибок:       {errors}")
    print(f"📊 Всего:        {total_count}")
    
    if not dry_run and errors == 0:
        print("\n🎉 Миграция успешно завершена!")
        print("\n📝 Следующие шаги:")
        print("1. Проверьте новые отзывы в админке: /admin/reviews/review/")
        print("2. Убедитесь, что все данные корректны")
        print("3. После проверки можно удалить старые отзывы:")
        print("   python manage.py shell")
        print("   >>> from apps.hotel.models import RoomReview")
        print("   >>> RoomReview.objects.all().delete()")
    elif dry_run:
        print("\n💡 Для реальной миграции запустите без --dry-run")
    
    return migrated, skipped, errors


if __name__ == "__main__":
    # Проверяем аргументы
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    
    migrate_room_reviews(dry_run=dry_run)
