# Архитектура проекта «Зори Ваха»

## Принципы

1. **Fat services, thin views** — вся бизнес-логика в `services.py`, views только принимают запрос и возвращают ответ
2. **Selectors** — все сложные запросы к БД изолированы в `selectors.py`, views не пишут ORM-запросы напрямую
3. **Tasks** — всё асинхронное (email, отчёты, автоотмена) идёт через Celery
4. **Signals** — минимально, только для side-effects (создание CRM-профиля при регистрации)
5. **Forms** — только валидация и очистка данных, без логики
6. **Models** — только поля, свойства и простые методы уровня одного объекта

---

## Полная структура проекта

```
DP_zorivaha/
│
├── config/                          # Конфигурация Django
│   ├── settings/
│   │   ├── base.py                  # Общие настройки
│   │   ├── dev.py                   # Разработка (debug toolbar, console email)
│   │   └── prod.py                  # Продакшн (HTTPS, Sentry, HSTS)
│   ├── __init__.py                  # Импорт celery app
│   ├── celery.py                    # Celery application
│   ├── urls.py                      # Корневой роутинг
│   └── wsgi.py                      # WSGI entrypoint
│
├── apps/                            # Все Django-приложения
│   │
│   ├── core/                        # Ядро — базовые классы, утилиты
│   │   ├── models.py                # TimeStampedModel, UUIDModel, SoftDeleteModel
│   │   ├── mixins.py                # View-миксины (RoleRequired, StaffRequired)
│   │   ├── context_processors.py   # Глобальные переменные в шаблонах
│   │   ├── utils.py                 # Вспомогательные функции
│   │   └── apps.py
│   │
│   ├── accounts/                    # Пользователи и личный кабинет
│   │   ├── models.py                # User (email auth, roles)
│   │   ├── forms.py                 # ProfileUpdateForm, PasswordChangeForm
│   │   ├── views.py                 # CabinetDashboard, ProfileUpdate, MyBookings
│   │   ├── selectors.py             # get_user_bookings(), get_user_stats()
│   │   ├── services.py              # update_profile(), change_password()
│   │   ├── signals.py               # post_save → create ClientProfile
│   │   ├── admin.py                 # UserAdmin
│   │   ├── urls.py
│   │   └── apps.py
│   │
│   ├── hotel/                       # Каталог номеров (публичная часть)
│   │   ├── models.py                # RoomCategory, Room, Amenity, RoomImage
│   │   ├── views.py                 # Index, RoomList, RoomDetail, About, Contacts
│   │   ├── selectors.py             # get_available_categories(), get_room_by_slug()
│   │   ├── forms.py                 # AvailabilitySearchForm
│   │   ├── admin.py                 # RoomCategoryAdmin, RoomAdmin
│   │   ├── urls.py
│   │   └── apps.py
│   │
│   ├── bookings/                    # Бронирование
│   │   ├── models.py                # Booking, BookingStatusLog
│   │   ├── forms.py                 # BookingCreateForm, CancelForm
│   │   ├── views.py                 # Create, Detail, Confirm, Cancel, Success
│   │   ├── selectors.py             # get_booking_by_id(), check_availability()
│   │   ├── services.py              # create_booking(), confirm_booking(), cancel_booking()
│   │   ├── tasks.py                 # auto_cancel_expired, send_checkin_reminders
│   │   ├── admin.py                 # BookingAdmin с inline логами
│   │   ├── urls.py
│   │   └── apps.py
│   │
│   ├── crm/                         # CRM для менеджеров
│   │   ├── models.py                # ClientProfile, Interaction, Task
│   │   ├── forms.py                 # InteractionForm, TaskForm, ClientNoteForm
│   │   ├── views.py                 # Dashboard, ClientList, ClientDetail, Tasks
│   │   ├── selectors.py             # get_clients(), get_tasks_for_manager()
│   │   ├── services.py              # create_interaction(), assign_task()
│   │   ├── admin.py                 # ClientProfileAdmin, TaskAdmin
│   │   ├── urls.py
│   │   └── apps.py
│   │
│   ├── notifications/               # Email-уведомления
│   │   ├── tasks.py                 # Celery tasks: confirmation, reminder, cancel
│   │   ├── services.py              # send_email() helper
│   │   └── apps.py
│   │
│   ├── reports/                     # Отчёты: PDF, Excel, метрики
│   │   ├── views.py                 # ReportIndex, PDF, Excel, Revenue, Occupancy
│   │   ├── selectors.py             # get_revenue_data(), get_occupancy_stats()
│   │   ├── services.py              # generate_pdf(), generate_excel()
│   │   ├── urls.py
│   │   └── apps.py
│   │
│   └── dashboard/                   # Панель управления (staff)
│       ├── views.py                 # Dashboard, BookingMgmt, CheckIn, CheckOut, Rooms
│       ├── selectors.py             # get_dashboard_metrics(), get_today_arrivals()
│       ├── urls.py
│       └── apps.py
│
├── templates/                       # Все HTML-шаблоны
│   ├── base.html                    # Базовый layout
│   ├── partials/                    # Переиспользуемые фрагменты
│   │   ├── _navbar.html
│   │   ├── _footer.html
│   │   ├── _messages.html
│   │   ├── _pagination.html
│   │   └── _breadcrumbs.html
│   ├── hotel/                       # Публичный сайт
│   │   ├── index.html
│   │   ├── room_list.html
│   │   ├── room_detail.html
│   │   ├── about.html
│   │   └── contacts.html
│   ├── bookings/
│   │   ├── create.html
│   │   ├── detail.html
│   │   ├── success.html
│   │   └── cancel_confirm.html
│   ├── accounts/                    # Личный кабинет
│   │   ├── cabinet.html
│   │   ├── profile.html
│   │   └── my_bookings.html
│   ├── dashboard/                   # Staff панель
│   │   ├── base_dashboard.html      # Layout с боковым меню
│   │   ├── index.html
│   │   ├── bookings.html
│   │   └── rooms.html
│   ├── crm/
│   │   ├── dashboard.html
│   │   ├── guest_list.html
│   │   ├── guest_detail.html
│   │   └── task_list.html
│   ├── reports/
│   │   ├── index.html
│   │   └── revenue.html
│   └── notifications/
│       └── email/                   # HTML-письма
│           ├── base_email.html
│           ├── booking_confirmation.html
│           ├── booking_cancelled.html
│           └── checkin_reminder.html
│
├── static/                          # Исходные статические файлы
│   ├── css/
│   │   ├── main.css                 # Глобальные стили
│   │   ├── hotel.css                # Стили публичного сайта
│   │   └── dashboard.css            # Стили панели управления
│   ├── js/
│   │   ├── main.js                  # Глобальный JS
│   │   ├── booking.js               # Логика формы бронирования
│   │   └── dashboard.js             # Графики, таблицы дашборда
│   └── images/
│       └── logo.svg
│
├── staticfiles/                     # collectstatic output (gitignored)
├── media/                           # Загружаемые файлы (gitignored)
│   ├── avatars/
│   ├── rooms/
│   │   ├── thumbnails/
│   │   └── gallery/
│   └── reports/                     # Сгенерированные PDF/Excel
│
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
│
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── .env.example
├── .gitignore
└── README.md
```

