# Скрипты миграции для оптимизации БД

## 📋 Обзор

Эта папка содержит скрипты для постепенной миграции данных из deprecated моделей в новые.

## 🚀 Быстрый старт

### 1. Проверка текущего состояния

```bash
# Через management command (рекомендуется)
python manage.py check_deprecated_usage

# Или напрямую через скрипт
python scripts/migrations/check_deprecated_usage.py
```

### 2. Миграция отзывов (RoomReview → Review)

```bash
# Тестовый запуск (без сохранения)
python manage.py migrate_room_reviews --dry-run

# Реальная миграция
python manage.py migrate_room_reviews
```

### 3. Экспорт задач в CSV

```bash
# Экспорт в файл с датой
python scripts/migrations/export_tasks_to_csv.py

# Экспорт в конкретный файл
python scripts/migrations/export_tasks_to_csv.py my_tasks.csv
```

## 📁 Доступные скрипты

### check_deprecated_usage.py
**Назначение:** Проверяет использование deprecated моделей в БД и коде

**Что проверяет:**
- Количество записей в deprecated таблицах
- Использование deprecated моделей в Python коде
- Последние записи в каждой таблице

**Использование:**
```bash
python manage.py check_deprecated_usage
```

**Вывод:**
- ✅ Зеленый - нет данных, можно удалять
- ⚠️  Желтый - есть данные, нужна миграция
- ❌ Красный - ошибка проверки

---

### migrate_room_reviews.py
**Назначение:** Мигрирует отзывы из `hotel.RoomReview` в `reviews.Review`

**Что делает:**
- Переносит все поля отзывов
- Сохраняет связи с бронированиями
- Переносит статус модерации
- Сохраняет временные метки

**Использование:**
```bash
# Тестовый запуск
python manage.py migrate_room_reviews --dry-run

# Реальная миграция
python manage.py migrate_room_reviews
```

**Безопасность:**
- Использует транзакции (откат при ошибке)
- Пропускает уже мигрированные отзывы
- Режим dry-run для тестирования

**После миграции:**
1. Проверьте данные в админке: `/admin/reviews/review/`
2. Убедитесь, что всё корректно
3. Удалите старые отзывы:
   ```python
   python manage.py shell
   >>> from apps.hotel.models import RoomReview
   >>> RoomReview.objects.all().delete()
   ```

---

### export_tasks_to_csv.py
**Назначение:** Экспортирует задачи из `crm.Task` в CSV для импорта в Trello/Asana

**Что экспортирует:**
- Заголовок и описание
- Статус и приоритет
- Создатель и исполнитель
- Связанный клиент и бронирование
- Сроки и даты

**Использование:**
```bash
# Экспорт с автоматическим именем файла
python scripts/migrations/export_tasks_to_csv.py

# Экспорт в конкретный файл
python scripts/migrations/export_tasks_to_csv.py tasks_2024.csv
```

**Формат CSV:**
- Кодировка: UTF-8 with BOM (для Excel)
- Разделитель: запятая
- Заголовки: русские названия

**Импорт в другие системы:**
- **Trello:** Board → Menu → More → Print and Export → Export as CSV
- **Asana:** Project → ... → Import → CSV
- **Notion:** Import → CSV
- **Excel/Google Sheets:** Открыть напрямую

---

## 🗺️ План миграции

### Этап 1: Подготовка (сейчас)
- [x] Пометить deprecated модели
- [x] Создать скрипты миграции
- [x] Обновить документацию

### Этап 2: Проверка (1-2 недели)
- [ ] Запустить `check_deprecated_usage`
- [ ] Проверить, используются ли deprecated модели
- [ ] Обновить код, если нужно

### Этап 3: Миграция данных (1-3 месяца)
- [ ] Мигрировать отзывы: `migrate_room_reviews`
- [ ] Экспортировать задачи: `export_tasks_to_csv`
- [ ] Импортировать задачи в Trello/Asana
- [ ] Проверить целостность данных

### Этап 4: Очистка (через 6-12 месяцев)
- [ ] Удалить данные из deprecated таблиц
- [ ] Удалить deprecated модели из кода
- [ ] Создать миграцию Django для удаления таблиц
- [ ] Обновить документацию

---

## ⚠️ Важные замечания

### Безопасность
1. **Всегда делайте резервную копию БД перед миграцией!**
   ```bash
   # PostgreSQL
   pg_dump dbname > backup_$(date +%Y%m%d).sql
   
   # SQLite
   cp db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d)
   ```

2. **Используйте --dry-run для тестирования**
   ```bash
   python manage.py migrate_room_reviews --dry-run
   ```

3. **Проверяйте результаты после каждого шага**

### Откат изменений
Если что-то пошло не так:

1. **Восстановить из резервной копии:**
   ```bash
   # PostgreSQL
   psql dbname < backup_20240101.sql
   
   # SQLite
   cp db.sqlite3.backup_20240101 db.sqlite3
   ```

2. **Удалить мигрированные данные:**
   ```python
   # Если миграция прошла, но данные неверные
   from apps.reviews.models import Review
   Review.objects.filter(created_at__gte='2024-01-01').delete()
   ```

### Производительность
- Миграция больших объемов данных может занять время
- Рекомендуется запускать в нерабочее время
- Используйте `--dry-run` для оценки времени

---

## 📊 Статистика

После запуска скриптов вы увидите:

```
================================================================================
ИТОГИ МИГРАЦИИ
================================================================================
✅ Мигрировано:  150
⏭️  Пропущено:    5
❌ Ошибок:       0
📊 Всего:        155

🎉 Миграция успешно завершена!
```

---

## 🆘 Помощь

### Частые проблемы

**Проблема:** `ModuleNotFoundError: No module named 'apps'`
**Решение:** Запускайте скрипты из корня проекта

**Проблема:** `django.core.exceptions.ImproperlyConfigured`
**Решение:** Установите переменную окружения:
```bash
export DJANGO_SETTINGS_MODULE=config.settings.dev
```

**Проблема:** Ошибка при миграции отзывов
**Решение:** 
1. Проверьте, что все связанные объекты существуют
2. Используйте `--dry-run` для диагностики
3. Проверьте логи

### Контакты
- Документация: `docs/DEPRECATION_PLAN.md`
- Основной план: `docs/db_optimization_plan.md`

---

## 📝 Чеклист миграции

Используйте этот чеклист для отслеживания прогресса:

- [ ] Создана резервная копия БД
- [ ] Запущена проверка: `check_deprecated_usage`
- [ ] Обновлен код (если нужно)
- [ ] Тестовая миграция отзывов: `--dry-run`
- [ ] Реальная миграция отзывов
- [ ] Проверка данных в админке
- [ ] Экспорт задач в CSV
- [ ] Импорт задач в Trello/Asana
- [ ] Проверка целостности данных
- [ ] Удаление старых данных (через 6 месяцев)
- [ ] Удаление deprecated моделей (через 12 месяцев)
- [ ] Обновление документации

---

## 🎯 Следующие шаги

1. **Сейчас:**
   ```bash
   python manage.py check_deprecated_usage
   ```

2. **Через 1-2 недели:**
   ```bash
   python manage.py migrate_room_reviews --dry-run
   ```

3. **Через 1 месяц:**
   ```bash
   python manage.py migrate_room_reviews
   python scripts/migrations/export_tasks_to_csv.py
   ```

4. **Через 6-12 месяцев:**
   - Удалить deprecated модели
   - Создать финальную миграцию Django

Удачи! 🚀
