#!/usr/bin/env python
"""
Инициализация SQLite базы данных с минимальными таблицами для тестирования
"""

import sqlite3
import uuid
from datetime import datetime

def init_database():
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    # Создаем таблицу удобств
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hotel_amenity (
            id TEXT PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            icon VARCHAR(60) DEFAULT 'bi-check-circle',
            category VARCHAR(20) DEFAULT 'comfort',
            is_highlighted BOOLEAN DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Создаем таблицу категорий номеров
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hotel_roomcategory (
            id TEXT PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            slug VARCHAR(120) UNIQUE NOT NULL,
            description TEXT NOT NULL,
            short_description VARCHAR(255) NOT NULL,
            max_guests INTEGER DEFAULT 2,
            base_price_per_night DECIMAL(10,2) NOT NULL,
            area_sqm INTEGER,
            bed_type VARCHAR(20) DEFAULT 'double',
            is_active BOOLEAN DEFAULT 1,
            is_featured BOOLEAN DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Создаем таблицу связи категорий и удобств
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hotel_roomcategory_amenities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roomcategory_id TEXT NOT NULL,
            amenity_id TEXT NOT NULL,
            FOREIGN KEY (roomcategory_id) REFERENCES hotel_roomcategory (id),
            FOREIGN KEY (amenity_id) REFERENCES hotel_amenity (id),
            UNIQUE(roomcategory_id, amenity_id)
        )
    """)
    
    # Создаем таблицу номеров
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hotel_room (
            id TEXT PRIMARY KEY,
            category_id TEXT NOT NULL,
            number VARCHAR(10) NOT NULL,
            subdivision VARCHAR(5) DEFAULT '',
            floor INTEGER NOT NULL,
            max_guests_per_room INTEGER DEFAULT 2,
            status VARCHAR(20) DEFAULT 'available',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES hotel_roomcategory (id)
        )
    """)
    
    print("✓ Таблицы созданы")
    
    # Создаем удобства
    amenities_data = [
        ('Wi-Fi', 'bi-wifi', 'tech'),
        ('Кондиционер', 'bi-thermometer-sun', 'comfort'),
        ('Телевизор', 'bi-tv', 'tech'),
        ('Мини-бар', 'bi-cup-hot', 'food'),
        ('Сейф', 'bi-shield-check', 'service'),
        ('Балкон', 'bi-door-open', 'comfort'),
        ('Джакузи', 'bi-water', 'wellness'),
    ]
    
    amenity_ids = {}
    now = datetime.now().isoformat()
    
    for name, icon, category in amenities_data:
        amenity_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT OR IGNORE INTO hotel_amenity 
            (id, name, icon, category, is_highlighted, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, 0, 0, ?, ?)
        """, (amenity_id, name, icon, category, now, now))
        amenity_ids[name] = amenity_id
        print(f"✓ Создано удобство: {name}")
    
    # Создаем категории номеров
    categories_data = [
        {
            'name': 'Эконом',
            'slug': 'econom',
            'description': 'Уютные номера эконом-класса с базовым набором удобств. Идеально подходят для бюджетного размещения.',
            'short_description': 'Бюджетный вариант размещения с основными удобствами',
            'max_guests': 2,
            'base_price_per_night': 2500.00,
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
            'base_price_per_night': 3500.00,
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
            'base_price_per_night': 4500.00,
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
            'base_price_per_night': 6500.00,
            'area_sqm': 35,
            'bed_type': 'king',
            'amenities': ['Wi-Fi', 'Кондиционер', 'Телевизор', 'Мини-бар', 'Сейф', 'Балкон', 'Джакузи'],
            'is_featured': False,
        },
        {
            'name': 'Семейный',
            'slug': 'semejnyj',
            'description': 'Просторный семейный номер с дополниостиницаными спальными местами, идеально подходящий для отдыха с детьми.',
            'short_description': 'Просторный номер для семейного отдыха',
            'max_guests': 6,
            'base_price_per_night': 5500.00,
            'area_sqm': 40,
            'bed_type': 'twin',
            'amenities': ['Wi-Fi', 'Кондиционер', 'Телевизор', 'Мини-бар', 'Сейф'],
            'is_featured': False,
        },
    ]
    
    created_count = 0
    
    for i, cat_data in enumerate(categories_data):
        category_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT OR IGNORE INTO hotel_roomcategory 
            (id, name, slug, description, short_description, max_guests, 
             base_price_per_night, area_sqm, bed_type, is_active, is_featured, 
             sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
        """, (
            category_id, cat_data['name'], cat_data['slug'], 
            cat_data['description'], cat_data['short_description'],
            cat_data['max_guests'], cat_data['base_price_per_night'],
            cat_data['area_sqm'], cat_data['bed_type'],
            1 if cat_data['is_featured'] else 0,
            i + 1, now, now
        ))
        
        if cursor.rowcount > 0:
            created_count += 1
            print(f"✓ Создана категория: {cat_data['name']} ({cat_data['base_price_per_night']} ₽/ночь)")
            
            # Добавляем связи с удобствами
            for amenity_name in cat_data['amenities']:
                if amenity_name in amenity_ids:
                    cursor.execute("""
                        INSERT OR IGNORE INTO hotel_roomcategory_amenities 
                        (roomcategory_id, amenity_id)
                        VALUES (?, ?)
                    """, (category_id, amenity_ids[amenity_name]))
            
            # Создаем физические номера
            room_numbers = {
                'econom': ['101', '102', '103'],
                'standart': ['201', '202', '203', '204'],
                'poluluks': ['301', '302'],
                'luks': ['401'],
                'semejnyj': ['501', '502'],
            }
            
            if cat_data['slug'] in room_numbers:
                for room_num in room_numbers[cat_data['slug']]:
                    room_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT OR IGNORE INTO hotel_room 
                        (id, category_id, number, subdivision, floor, 
                         max_guests_per_room, status, created_at, updated_at)
                        VALUES (?, ?, ?, '', ?, ?, 'available', ?, ?)
                    """, (
                        room_id, category_id, room_num, 
                        int(room_num[0]), cat_data['max_guests'],
                        now, now
                    ))
                    if cursor.rowcount > 0:
                        print(f"  ✓ Создан номер: {room_num}")
        else:
            print(f"- Категория уже существует: {cat_data['name']}")
    
    # Сохраняем изменения
    conn.commit()
    
    # Проверяем что создалось
    cursor.execute("SELECT COUNT(*) FROM hotel_roomcategory WHERE is_active = 1")
    total_categories = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM hotel_room")
    total_rooms = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM hotel_amenity")
    total_amenities = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n🎉 База данных инициализирована!")
    print(f"📊 Создано категорий: {total_categories}")
    print(f"📊 Создано номеров: {total_rooms}")
    print(f"📊 Создано удобств: {total_amenities}")
    print("\nТеперь категории должны отображаться на странице /номера/")

if __name__ == '__main__':
    init_database()