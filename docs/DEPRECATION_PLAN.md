# План постепенной оптимизации БД (Мягкий вариант)

## 📅 График внедрения

### Фаза 1: Пометка deprecated (сейчас)
- Пометить устаревшие модели
- Добавить предупреждения в код
- Обновить документацию

### Фаза 2: Переход на новые модели (1-3 месяца)
- Использовать новые модели в новом коде
- Старые данные остаются доступными
- Двойная запись (опционально)

### Фаза 3: Миграция данных (через 3-6 месяцев)
- Перенести старые данные в новые таблицы
- Проверить целостность

### Фаза 4: Удаление (через 6-12 месяцев)
- Удалить deprecated модели
- Очистить код
- Финальная миграция

---

## 🗑️ Модели для удаления

### DEPRECATED (будут удалены в v2.0)

#### analytics.PageView
- **Причина:** Избыточно, есть Google Analytics
- **Альтернатива:** Google Analytics / Yandex.Metrica
- **Дата удаления:** v2.0 (через 6 месяцев)
- **Действие:** Перестать записывать новые данные

#### analytics.BookingFunnel
- **Причина:** Избыточно для малого отеля
- **Альтернатива:** Google Analytics Goals
- **Дата удаления:** v2.0 (через 6 месяцев)
- **Действие:** Перестать записывать новые данные

#### analytics.RevenueSnapshot
- **Причина:** Дублирует DailyMetrics
- **Альтернатива:** Считать из DailyMetrics
- **Дата удаления:** v2.0 (через 6 месяцев)
- **Действие:** Использовать DailyMetrics.aggregate()

#### crm.Interaction
- **Причина:** Дублирует BookingHistory + AdminComment
- **Альтернатива:** bookings.BookingHistory + crm.AdminComment
- **Дата удаления:** v2.0 (через 6 месяцев)
- **Действие:** Записывать в BookingHistory

#### crm.Task
- **Причина:** Избыточно, есть внешние таск-менеджеры
- **Альтернатива:** Trello, Asana, Notion
- **Дата удаления:** v2.0 (через 6 месяцев)
- **Действие:** Экспортировать в внешний сервис

#### crm.Message
- **Причина:** Дублирует ContactMessage
- **Альтернатива:** notifications.ContactMessage
- **Дата удаления:** v2.0 (через 6 месяцев)
- **Действие:** Использовать ContactMessage

#### hotel.RoomReview
- **Причина:** Дублирует reviews.Review
- **Альтернатива:** reviews.Review (более полная)
- **Дата удаления:** v2.0 (через 6 месяцев)
- **Действие:** Мигрировать данные в reviews.Review

---

## ✅ Модели, которые остаются

### accounts
- ✅ User

### hotel
- ✅ Amenity
- ✅ RoomCategory
- ✅ RoomImage
- ✅ Room
- ✅ SeasonalPrice
- ❌ RoomReview → reviews.Review

### bookings
- ✅ Booking
- ✅ BookingHistory
- ✅ Payment

### crm
- ✅ Organization
- ✅ ClientProfile
- ✅ AdminComment
- ❌ Interaction → BookingHistory
- ❌ Task → внешний сервис
- ❌ Message → ContactMessage

### reviews
- ✅ Review
- ✅ ReviewResponse
- ✅ ReviewModeration

### notifications
- ✅ EmailLog
- ✅ NotificationTemplate
- ✅ PushNotification
- ✅ ContactMessage
- ✅ ContactReply

### analytics
- ✅ DailyMetrics
- ❌ PageView → Google Analytics
- ❌ BookingFunnel → Google Analytics
- ❌ RevenueSnapshot → DailyMetrics

---

## 🔄 Миграционная стратегия

### Для RoomReview → Review
```python
# Скрипт миграции (запустить вручную)
python manage.py migrate_room_reviews
```

### Для остальных моделей
- Просто перестать использовать
- Данные останутся в БД (для истории)
- Удалить через 6-12 месяцев

---

## 📝 Чеклист для разработчиков

### При работе с отзывами:
- ❌ НЕ использовать `hotel.RoomReview`
- ✅ Использовать `reviews.Review`

### При работе с аналитикой:
- ❌ НЕ записывать `PageView`, `BookingFunnel`
- ✅ Использовать Google Analytics
- ✅ Использовать `DailyMetrics` для отчетов

### При работе с CRM:
- ❌ НЕ создавать `Interaction`, `Task`, `Message`
- ✅ Использовать `BookingHistory` для истории
- ✅ Использовать `AdminComment` для заметок
- ✅ Использовать `ContactMessage` для переписки

---

## 🚨 Предупреждения в коде

Все deprecated модели помечены:
```python
class DeprecatedModel(models.Model):
    """
    ⚠️ DEPRECATED: This model will be removed in v2.0
    Use NewModel instead.
    Migration guide: docs/DEPRECATION_PLAN.md
    """
```

---

## 📊 Мониторинг использования

Проверить, используются ли deprecated модели:
```bash
# Поиск в коде
grep -r "PageView" apps/
grep -r "BookingFunnel" apps/
grep -r "Interaction" apps/
grep -r "crm.Task" apps/
grep -r "crm.Message" apps/
grep -r "RoomReview" apps/

# Проверка в БД
python manage.py check_deprecated_usage
```

---

## 🎯 Метрики успеха

- [ ] Все новые отзывы идут в `reviews.Review`
- [ ] Нет новых записей в `PageView`, `BookingFunnel`
- [ ] Нет новых записей в `Interaction`, `Task`, `Message`
- [ ] Старые данные мигрированы
- [ ] Код обновлен
- [ ] Тесты проходят

---

## 📞 Контакты

Вопросы по миграции:
- Документация: `docs/DEPRECATION_PLAN.md`
- Скрипты миграции: `scripts/migrations/`
