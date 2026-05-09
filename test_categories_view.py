#!/usr/bin/env python
"""
Тестовое представление для проверки категорий номеров
"""

import sqlite3

def test_categories():
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    # Проверяем категории
    cursor.execute("""
        SELECT name, slug, short_description, base_price_per_night, is_active, is_featured
        FROM hotel_roomcategory 
        WHERE is_active = 1
        ORDER BY sort_order, name
    """)
    
    categories = cursor.fetchall()
    
    print("🏨 Активные категории номеров:")
    print("=" * 60)
    
    if not categories:
        print("❌ Категории не найдены!")
        return
    
    for cat in categories:
        name, slug, description, price, is_active, is_featured = cat
        featured_mark = "⭐" if is_featured else "  "
        print(f"{featured_mark} {name} ({slug})")
        print(f"   💰 {price} ₽/ночь")
        print(f"   📝 {description}")
        
        # Проверяем удобства для этой категории
        cursor.execute("""
            SELECT a.name, a.icon 
            FROM hotel_amenity a
            JOIN hotel_roomcategory_amenities rca ON a.id = rca.amenity_id
            JOIN hotel_roomcategory rc ON rc.id = rca.roomcategory_id
            WHERE rc.slug = ?
        """, (slug,))
        
        amenities = cursor.fetchall()
        if amenities:
            amenity_names = [f"{icon} {name}" for name, icon in amenities]
            print(f"   🛎️  {', '.join(amenity_names)}")
        
        # Проверяем номера для этой категории
        cursor.execute("""
            SELECT number, status 
            FROM hotel_room r
            JOIN hotel_roomcategory rc ON rc.id = r.category_id
            WHERE rc.slug = ?
            ORDER BY number
        """, (slug,))
        
        rooms = cursor.fetchall()
        if rooms:
            room_list = [f"{num}({status})" for num, status in rooms]
            print(f"   🏠 Номера: {', '.join(room_list)}")
        
        print()
    
    conn.close()
    
    print(f"✅ Найдено {len(categories)} активных категорий")
    print("\nЕсли категории не отображаются на сайте, проверьте:")
    print("1. Запущен ли сервер Django")
    print("2. Правильно ли настроены URL-ы")
    print("3. Нет ли ошибок в шаблонах")

if __name__ == '__main__':
    test_categories()