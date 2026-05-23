# Руководство по миграции БД (Мягкая оптимизация)

## 🎯 Цель

Постепенно оптимизировать структуру БД, убрав дублирование и избыточные модели, без риска потери данных.

## 📅 Временная шкала

```
Сейчас          1 месяц         3 месяца        6 месяцев       12 месяцев
  │                │                │                │                │
  ▼                ▼                ▼                ▼                ▼
Пометка       Миграция        Проверка         Очистка         Удаление
deprecated     данных          работы           данных          моделей
```

## 🚀 Быстрый старт

### Шаг 1: Проверка текущего состояния

```bash
# Проверить, какие deprecated модели используются
python manage.py check_deprecated_usage
```

**Что вы увидите:**
- ✅ Зеленый - нет данных, безопасно
- ⚠️  Желтый - есть данные, нужна миграция
- ❌ Красный - ошибка

### Шаг 2: Резервная копия БД

**ОБЯЗАТЕЛЬНО перед любой миграцией!**

```bash
# PostgreSQL
pg_dump zori_vaha > backup_$(date +%Y%m%d).sql

# SQLite
cp db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d)
```

### Шаг 3: Миграция отзывов (если есть)

```bash
# Тестовый запуск (безопасно)
python manage.py migrate_room_reviews --dry-run

# Если всё ОК - реальная миграция
python manage.py migrate_room_reviews
```

### Шаг 4: Экспорт задач (если есть)

```bash
# Экспортировать задачи в CSV
python scripts/migrations/export_tasks_to_csv.py

# Импортировать в Trello/Asana/Notion
# (см. инструкции ниже)
```

---

## 📋 Детальные инструкции

### 1. Миграция отзывов: RoomReview → Review

#### Зачем?
- `hotel.RoomReview` - старая модель с ограниченным функционалом
- `reviews.Review` - новая модель с модерацией, ответами, детальными оценками

#### Как мигрировать?

**Шаг 1: Проверка**
```bash
python manage.py shell
>>> from apps.hotel.models import RoomReview
>>> RoomReview.objects.count()
# Если 0 - миграция не нужна
```

**Шаг 2: Тестовая миграция**
```bash
python manage.py migrate_room_reviews --dry-run
```

Проверьте вывод:
- Сколько отзывов будет мигрировано
- Есть ли ошибки
- Какие данные будут перенесены

**Шаг 3: Реальная миграция**
```bash
python manage.py migrate_room_reviews
```

**Шаг 4: Проверка результата**
1. Откройте админку: `/admin/reviews/review/`
2. Проверьте несколько отзывов:
   - Правильные ли оценки
   - Сохранились ли тексты
   - Корректные ли даты
3. Проверьте связи с бронированиями

**Шаг 5: Удаление старых данных (через 1-2 месяца)**
```python
python manage.py shell
>>> from apps.hotel.models import RoomReview
>>> RoomReview.objects.all().delete()
```

---

### 2. Экспорт задач: Task → Trello/Asana

#### Зачем?
- `crm.Task` - избыточно для малого отеля
- Внешние сервисы (Trello, Asana) - лучше для управления задачами

#### Как экспортировать?

**Шаг 1: Экспорт в CSV**
```bash
python scripts/migrations/export_tasks_to_csv.py
```

Будет создан файл: `tasks_export_YYYYMMDD_HHMMSS.csv`

**Шаг 2: Импорт в Trello**
1. Откройте доску Trello
2. Menu → More → Print and Export → Export as CSV
3. Скачайте шаблон CSV
4. Адаптируйте ваш CSV под формат Trello
5. Импортируйте обратно

**Шаг 3: Импорт в Asana**
1. Откройте проект Asana
2. ... → Import → CSV
3. Выберите файл `tasks_export_*.csv`
4. Сопоставьте колонки
5. Импортируйте

