# Зори Ваха

Django-проект для сайта и внутренней системы управления гостиницей «Зори Ваха».

Проект включает публичный сайт, бронирование номеров, личный кабинет гостя, панель управления персонала, CRM, отчёты, отзывы с модерацией и редактируемый контент сайта.

## Возможности

- Публичный сайт гостиницы: главная, каталог категорий номеров, галерея, «О нас», контакты, FAQ и правовые страницы.
- Поиск и бронирование номеров с проверкой доступности, групповые бронирования и автоматическое распределение гостей по комнатам.
- Расчёт стоимости с учётом количества взрослых и детей со спальным местом, сезонных/выходных цен и раннего заезда с доплатой 50% от стоимости суток.
- Личный кабинет гостя: профиль, email, история проживания, бронирования, организации и обращения.
- Роли доступа: гость, ресепшн, менеджер, администратор и супер-администратор.
- Управление пользователями: просмотр, активация/деактивация, назначение ролей и смена пароля пользователю администратором.
- Дашборд персонала: календарь загрузки, статистика, метрики, бронирования, номера, пользователи, CRM и управление контентом сайта.
- Управление категориями номеров, физическими номерами, удобствами, изображениями и статусами номеров.
- Редактирование контента: галерея сайта, FAQ, правовые страницы и страница «О нас».
- Система отзывов: один отзыв на аккаунт, общие отзывы без обязательной брони, модерация в дашборде и горизонтальная лента отзывов на главной.
- CRM: клиенты, организации, задачи, комментарии и взаимодействия.
- Отчёты: выручка по месяцам, загрузка номеров, PDF и Excel-экспорт.
- Уведомления и обращения клиентов.
- Production Docker-конфигурация с PostgreSQL, Redis, Gunicorn и Celery.

## Стек

- Python 3.12
- Django 5.0.4
- Django templates, Bootstrap 5, Bootstrap Icons
- SQLite для локальной разработки по умолчанию
- PostgreSQL для production через `docker-compose.prod.yml`
- Redis
- Celery и Celery Beat
- Gunicorn
- WhiteNoise
- ReportLab и OpenPyXL для отчётов
- Chart.js для графиков
- Docker и Docker Compose

## Быстрый запуск через Docker

### Требования

- Docker Desktop с Docker Compose
- Git

### 1. Клонировать репозиторий

```bash
git clone https://github.com/Skorinov322/zorivaha.git
cd zorivaha
```

### 2. Создать `.env`

```bash
cp .env.example .env
```

Для локальной разработки файл уже содержит безопасные dev-настройки. По умолчанию Django использует SQLite (`db.sqlite3`), а письма выводятся в консоль.

### 3. Запустить контейнеры

```bash
docker compose up -d --build
```

Локальный compose запускает:

- `web` — Django development server на `http://localhost:8000`
- `redis` — Redis для фоновых задач
- `celery_worker` — Celery worker
- `celery_beat` — Celery Beat
- `db` — MySQL-контейнер, оставлен для совместимости старого dev-окружения, но текущие dev-настройки используют SQLite

### 4. Подготовить базу

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createcachetable
docker compose exec web python manage.py createsuperuser
```

Если нужны начальные данные:

```bash
docker compose exec web python manage.py loaddata fixtures/initial_data.json
```

### 5. Открыть проект

- Сайт: `http://localhost:8000/`
- Личный кабинет: `http://localhost:8000/cabinet/`
- Бронирование: `http://localhost:8000/bookings/`
- Дашборд: `http://localhost:8000/dashboard/`
- CRM: `http://localhost:8000/crm/`
- Отчёты: `http://localhost:8000/reports/`
- Django Admin: `http://localhost:8000/admin/`
- Role-based admin: `http://localhost:8000/staff-admin/`
- Health check: `http://localhost:8000/health/`

## Production запуск с PostgreSQL

Для сервера используйте `docker-compose.prod.yml` и `.env.prod.example`.

### 1. Создать production `.env`

```bash
cp .env.prod.example .env
nano .env
```

Обязательно замените:

- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- пароль внутри `DATABASE_URL`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- email-настройки, если нужна отправка писем

Для первого запуска только по IP без HTTPS:

```env
ALLOWED_HOSTS=YOUR_SERVER_IP
CSRF_TRUSTED_ORIGINS=http://YOUR_SERVER_IP
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
```

После подключения домена и HTTPS:

```env
ALLOWED_HOSTS=your-domain.ru,www.your-domain.ru
CSRF_TRUSTED_ORIGINS=https://your-domain.ru,https://www.your-domain.ru
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### 2. Запустить production compose

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 3. Подготовить БД и статику

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml exec web python manage.py createcachetable
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### 4. Проверить работу

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f web
```

Открыть:

```text
http://YOUR_SERVER_IP:8000
```

Подробная инструкция для Yandex Cloud лежит в `DEPLOY_YANDEX_CLOUD.md`.

## Полезные команды