---

## Разделение логики по слоям

### models.py — только данные
```
✅ Поля модели
✅ Meta (ordering, indexes, verbose_name)
✅ __str__, get_absolute_url
✅ Простые @property (nights, total_guests, is_active)
✅ Методы уровня одного объекта (confirm, cancel, check_in)
❌ ORM-запросы по другим моделям
❌ Отправка email
❌ Бизнес-правила, затрагивающие несколько объектов
```

### selectors.py — только чтение из БД
```python
# apps/bookings/selectors.py
def get_booking_by_id(booking_id: UUID, user=None) -> Booking: ...
def check_room_availability(category_id, check_in, check_out) -> bool: ...
def get_bookings_for_period(start, end) -> QuerySet: ...
```
```
✅ Все сложные ORM-запросы (select_related, prefetch, annotate, filter)
✅ Проверки доступности
✅ Агрегации для отчётов
❌ Изменение данных
❌ Бизнес-логика
```

### services.py — бизнес-логика и запись
```python
# apps/bookings/services.py
def create_booking(guest, category_id, check_in, check_out, **kwargs) -> Booking: ...
def confirm_booking(booking_id, actor) -> Booking: ...
def cancel_booking(booking_id, reason, actor) -> Booking: ...
```
```
✅ Транзакции (atomic)
✅ Вызов нескольких моделей
✅ Запуск Celery-задач
✅ Обновление связанных объектов (Room.status при check-in)
❌ HTTP-запросы, request/response
❌ Рендеринг шаблонов
```

### views.py — только HTTP
```python
# apps/bookings/views.py
class BookingCreateView(LoginRequiredMixin, CreateView):
    def form_valid(self, form):
        booking = create_booking(self.request.user, **form.cleaned_data)
        return redirect(booking.get_absolute_url())
```
```
✅ Получение данных из request
✅ Вызов selectors и services
✅ Рендеринг шаблона / редирект
❌ ORM-запросы напрямую
❌ Бизнес-логика
```

### tasks.py — только Celery
```
✅ Асинхронные операции (email, PDF, тяжёлые вычисления)
✅ Периодические задачи (автоотмена, напоминания)
✅ Вызов services внутри задачи
❌ Прямые HTTP-ответы
```

---

## Celery — где и что

```
config/celery.py          ← Инициализация app, autodiscover_tasks
config/__init__.py        ← from .celery import app as celery_app

apps/bookings/tasks.py    ← auto_cancel_expired_bookings (каждые 15 мин)
                             send_checkin_reminders (ежедневно 10:00)

apps/notifications/tasks.py ← send_booking_confirmation_email
                               send_booking_cancelled_email
                               send_checkin_reminder_email

apps/reports/tasks.py     ← generate_monthly_report (1-е число месяца)
```

