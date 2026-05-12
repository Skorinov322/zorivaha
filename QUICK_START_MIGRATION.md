# 🚀 Быстрый старт: Оптимизация БД

## ⚡ За 5 минут

### 1. Проверка текущего состояния
```bash
python manage.py check_deprecated_usage
```

### 2. Резервная копия (ОБЯЗАТЕЛЬНО!)
```bash
# SQLite
cp db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d)

# PostgreSQL
pg_dump zori_vaha > backup_$(date +%Y%m%d).sql
```

### 3. Миграция отзывов (если есть)
```bash
# Тест
python manage.py migrate_room_reviews --dry-run

# Реально
python manage.py migrate_room_reviews
```

### 4. Экспорт задач (если есть)
```bash
python scripts/migrations/export_tasks_to_csv.py
```

---

## 📋 Что deprecated?

| Модель | Альтернатива | Действие |
|--------|--------------|----------|
| `hotel.RoomReview` | `reviews.Review` | Мигрировать |
| `analytics.PageView` | Google Analytics | Отключить |
| `analytics.BookingFunnel` | Google Analytics | Отключить |
| `analytics.RevenueSnapshot` | `DailyMetrics` | Отключить |
| `crm.Interaction` | `BookingHistory` | Заменить в коде |
| `crm.Task` | Trello/Asana | Экспортировать |
| `crm.Message` | `ContactMessage` | Заменить в коде |

---

## 🎯 Следующие шаги

1. **Сейчас:** Проверка + резервная копия
2. **Через неделю:** Миграция отзывов
3. **Через месяц:** Экспорт задач
4. **Через 6 месяцев:** Удаление данных
5. **Через 12 месяцев:** Удаление моделей

---

## 📚 Полная документация

- **Детальное руководство:** `docs/MIGRATION_GUIDE.md`
- **План оптимизации:** `docs/db_optimization_plan.md`
- **План deprecation:** `docs/DEPRECATION_PLAN.md`
- **Скрипты:** `scripts/migrations/README.md`

---

## ⚠️ Важно!

- ✅ Всегда делайте резервную копию
- ✅ Используйте `--dry-run` для тестирования
- ✅ Проверяйте результаты после миграции
- ❌ Не удаляйте данные без проверки

---

## 🆘 Помощь

```bash
# Проверка
python manage.py check_deprecated_usage

# Миграция отзывов
python manage.py migrate_room_reviews --help

# Экспорт задач
python scripts/migrations/export_tasks_to_csv.py --help
```

Удачи! 🎉
