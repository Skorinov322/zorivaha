# Архитектура системы FAQ

## Диаграмма компонентов

```
┌─────────────────────────────────────────────────────────────────┐
│                         ПОЛЬЗОВАТЕЛИ                             │
└─────────────────────────────────────────────────────────────────┘
                    │                           │
                    │                           │
         ┌──────────▼──────────┐    ┌──────────▼──────────┐
         │   Гости сайта       │    │  Администраторы     │
         │   (публичный доступ)│    │  (Manager+)         │
         └──────────┬──────────┘    └──────────┬──────────┘
                    │                           │
                    │                           │
         ┌──────────▼──────────┐    ┌──────────▼──────────┐
         │   /faq/             │    │  /staff-admin/      │
         │   (публичная        │    │  content/faq/       │
         │    страница)        │    │  (админ-панель)     │
         └──────────┬──────────┘    └──────────┬──────────┘
                    │                           │
                    │                           │
         ┌──────────▼──────────┐    ┌──────────▼──────────┐
         │  FAQListView        │    │  FAQAdmin           │
         │  (views.py)         │    │  (admin.py)         │
         └──────────┬──────────┘    └──────────┬──────────┘
                    │                           │
                    └───────────┬───────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   FAQ Model           │
                    │   (models.py)         │
                    │                       │
                    │  • question           │
                    │  • answer             │
                    │  • category           │
                    │  • is_active          │
                    │  • sort_order         │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   База данных         │
                    │   (content_faq)       │
                    └───────────────────────┘
```

## Поток данных

### 1. Создание FAQ (Администратор)

```
Администратор
    │
    ├─> Вход в админ-панель (/staff-admin/)
    │
    ├─> Проверка прав (RoleRestrictedMixin)
    │   └─> min_add_role = "manager"
    │
    ├─> Форма создания FAQ
    │   ├─> Вопрос (CharField)
    │   ├─> Ответ (TextField)
    │   ├─> Категория (ChoiceField)
    │   ├─> Активен (BooleanField)
    │   └─> Порядок (IntegerField)
    │
    ├─> Валидация данных
    │
    ├─> Сохранение в БД
    │   └─> FAQ.objects.create(...)
    │
    └─> Редирект на список FAQ
```

### 2. Просмотр FAQ (Гость)

```
Гость
    │
    ├─> Переход на /faq/
    │
    ├─> FAQListView.as_view()
    │   │
    │   ├─> get_queryset()
    │   │   └─> FAQ.objects.filter(is_active=True)
    │   │       .order_by("category", "sort_order")
    │   │
    │   └─> get_context_data()
    │       └─> Группировка по категориям
    │
    ├─> Рендеринг шаблона (faq.html)
    │   │
    │   ├─> Hero секция
    │   │
    │   ├─> Для каждой категории:
    │   │   ├─> Заголовок с иконкой
    │   │   └─> Аккордеон с вопросами
    │   │
    │   └─> CTA блок (Контакты)
    │
    └─> Отображение страницы
```

## Структура базы данных

### Таблица: content_faq

```sql
CREATE TABLE content_faq (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question VARCHAR(500) NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE INDEX idx_faq_category ON content_faq(category);
CREATE INDEX idx_faq_active ON content_faq(is_active);
CREATE INDEX idx_faq_sort ON content_faq(category, sort_order);
```

### Пример записи

```json
{
    "id": 1,
    "question": "Во сколько заезд и выезд?",
    "answer": "Стандартное время заезда и выезда:\n\n• Заезд: с 14:00\n• Выезд: до 12:00",
    "category": "checkin",
    "is_active": true,
    "sort_order": 1,
    "created_at": "2026-05-10T00:00:00Z",
    "updated_at": "2026-05-10T00:00:00Z"
}
```

## Права доступа

### Матрица прав

| Роль          | Просмотр | Добавление | Редактирование | Удаление |
|---------------|----------|------------|----------------|----------|
| User          | ❌       | ❌         | ❌             | ❌       |
| Receptionist  | ❌       | ❌         | ❌             | ❌       |
| Manager       | ✅       | ✅         | ✅             | ❌       |
| Admin         | ✅       | ✅         | ✅             | ✅       |
| Super Admin   | ✅       | ✅         | ✅             | ✅       |

### Реализация в коде

```python
@admin.register(FAQ, site=role_admin_site)
class FAQAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "manager"
    min_change_role = "manager"
    min_delete_role = "admin"
    min_add_role    = "manager"
```

## URL-маршруты

### Публичные

```python
# apps/content/urls.py
urlpatterns = [
    path("faq/", views.FAQListView.as_view(), name="faq"),
]
```

### Админ-панель

```python
# Автоматически генерируется Django Admin
/staff-admin/content/faq/           # Список
/staff-admin/content/faq/add/       # Добавление
/staff-admin/content/faq/<id>/      # Просмотр
/staff-admin/content/faq/<id>/change/  # Редактирование
/staff-admin/content/faq/<id>/delete/  # Удаление
```