**Celery Beat расписание** (хранится в БД через django-celery-beat):
| Задача | Расписание |
|--------|-----------|
| auto_cancel_expired_bookings | каждые 15 минут |
| send_checkin_reminders | ежедневно в 10:00 |
| generate_monthly_report | 1-е число месяца в 06:00 |

---

## Templates — структура и наследование

```
base.html                        ← DOCTYPE, head, navbar, footer, messages
    └── hotel/index.html         ← Публичные страницы
    └── dashboard/base_dashboard.html  ← Layout с sidebar для staff
            └── dashboard/index.html
            └── crm/dashboard.html
            └── reports/index.html
    └── accounts/cabinet.html    ← Личный кабинет гостя

partials/                        ← {% include %} фрагменты
    _navbar.html                 ← Адаптивная навигация
    _footer.html
    _messages.html               ← Bootstrap alerts
    _pagination.html
    _breadcrumbs.html

notifications/email/
    base_email.html              ← Базовый layout письма
    booking_confirmation.html
    booking_cancelled.html
    checkin_reminder.html
```

---

## Static / Media

```
static/          ← Исходники (в git)
    css/main.css          ← Bootstrap 5 + кастомные переменные
    css/hotel.css         ← Luxury стили публичного сайта
    css/dashboard.css     ← Стили панели управления
    js/main.js            ← Инициализация Bootstrap, общие утилиты
    js/booking.js         ← Datepicker, расчёт стоимости в реальном времени
    js/dashboard.js       ← Chart.js графики

staticfiles/     ← collectstatic output (gitignored, nginx раздаёт)

media/           ← Загружаемые файлы (gitignored)
    avatars/%Y/%m/
    rooms/thumbnails/%Y/%m/
    rooms/gallery/%Y/%m/
    reports/              ← Сгенерированные PDF/Excel (временные)
```

**В production** статику раздаёт Nginx напрямую, media — тоже Nginx или S3.

---

## Роли и доступ

| URL prefix | Кто имеет доступ | Миксин |
|------------|-----------------|--------|
| `/` | Все | — |
| `/rooms/` | Все | — |
| `/bookings/` | Авторизованные | `LoginRequiredMixin` |
| `/cabinet/` | Авторизованные | `LoginRequiredMixin` |
| `/dashboard/` | manager, admin | `RoleRequiredMixin(["manager","admin"])` |
| `/crm/` | manager, admin | `RoleRequiredMixin(["manager","admin"])` |
| `/reports/` | admin | `AdminRequiredMixin` |
| `/admin/` | superuser | Django built-in |

---

## Production-структура (Docker)

```
┌─────────────────────────────────────────────┐
│                   Nginx                      │
│  /static/ → staticfiles/  (whitenoise/nginx) │
│  /media/  → media/                           │
│  /        → gunicorn:8000                    │
└──────────────┬──────────────────────────────┘
               │
    ┌──────────▼──────────┐
    │   Gunicorn (web)     │  4 workers
    │   Django 5.0         │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐    ┌─────────────────┐
    │   PostgreSQL 16      │    │   Redis 7        │
    │   (primary DB)       │    │   db0: broker    │
    └─────────────────────┘    │   db1: results   │
                               │   db2: cache     │
                               └────────┬────────┘
                                        │
                          ┌─────────────▼──────────────┐
                          │   Celery Worker (4 concur.) │
                          │   Celery Beat (scheduler)   │
                          └────────────────────────────┘
```

---

## Naming Conventions

### Python
| Что | Конвенция | Пример |
|-----|-----------|--------|
| Модели | PascalCase | `RoomCategory`, `BookingStatusLog` |
| Поля | snake_case | `check_in`, `price_per_night` |
| Services | глагол_существительное | `create_booking`, `cancel_booking` |
| Selectors | get_/check_/list_ | `get_booking_by_id`, `check_availability` |
| Tasks | глагол_существительное | `auto_cancel_expired_bookings` |
| URL names | namespace:action | `bookings:detail`, `hotel:room_list` |
| Constants/Choices | UPPER_SNAKE | `BookingStatus.PENDING` |

### Templates
| Что | Конвенция | Пример |
|-----|-----------|--------|
| Страницы | snake_case.html | `room_detail.html` |
| Партиалы | `_` prefix | `_navbar.html`, `_pagination.html` |
| Email | суффикс типа | `booking_confirmation.html` |
| Блоки | snake_case | `{% block page_title %}` |

### CSS/JS
| Что | Конвенция | Пример |
|-----|-----------|--------|
| CSS классы | BEM или Bootstrap | `.booking-card__price` |
| JS переменные | camelCase | `checkInDate`, `totalPrice` |
| JS функции | camelCase глагол | `calculateTotal()`, `initDatepicker()` |
| Data атрибуты | kebab-case | `data-booking-id` |
