"""
Management command to set up economy rooms with subdivisions and multiple occupancy.
Usage: python manage.py setup_economy_rooms
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.hotel.models import RoomCategory, Room


class Command(BaseCommand):
    help = 'Настройка номеров эконом-класса с подразделениями и множественным заселением'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет создано без фактического создания',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('РЕЖИМ ПРЕДВАРИТЕЛЬНОГО ПРОСМОТРА'))
        
        try:
            # Find or create economy category
            economy_category, created = RoomCategory.objects.get_or_create(
                slug='econom',
                defaults={
                    'name': 'Эконом',
                    'description': 'Экономичные номера с возможностью размещения нескольких гостей',
                    'short_description': 'Бюджетный вариант размещения',
                    'max_guests': 4,
                    'base_price_per_night': 1500,
                    'area_sqm': 20,
                    'is_active': True,
                }
            )
            
            if created and not dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f'Создана категория: {economy_category.name}')
                )
            elif not dry_run:
                self.stdout.write(f'Найдена категория: {economy_category.name}')
            
            # Create economy rooms with subdivisions
            rooms_to_create = [
                # Room 303 with subdivisions a and b
                {'number': '303', 'subdivision': 'а', 'floor': 3, 'max_concurrent': 2},
                {'number': '303', 'subdivision': 'б', 'floor': 3, 'max_concurrent': 2},
                
                # Room 304 with subdivisions a and b  
                {'number': '304', 'subdivision': 'а', 'floor': 3, 'max_concurrent': 2},
                {'number': '304', 'subdivision': 'б', 'floor': 3, 'max_concurrent': 2},
                
                # Room 305 - single room but allows multiple guests
                {'number': '305', 'subdivision': '', 'floor': 3, 'max_concurrent': 3},
                
                # Room 401 with subdivisions
                {'number': '401', 'subdivision': 'а', 'floor': 4, 'max_concurrent': 2},
                {'number': '401', 'subdivision': 'б', 'floor': 4, 'max_concurrent': 2},
            ]
            
            created_count = 0
            
            with transaction.atomic():
                for room_data in rooms_to_create:
                    room, created = Room.objects.get_or_create(
                        category=economy_category,
                        number=room_data['number'],
                        subdivision=room_data['subdivision'],
                        defaults={
                            'floor': room_data['floor'],
                            'max_guests_per_room': room_data['max_concurrent'],
                            'status': Room.RoomStatus.AVAILABLE,
                        }
                    )
                    
                    if created:
                        created_count += 1
                        if not dry_run:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'Создан номер: {room.full_number} '
                                    f'(макс. {room.max_guests_per_room} персон)'
                                )
                            )
                        else:
                            self.stdout.write(
                                f'Будет создан: {room.full_number} '
                                f'(макс. {room_data["max_concurrent"]} броней)'
                            )
                    else:
                        if not dry_run:
                            self.stdout.write(f'Уже существует: {room.full_number}')
                
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(f'Будет создано {created_count} новых номеров')
                    )
                    # Rollback transaction in dry run
                    transaction.set_rollback(True)
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'Создано {created_count} новых номеров')
                    )
            
            if not dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        '\nНастройка завершена! Теперь администраторы могут:\n'
                        '- Заселять несколько гостей в один номер эконом-класса\n'
                        '- Использовать подразделения номеров (303а, 303б)\n'
                        '- Видеть текущую заполненность номеров в админке'
                    )
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при настройке номеров: {e}')
            )
            raise