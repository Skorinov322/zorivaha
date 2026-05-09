# Инструкция по настройке системы отзывов

## ✅ Что уже сделано

Система отзывов полностью создана и готова к использованию:

1. **Модели** (`apps/reviews/models.py`):
   - `Review` — отзыв гостя с оценками и текстом
   - `ReviewResponse` — ответ администрации
   - `ReviewModeration` — история модерации (аудит-лог)

2. **Админ-панель** (`apps/reviews/admin.py`):
   - Управление отзывами с массовыми действиями
   - Inline для ответов администрации
   - История модерации

3. **Views и формы**:
   - Публичные страницы (список, детальная)
   - Создание отзыва гостем
   - Модерация для персонала
   - Ответы администрации

4. **Шаблоны**:
   - `review_list.html` — список отзывов
   - `review_detail.html` — детальная страница
   - `review_create.html` — форма создания
   - `moderation_list.html` — список для модерации
   - `moderate_review.html` — форма модерации
   - `respond_to_review.html` — форма ответа
   - `my_reviews.html` — личный кабинет гостя

5. **Интеграция**:
   - Добавлено в `INSTALLED_APPS`
   - URL-маршруты подключены
   - Кнопка "Оставить отзыв" в личном кабинете

## 🚀 Шаги для запуска

### 1. Применить миграции

```bash
python manage.py makemigrations reviews
python manage.py migrate
```

### 2. Проверить работу

#### Для гостей:
1. Завершите бронирование (статус `checked_out`)
2. Откройте страницу бронирования в личном кабинете
3. Нажмите "Оставить отзыв"
4. Заполните форму и отправьте

#### Для персонала:
1. Войдите как пользователь с ролью `receptionist` или выше
2. Перейдите на `/reviews/moderation/`
3. Одобрите или отклоните отзывы

#### Для администраторов:
1. Войдите как `admin` или `manager`
2. Перейдите на `/reviews/moderation/`
3. Одобрите отзыв
4. Нажмите "Ответить" и напишите ответ

#### Публичные страницы:
- `/reviews/` — все опубликованные отзывы
- `/reviews/<uuid>/` — детальная страница отзыва

### 3. Настройка админ-панели

Система уже зарегистрирована в админке Django:
- `/admin/reviews/review/` — управление отзывами
- `/admin/reviews/reviewresponse/` — ответы
- `/admin/reviews/reviewmoderation/` — история модерации

## 📋 Права доступа

### Гость (role = "user"):
- ✅ Создать отзыв на свое завершенное бронирование
- ✅ Просмотреть свои отзывы
- ✅ Просмотреть публичные отзывы

### Ресепшн (role = "receptionist"):
- ✅ Все права гостя
- ✅ Модерация отзывов (одобрение/отклонение)
- ✅ Просмотр всех отзывов

### Менеджер (role = "manager"):
- ✅ Все права ресепшена
- ✅ Ответ на отзывы от имени администрации

### Администратор (role = "admin"):
- ✅ Все права менеджера
- ✅ Отметка избранных отзывов
- ✅ Полный доступ через админ-панель

## 🔧 Дополнительные настройки

### Добавить ссылку в навигацию персонала

Найдите шаблон навигации для персонала и добавьте:

```html
<a href="{% url 'reviews:moderation_list' %}">
    Модерация отзывов
    {% if pending_reviews_count %}
        <span class="badge">{{ pending_reviews_count }}</span>
    {% endif %}
</a>
```

### Добавить виджет на главную страницу

В шаблоне главной страницы:

```django
{% load static %}

<!-- Избранные отзывы -->
<section class="reviews-section">
    <h2>Отзывы наших гостей</h2>
    
    {% for review in featured_reviews %}
    <div class="review-card">
        <h3>{{ review.title }}</h3>
        <div class="rating">
            {% for i in "12345" %}
                {% if forloop.counter <= review.overall_rating %}⭐{% endif %}
            {% endfor %}
        </div>
        <p>{{ review.text|truncatewords:30 }}</p>
        <small>{{ review.guest_name }} • {{ review.created_at|date:"d.m.Y" }}</small>
    </div>
    {% endfor %}
    
    <a href="{% url 'reviews:list' %}" class="btn">Все отзывы</a>
</section>
```

В view главной страницы:

```python
from apps.reviews.selectors import get_featured_reviews

def home_view(request):
    context = {
        'featured_reviews': get_featured_reviews(limit=3),
    }
    return render(request, 'home.html', context)
```

### Добавить счетчик в контекст-процессор

В `apps/core/context_processors.py`:

```python
from apps.reviews.models import Review, ReviewStatus

def reviews_context(request):
    """Добавляет счетчик отзывов на модерации"""
    pending_count = 0
    if request.user.is_authenticated and request.user.has_role('receptionist'):
        pending_count = Review.objects.filter(
            status=ReviewStatus.PENDING
        ).count()
    
    return {
        'pending_reviews_count': pending_count,
    }
```

Добавьте в `settings/base.py`:

```python
TEMPLATES = [
    {
        ...
        "OPTIONS": {
            "context_processors": [
                ...
                "apps.core.context_processors.reviews_context",
            ],
        },
    },
]
```

## 📊 Использование в коде

### Получить статистику:

```python
from apps.reviews.selectors import get_review_statistics

stats = get_review_statistics()
# {
#     'total_count': 42,
#     'average_overall': 4.5,
#     'average_cleanliness': 4.7,
#     'average_comfort': 4.6,
#     'average_staff': 4.8,
#     'average_value': 4.3,
#     'average_location': 4.9,
#     'rating_distribution': {1: 0, 2: 1, 3: 5, 4: 15, 5: 21}
# }
```

### Проверить, может ли гость оставить отзыв:

```python
from apps.reviews.selectors import can_user_review_booking

can_review, message = can_user_review_booking(user, booking)
if can_review:
    # Показать форму
else:
    # Показать сообщение: message
```

### Получить опубликованные отзывы:

```python
from apps.reviews.selectors import get_published_reviews

reviews = get_published_reviews()
```

## 🎨 Стилизация

Все шаблоны используют Bootstrap 5 и совместимы с текущим дизайном сайта.

Для кастомизации отредактируйте шаблоны в `templates/reviews/`.

## 📝 Примечания

1. **Один отзыв на бронирование** — гость может оставить только один отзыв на каждое бронирование
2. **Модерация обязательна** — все отзывы проходят модерацию перед публикацией
3. **История сохраняется** — все действия модераторов логируются в `ReviewModeration`
4. **IP и User-Agent** — сохраняются для защиты от спама

## 🐛 Возможные проблемы

### Ошибка при создании отзыва

Проверьте:
- Бронирование завершено (`status = 'checked_out'`)
- Пользователь — гость этого бронирования
- Отзыв еще не создан

### Не отображаются отзывы

Проверьте:
- Отзывы одобрены (`status = 'approved'`)
- Есть `published_at` дата

### Нет доступа к модерации

Проверьте роль пользователя:
```python
user.has_role('receptionist')  # True для ресепшена и выше
```

## 📚 Документация

Полная документация в `apps/reviews/README.md`

## ✨ Готово!

Система отзывов полностью настроена и готова к использованию.
