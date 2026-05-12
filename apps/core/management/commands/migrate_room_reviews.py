"""
Management command для миграции отзывов из hotel.RoomReview в reviews.Review

Использование:
    python manage.py migrate_room_reviews
    python manage.py migrate_room_reviews --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.hotel.models import RoomReview as OldReview
from apps.reviews.models import Review as NewReview


class Command(BaseCommand):
    help = 'Мигрирует отзывы из hotel.RoomReview в reviews.Review'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет сделано, но не сохранять изменения',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("МИГРАЦИЯ ОТЗЫВОВ: hotel.RoomReview → reviews.Review"))
        self.stdout.write("=" * 80)
        
        # Проверяем наличие старых отзывов
        old_reviews = OldReview.objects.all()
        total_count = old_reviews.count()
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("\n✅ Нет отзывов для миграции в hotel.RoomReview"))
            return
        
        self.stdout.write(f"\n📊 Найдено отзывов для миграции: {total_count}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠️  DRY RUN MODE - изменения не будут сохранены\n"))
        
        migrated = 0
        skipped = 0
        errors = 0
        
        with transaction.atomic():
            for old_review in old_reviews:
                try:
                    # Проверяем, не мигрирован ли уже этот отзыв
                    if old_review.booking and NewReview.objects.filter(booking=old_review.booking).exists():
                        self.stdout.write(
                            self.style.WARNING(
                                f"⏭️  Пропущен (уже существует): бронь {old_review.booking.confirmation_number}"
                            )
                        )
                        skipped += 1
                        continue
                    
                    # Создаем новый отзыв
                    new_review = NewReview(
                        booking=old_review.booking,
                        author=old_review.guest,
                        
                        # Ratings
                        overall_rating=old_review.rating,
                        cleanliness_rating=old_review.cleanliness_rating or old_review.rating,
                        comfort_rating=old_review.comfort_rating or old_review.rating,
                        staff_rating=old_review.service_rating or old_review.rating,
                        value_rating=old_review.rating,
                        location_rating=old_review.rating,
                        
                        # Content
                        title=old_review.title or f"Отзыв о {old_review.category.name}",
                        text=old_review.body,
                        pros="",
                        cons="",
                        
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
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Мигрирован: {old_review.guest} → {old_review.category.name} ({old_review.rating}★)"
                        )
                    )
                    migrated += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"❌ Ошибка при миграции отзыва #{old_review.pk}: {e}")
                    )
                    errors += 1
                    if not dry_run:
                        raise
            
            if dry_run:
                self.stdout.write(self.style.WARNING("\n⚠️  DRY RUN - откатываем транзакцию"))
                transaction.set_rollback(True)
        
        # Итоги
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("ИТОГИ МИГРАЦИИ"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"✅ Мигрировано:  {migrated}")
        self.stdout.write(f"⏭️  Пропущено:    {skipped}")
        self.stdout.write(f"❌ Ошибок:       {errors}")
        self.stdout.write(f"📊 Всего:        {total_count}")
        
        if not dry_run and errors == 0:
            self.stdout.write(self.style.SUCCESS("\n🎉 Миграция успешно завершена!"))
            self.stdout.write("\n📝 Следующие шаги:")
            self.stdout.write("1. Проверьте новые отзывы в админке: /admin/reviews/review/")
            self.stdout.write("2. Убедитесь, что все данные корректны")
            self.stdout.write("3. После проверки можно удалить старые отзывы:")
            self.stdout.write("   python manage.py shell")
            self.stdout.write("   >>> from apps.hotel.models import RoomReview")
            self.stdout.write("   >>> RoomReview.objects.all().delete()")
        elif dry_run:
            self.stdout.write(self.style.WARNING("\n💡 Для реальной миграции запустите без --dry-run"))