```bash
# Статус контейнеров
docker compose ps

# Логи Django
docker compose logs -f web

# Логи Celery
docker compose logs -f celery_worker

# Django shell
docker compose exec web python manage.py shell

# Применить миграции
docker compose exec web python manage.py migrate

# Собрать статику
docker compose exec web python manage.py collectstatic --noinput

# Создать суперпользователя
docker compose exec web python manage.py createsuperuser

# Перезапустить web
docker compose restart web

# Остановить контейнеры
docker compose down

# Остановить контейнеры и удалить volumes
docker compose down -v
```

Production-вариант тех же команд:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml restart web
docker compose -f docker-compose.prod.yml down
```

Резервная копия PostgreSQL:

```bash
docker compose -f docker-compose.prod.yml exec db pg_dump -U zorivaha_user zorivaha > backup.sql
```

## Основные разделы проекта

```text
zorivaha/
├── apps/
│   ├── accounts/       # пользователи, роли, кабинет, управление пользователями
│   ├── analytics/      # аналитика посещений
│   ├── bookings/       # бронирования, цены, заселение/выезд
│   ├── content/        # FAQ, правовые страницы, «О нас», галерея
│   ├── core/           # общие модели, права, middleware, healthcheck
│   ├── crm/            # клиенты, организации, задачи
│   ├── dashboard/      # административный дашборд
│   ├── hotel/          # категории номеров, номера, публичные страницы
│   ├── notifications/  # обращения и email-уведомления
│   ├── reports/        # отчёты, PDF/Excel
│   ├── reviews/        # отзывы и модерация
│   └── setup/          # первичная настройка
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   └── celery.py
├── deploy/             # конфиги и скрипты деплоя
├── docs/               # дополнительные документы
├── fixtures/           # начальные данные
├── frontend/           # статические HTML/CSS/JS материалы
├── requirements/       # зависимости Python
├── static/             # исходная статика
├── templates/          # Django templates
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
└── manage.py
```

## Роли

- `USER` — гость, бронирования, профиль, обращения и отзыв.
- `RECEPTIONIST` — работа с бронями, заселение/выезд, базовая модерация.
- `MANAGER` — CRM, отчёты, бронирования и операционные разделы.
- `ADMIN` — управление сайтом, номерами, пользователями и контентом.
- `SUPER_ADMIN` — полный доступ, включая назначение верхних ролей.

## Важные URL

- `/` — главная страница
- `/rooms/` — каталог категорий номеров
- `/about/` — страница «О нас»
- `/contacts/` — контакты
- `/faq/` — FAQ
- `/bookings/` — создание бронирования
- `/cabinet/` — личный кабинет
- `/cabinet/users/` — управление пользователями
- `/dashboard/` — дашборд
- `/dashboard/about-content/` — редактирование страницы «О нас»
- `/dashboard/site-content/` — правовые страницы
- `/dashboard/gallery/` — галерея
- `/dashboard/reviews/` — модерация отзывов
- `/reports/` — отчёты
- `/crm/` — CRM
- `/admin/` — стандартный Django Admin
- `/staff-admin/` — роль-зависимая админка

## Переменные окружения

Для локальной разработки используется `.env.example`.

Ключевые переменные:

- `DJANGO_SETTINGS_MODULE=config.settings.dev`
- `SECRET_KEY`
- `DEBUG=True`
- `ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `EMAIL_BACKEND_DEV=console`

Для production используется `.env.prod.example`.

Ключевые production-переменные:

- `DJANGO_SETTINGS_MODULE=config.settings.prod`
- `DEBUG=False`
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `SECURE_SSL_REDIRECT`
- `SESSION_COOKIE_SECURE`
- `CSRF_COOKIE_SECURE`
- SMTP-переменные для email

## Разработка без Docker

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements/dev.txt
copy .env.example .env
python manage.py migrate
python manage.py createcachetable
python manage.py createsuperuser
python manage.py runserver
```

Для Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env
python manage.py migrate
python manage.py createcachetable
python manage.py createsuperuser
python manage.py runserver
```

## Troubleshooting

### Сайт не открывается по `0.0.0.0:8000`

В браузере используйте:

```text
http://localhost:8000/
```

или:

```text
http://127.0.0.1:8000/
```

### Не применены миграции

```bash
docker compose exec web python manage.py migrate
```

### Нет таблицы Django cache

```bash
docker compose exec web python manage.py createcachetable
```

### Порт 8000 занят

Измените порт в `docker-compose.yml`:

```yaml
web:
  ports:
    - "8001:8000"
```

Затем откройте `http://localhost:8001/`.

### Нужно полностью пересоздать локальное окружение

```bash
docker compose down -v
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createcachetable
docker compose exec web python manage.py createsuperuser
```

## Git

Основная ветка проекта: `main`.

```bash
git status
git add .
git commit -m "new"
git push origin main
```

Перед коммитом не добавляйте реальные `.env`, пароли, токены, дампы production-БД и приватные ключи.