## Шаблоны

### Иерархия наследования

```
base.html
    │
    └─> content/faq.html
            │
            ├─> Hero секция
            ├─> FAQ по категориям
            │   └─> Аккордеоны
            └─> CTA блок
```

### Блоки шаблона

```django
{% extends "base.html" %}

{% block title %}Часто задаваемые вопросы{% endblock %}
{% block meta_description %}...{% endblock %}
{% block extra_css %}...{% endblock %}
{% block content %}...{% endblock %}
{% block extra_js %}...{% endblock %}
```

## Категории FAQ

### Enum определение

```python
class FAQCategory(models.TextChoices):
    BOOKING  = "booking",  "Бронирование"
    CHECKIN  = "checkin",  "Заезд и выезд"
    SERVICES = "services", "Услуги"
    PAYMENT  = "payment",  "Оплата"
    GENERAL  = "general",  "Общее"
```

### Иконки Bootstrap Icons

| Категория       | Иконка              | Код                  |
|-----------------|---------------------|----------------------|
| Бронирование    | 📅                  | bi-calendar-check    |
| Заезд и выезд   | 🚪                  | bi-door-open         |
| Услуги          | ⭐                  | bi-star              |
| Оплата          | 💳                  | bi-credit-card       |
| Общее           | ℹ️                  | bi-info-circle       |

## Массовые операции

### Доступные действия

```python
actions = [
    "activate_faqs",      # Активировать
    "deactivate_faqs",    # Деактивировать
    "delete_selected",    # Удалить
]
```

### Реализация

```python
@admin.action(description="Активировать выбранные FAQ")
def activate_faqs(self, request, queryset):
    updated = queryset.update(is_active=True)
    self.message_user(request, f"Активировано FAQ: {updated}")
```

## Интеграция с навигацией

### Главное меню (_navbar.html)

```html
<li>
    <a href="{% url 'content:faq' %}" class="nav-link-item">FAQ</a>
</li>
```

### Футер (_footer.html)

```html
<li>
    <a href="{% url 'content:faq' %}">FAQ</a>
</li>
```

## Management команды

### create_sample_faq

```bash
python manage.py create_sample_faq
```

**Что делает:**
1. Создает 15 примеров FAQ
2. Покрывает все 5 категорий
3. Использует `update_or_create` (безопасно для повторного запуска)
4. Выводит статистику (создано/обновлено)

**Структура:**

```python
sample_faqs = [
    {
        "category": FAQ.FAQCategory.BOOKING,
        "question": "...",
        "answer": "...",
        "sort_order": 1,
    },
    # ... еще 14 вопросов
]
```

## Производительность

### Оптимизации

1. **Индексы БД:**
   - `category` — для фильтрации
   - `is_active` — для публичной страницы
   - `(category, sort_order)` — для сортировки

2. **Кэширование (будущее):**
   ```python
   from django.views.decorators.cache import cache_page
   
   @cache_page(60 * 15)  # 15 минут
   class FAQListView(ListView):
       ...
   ```

3. **Пагинация (если много FAQ):**
   ```python
   class FAQListView(ListView):
       paginate_by = 50
   ```

## Безопасность

### XSS защита

- Все пользовательские данные экранируются Django автоматически
- `{{ faq.answer|linebreaks }}` — безопасное преобразование переносов строк

### CSRF защита

- Все формы в админке защищены `{% csrf_token %}`

### SQL Injection

- Django ORM защищает от SQL-инъекций автоматически

## Мониторинг и логирование

### Логи админ-действий

Django автоматически логирует:
- Создание FAQ
- Изменение FAQ
- Удаление FAQ

Доступно в: `/staff-admin/admin/logentry/`

### Метрики (будущее)

- Количество просмотров FAQ
- Популярные категории
- Время на странице
- Клики по вопросам

## Тестирование

### Unit тесты (пример)

```python
from django.test import TestCase
from apps.content.models import FAQ

class FAQModelTest(TestCase):
    def test_create_faq(self):
        faq = FAQ.objects.create(
            question="Тест?",
            answer="Ответ",
            category=FAQ.FAQCategory.GENERAL,
        )
        self.assertEqual(faq.question, "Тест?")
        self.assertTrue(faq.is_active)
```

### Integration тесты (пример)

```python
from django.test import Client, TestCase

class FAQViewTest(TestCase):
    def test_faq_page_loads(self):
        client = Client()
        response = client.get('/faq/')
        self.assertEqual(response.status_code, 200)
```

## Развертывание

### Миграции

```bash
python manage.py makemigrations content
python manage.py migrate content
```

### Статические файлы

```bash
python manage.py collectstatic --noinput
```

### Проверка

```bash
python manage.py check
python manage.py check --deploy
```

---

**Документ обновлен:** Май 2026  
**Версия архитектуры:** 1.0
