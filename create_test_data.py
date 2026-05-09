#!/usr/bin/env python
"""
Простой скрипт для создания тестовых данных без зависимостей.
Запуск: python create_test_data.py
"""

import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Минимальные настройки Django без внешних зависимостей
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': 'db.sqlite3',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'apps.core',
            'apps.hotel',
        ],
        SECRET_KEY='test-key-for-data-creation',
        USE_TZ=True,
    )

django.setup()

# Теперь импортируем модели
from apps.hotel.models import RoomCategory, Room, Amenity

def create_test_data():
    print("Создание тестовых данных...")
    
    # Создаем удобства
    amenities_data = [
        {'name': 'Wi-Fi', 'icon': 'bi-wifi', 'category': 'tech'},
        {'name': 'Кондиционер', 'icon': 'bi-thermometer-sun', 'category': 'comfort'},
        {'name': 'Телевизор', 'icon': 'bi-tv', 'category': 'tech'},
        {'name': 'Мини-бар', 'icon': 'bi-cup-hot', 'category': 'food'},
        {'name': 'Сейф', 'icon': 'bi-shield-check', 'category': 'service'},
        {'name': 'Балкон', 'icon': 'bi-door-open', 'category': 'comfort'},
        {'name': 'Джакузи', 'icon': 'bi-water', 'category': 'wellness'},
    ]
    
    created_amenities = {}
    for amenity_data in amenities_data:
        amenity, created = Amenity.objects.get_or_create(
            name=amenity_data['name'],
            defaults={
                'icon': amenity_data['icon'],
                'category': amenity_data['category'],
            }
        )
        created_amenities[amenity_data['name']] = amenity
        if created:
            print(f'✓ Создано удобство: {amenity.name}')
    
    # Создаем категории номеров
    categories_data = [
        {
            'name': 'Эконом',
            'slug': 'econom',
            'description': 'Уютные номера эконом-класса с базовым набором удобств. Идеально подходят для бюджетного размещения.',
            'short_description': 'Бюджетный вариант размещения с основными удобствами',
            'max_guests': 2,
            'base_price_per_night': 2500,
            'area_sqm': 18,
            'bed_type': 'single',
            'amenities': ['Wi-Fi', 'Телевизор'],
            'is_featured': True,
        },
        {
            'name': 'Стандарт',
            'slug': 'standart',
            'description': 'Комфортабельные номера стандартной категории с современными удобствами и уютной обстановкой.',
            'short_description': 'Комфортабельный номер с современными удобствами',
            'max_guests': 2,
            'base_price_per_night': 3500,
            'area_sqm': 22,
            'bed_type': 'double',
            'amenities': ['Wi-Fi', 'Кондиционер', 'Телевизор', 'Мини-бар'],
            'is_featured': True,
        },
        {
            'name': 'Полулюкс',
            'slug': 'poluluks',
            'description': 'Просторный номер с улучшенным интерьером и расширенным набором удобств для комфортного проживания.',
            'short_description': 'Просторный номер с улучшенным интерьером',
            'max_guests': 3,
            'base_price_per_night': 4500,
            'area_sqm': 28,
            'bed_type': 'double',
            'amenities': ['Wi-Fi', 'Кондиционер', 'Телевизор', 'Мини-бар', 'Сейф', 'Балкон'],
            'is_featured': True,
        },
        {
            'name': 'Люкс',
            'slug': 'luks',
            'description': 'Роскошный номер с панорамными видами и премиальными удобствами для особых случаев.',
            'short_description': 'Роскошный номер с панорамными видами',
            'max_guests': 4,
            'base_price_per_night': 6500,
            'area_sqm': 35,
            'bed_type': 'king',
            'amenities': ['Wi-Fi', 'Кондиционер', 'Телевизор', 'Мини-бар', 'Сейф', 'Балкон', 'Джакузи'],
            'is_featured': False,
        },
        {
            'name': 'Семейный',
            'slug': 'semejnyj',
            'description': 'Просторный семейный номер с дополнительными спальными местами, идеально подходящий для отдыха с детьми.',
            'short_description': 'Просторный номер для семейного отдыха',
            'max_guests': 6,
            'base_price_per_night': 5500,
            'area_sqm': 40,
            'bed_type': 'twin',
            'amenities': ['Wi-Fi', 'Кондиционер', 'Телевизор', 'Мини-бар', 'Сейф'],
            'is_featured': False,
        },
    ]
    
    created_count = 0
    
    for i, cat_data in enumerate(categories_data):
        category, created = RoomCategory.objects.get_or_create(
            slug=cat_data['slug'],
            defaults={
                'name': cat_data['name'],
                'description': cat_data['description'],
                'short_description': cat_data['short_description'],
                'max_guests': cat_data['max_guests'],
                'base_price_per_night': cat_data['base_price_per_night'],
                'area_sqm': cat_data['area_sqm'],
                'bed_type': cat_data['bed_type'],
                'is_active': True,
                'is_featured': cat_data['is_featured'],
                'sort_order': i + 1,
            }
        )
        
        if created:
            # Добавляем удобства
            amenity_objects = [created_amenities[name] for name in cat_data['amenities'] if name in created_amenities]
            category.amenities.set(amenity_objects)
            
            created_count += 1
            print(f'✓ Создана категория: {category.name} ({category.base_price_per_night} ₽/ночь)')
            
            # Создаем несколько физических номеров для каждой категории
            room_numbers = {
                'econom': ['101', '102', '103'],
                'standart': ['201', '202', '203', '204'],
                'poluluks': ['301', '302'],
                'luks': ['401'],
                'semejnyj': ['501', '502'],
            }
            
            if cat_data['slug'] in room_numbers:
                for room_num in room_numbers[cat_data['slug']]:
                    room, room_created = Room.objects.get_or_create(
                        category=category,
                        number=room_num,
                        defaults={
                            'floor': int(room_num[0]),
                            'max_guests_per_room': cat_data['max_guests'],
                            'status': 'available',  # Room.RoomStatus.AVAILABLE
                        }
                    )
                    if room_created:
                        print(f'  ✓ Создан номер: {room.number}')
        else:
            print(f'- Категория уже существует: {category.name}')
    
    print(f'\n🎉 Создано {created_count} новых категорий номеров!')
    print('Теперь категории должны отображаться на странице /номера/')
    
    # Проверяем что создалось
    total_categories = RoomCategory.objects.filter(is_active=True).count()
    total_rooms = Room.objects.count()
    print(f'📊 Всего активных категорий: {total_categories}')
    print(f'📊 Всего номеров: {total_rooms}')

if __name__ == '__main__':
    create_test_data()