# Зори Ваха — Hotel Management System

---

## Запуск проекта

### Требования

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (включает Docker Compose)
- Git

---

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd DP_zorivaha
```

---

### 2. Создать файл окружения

```bash
cp .env.example .env
```

Файл `.env` уже настроен для локальной разработки — ничего менять не нужно.

---

### 3. Собрать и запустить контейнеры

```bash
docker compose up --build
```

Первый запуск занимает 3–5 минут (скачивает образы и устанавливает зависимости).

---

### 4. Применить миграции и загрузить начальные данные (в новом терминале)

```bash
# Применить миграции
docker compose exec web python manage.py migrate

# Загрузить начальные данные (категории номеров, удобства)
docker compose exec web python manage.py loaddata fixtures/initial_data.json

# Создать суперпользователя
docker compose exec web python manage.py shell -c "from apps.accounts.models import User; User.objects.create_superuser('admin@example.com', 'admin123'); print('Superuser created')"
```

Или создайте суперпользователя интерактивно:

```bash
docker compose exec web python manage.py createsuperuser
```

---

### 5. Открыть сайт

Учетные данные по умолчанию:
- Email: `admin@example.com`
- Пароль: `admin123`

| Страница | URL |
|----------|-----|
| Сайт гостиницы | http://localhost:8000/ |
| Личный кабинет | http://localhost:8000/cabinet/ |
| Панель управления | http://localhost:8000/dashboard/ |
| Django Admin | http://localhost:8000/admin/ |

---

## Что запускается

```
docker compose up
├── db             — MySQL 8        (порт 3306)
├── redis          — Redis 7        (порт 6379)
├── web            — Django dev server (порт 8000)
├── celery_worker  — Celery worker
└── celery_beat    — Celery Beat (периодические задачи)
```

---

## Полезные команды

```bash
# Посмотреть статус контейнеров
docker compose ps

# Логи Django
docker compose logs -f web

# Логи Celery
docker compose logs -f celery_worker

# Django shell
docker compose exec web python manage.py shell

# Создать дополнительного пользователя
docker compose exec web python manage.py shell -c "from apps.accounts.models import User; User.objects.create_user('user@example.com', 'password123'); print('User created')"

# Остановить всё
docker compose down

# Остановить и удалить данные БД
docker compose down -v

# Перезапустить только web контейнер
docker compose restart web
```

---

## Повторный запуск (после остановки)

```bash
# Запустить в фоновом режиме
docker compose up -d

# Или с выводом логов
docker compose up
```

Миграции применять повторно не нужно — данные сохраняются в Docker volume.

---

## Структура проекта

```
DP_zorivaha/
├── apps/                    # Django приложения
│   ├── accounts/           # Пользователи и аутентификация
│   ├── hotel/              # Номера, категории, удобства
│   ├── bookings/           # Бронирования
│   ├── crm/                # CRM профили гостей
│   ├── analytics/          # Аналитика и статистика
│   ├── notifications/      # Email уведомления
│   ├── reports/            # Отчеты
│   ├── dashboard/          # Панель управления
│   └── setup/              # Первоначальная настройка
├── config/                 # Настройки Django
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   └── celery.py
├── static/                 # Статические файлы
├── media/                  # Загруженные файлы
├── fixtures/               # Начальные данные
├── deploy/                 # Скрипты деплоя
├── requirements/           # Python зависимости
├── docker-compose.yml
├── Dockerfile
└── manage.py
```

---

## Стек

- **Backend**: Django 5.0, Python 3.12
- **БД**: MySQL 8
- **Кэш / Брокер**: Redis 7
- **Очереди**: Celery 5 + Celery Beat
- **Frontend**: Bootstrap 5, Chart.js
- **Контейнеризация**: Docker + Docker Compose

---

## Роли пользователей

Система поддерживает следующие роли:

- **USER** — обычный гость, может бронировать номера
- **RECEPTIONIST** — стойка регистрации, заселение/выселение
- **MANAGER** — менеджер, CRM + бронирования + отчёты
- **ADMIN** — администратор гостиницы, полный доступ кроме управления ролями
- **SUPER_ADMIN** — полный доступ, может управлять ролями пользователей

---

## Troubleshooting

### Контейнеры не запускаются

```bash
# Проверить логи
docker compose logs

# Пересобрать образы
docker compose build --no-cache
docker compose up
```

### Ошибка "Table doesn't exist"

```bash
# Применить миграции
docker compose exec web python manage.py migrate
```

### Порт 8000 уже занят

Измените порт в `docker-compose.yml`:

```yaml
web:
  ports:
    - "8001:8000"  # Используйте 8001 вместо 8000
```

### Сбросить базу данных

```bash
# Остановить контейнеры и удалить volumes
docker compose down -v

# Запустить заново
docker compose up --build

# Применить миграции и загрузить данные
docker compose exec web python manage.py migrate
docker compose exec web python manage.py loaddata fixtures/initial_data.json
```