**Шаг 4: Импорт в Notion**
1. Создайте новую базу данных
2. Import → CSV
3. Выберите файл
4. Настройте типы полей

**Шаг 5: Удаление старых задач (через 3-6 месяцев)**
```python
python manage.py shell
>>> from apps.crm.models import Task
>>> Task.objects.all().delete()
```

---

### 3. Отключение аналитики: PageView, BookingFunnel

#### Зачем?
- Избыточно - есть Google Analytics
- Занимает место в БД
- Не используется в отчетах

#### Как отключить?

**Шаг 1: Отключить middleware (если есть)**
```python
# config/settings/base.py
MIDDLEWARE = [
    # ...
    # Закомментируйте или удалите:
    # "apps.analytics.middleware.PageViewMiddleware",
]
```

**Шаг 2: Проверить, что новые данные не пишутся**
```bash
# Через неделю проверьте
python manage.py shell
>>> from apps.analytics.models import PageView
>>> PageView.objects.filter(viewed_at__gte='2024-01-01').count()
# Должно быть 0
```

**Шаг 3: Удалить старые данные (через 3-6 месяцев)**
```python
python manage.py shell
>>> from apps.analytics.models import PageView, BookingFunnel
>>> PageView.objects.all().delete()
>>> BookingFunnel.objects.all().delete()
```

---

### 4. Замена Interaction → BookingHistory + AdminComment

#### Зачем?
- `crm.Interaction` дублирует функционал
- `BookingHistory` - для истории броней
- `AdminComment` - для заметок о клиентах

#### Как заменить?

**Вместо Interaction используйте:**

**Для истории бронирований:**
```python
# Старый код (deprecated)
Interaction.objects.create(
    client=client_profile,
    booking=booking,
    interaction_type='call',
    subject='Звонок клиенту',
    body='Подтвердили бронь',
)

# Новый код
BookingHistory.objects.create(
    booking=booking,
    action='note_added',
    note='Звонок клиенту: подтвердили бронь',
    changed_by=request.user,
)
```

**Для заметок о клиентах:**
```python
# Старый код (deprecated)
Interaction.objects.create(
    client=client_profile,
    interaction_type='note',
    subject='VIP клиент',
    body='Предпочитает номера на верхних этажах',
)

# Новый код
AdminComment.objects.create(
    client=client_profile,
    author=request.user,
    body='VIP клиент. Предпочитает номера на верхних этажах',
    is_pinned=True,
)
```

---

### 5. Замена Message → ContactMessage

#### Зачем?
- `crm.Message` дублирует `notifications.ContactMessage`
- `ContactMessage` имеет больше функций (треды, статусы)

#### Как заменить?

**Вместо crm.Message используйте:**

```python
# Старый код (deprecated)
from apps.crm.models import Message
Message.objects.create(
    sender=guest,
    recipient=staff,
    subject='Вопрос о бронировании',
    body='Можно ли заселиться раньше?',
)

# Новый код
from apps.notifications.models import ContactMessage
ContactMessage.objects.create(
    sender_user=guest,
    sender_name=guest.get_full_name(),
    sender_email=guest.email,
    subject='Вопрос о бронировании',
    message='Можно ли заселиться раньше?',
    assigned_to=staff,
)
```

---

## 🗺️ Полный план миграции

### Месяц 1: Подготовка
- [x] Пометить deprecated модели
- [x] Создать скрипты миграции
- [x] Обновить документацию
- [ ] Проверить текущее использование
- [ ] Создать резервную копию БД

### Месяц 2-3: Миграция данных
- [ ] Мигрировать отзывы
- [ ] Экспортировать задачи
- [ ] Импортировать задачи в Trello/Asana
- [ ] Обновить код (заменить deprecated модели)
- [ ] Протестировать изменения

### Месяц 4-6: Проверка
- [ ] Убедиться, что новые данные не пишутся в deprecated таблицы
- [ ] Проверить, что всё работает корректно
- [ ] Собрать обратную связь от команды

### Месяц 7-12: Очистка
- [ ] Удалить данные из deprecated таблиц
- [ ] Удалить deprecated модели из кода
- [ ] Создать миграцию Django для удаления таблиц
- [ ] Обновить документацию

---

## ⚠️ Важные предупреждения

### ❌ НЕ ДЕЛАЙТЕ:
1. **Не удаляйте модели сразу** - сначала мигрируйте данные
2. **Не пропускайте резервное копирование** - это критично
3. **Не мигрируйте в production без тестирования** - сначала на dev/staging
4. **Не удаляйте данные без проверки** - убедитесь, что миграция прошла успешно

### ✅ ОБЯЗАТЕЛЬНО:
1. **Делайте резервные копии** перед каждым шагом
2. **Используйте --dry-run** для тестирования
3. **Проверяйте результаты** после каждой миграции
4. **Тестируйте на копии БД** перед production
5. **Документируйте изменения** для команды

---

## 🆘 Откат изменений

Если что-то пошло не так:

### Откат миграции отзывов
```python
# Удалить мигрированные отзывы
from apps.reviews.models import Review
Review.objects.filter(created_at__gte='2024-01-01').delete()

# Восстановить из резервной копии
# PostgreSQL
psql zori_vaha < backup_20240101.sql

# SQLite
cp db.sqlite3.backup_20240101 db.sqlite3
```

### Откат изменений кода
```bash
# Если используете git
git revert <commit_hash>

# Или восстановить из резервной копии
git checkout HEAD~1 -- apps/
```

---

## 📊 Мониторинг прогресса

### Проверка статуса миграции

```bash
# Общая проверка
python manage.py check_deprecated_usage

# Детальная проверка каждой модели
python manage.py shell
>>> from apps.hotel.models import RoomReview
>>> from apps.analytics.models import PageView, BookingFunnel
>>> from apps.crm.models import Interaction, Task, Message
>>> 
>>> print(f"RoomReview: {RoomReview.objects.count()}")
>>> print(f"PageView: {PageView.objects.count()}")
>>> print(f"BookingFunnel: {BookingFunnel.objects.count()}")
>>> print(f"Interaction: {Interaction.objects.count()}")
>>> print(f"Task: {Task.objects.count()}")
>>> print(f"Message: {Message.objects.count()}")
```

### Целевые показатели

| Модель | Сейчас | Через 3 мес | Через 6 мес | Через 12 мес |
|--------|--------|-------------|-------------|--------------|
| RoomReview | ? | 0 | 0 | Удалена |
| PageView | ? | 0 | 0 | Удалена |
| BookingFunnel | ? | 0 | 0 | Удалена |
| Interaction | ? | 0 | 0 | Удалена |
| Task | ? | 0 | 0 | Удалена |
| Message | ? | 0 | 0 | Удалена |

---

## 📚 Дополнительные ресурсы

- **План оптимизации:** `docs/db_optimization_plan.md`
- **План deprecation:** `docs/DEPRECATION_PLAN.md`
- **Скрипты миграции:** `scripts/migrations/README.md`
- **Management commands:** `apps/core/management/commands/`

---

## 🎯 Чеклист для начала

Перед началом миграции убедитесь:

- [ ] Прочитали всю документацию
- [ ] Создали резервную копию БД
- [ ] Протестировали на dev/staging
- [ ] Уведомили команду о планируемых изменениях
- [ ] Запланировали время для миграции (нерабочие часы)
- [ ] Подготовили план отката на случай проблем
- [ ] Проверили, что все зависимости установлены

---

## 💬 Вопросы?

Если возникли вопросы:
1. Проверьте документацию в `docs/`
2. Запустите `python manage.py check_deprecated_usage`
3. Используйте `--dry-run` для тестирования
4. Создайте issue в репозитории

Удачи с миграцией! 🚀
