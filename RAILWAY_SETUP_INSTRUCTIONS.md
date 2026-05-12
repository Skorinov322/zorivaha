# Инструкция по развертыванию на Railway

## Шаг 1: Создайте проект на Railway

1. Зайдите на https://railway.app
2. Нажмите "New Project"
3. Выберите "Deploy from GitHub repo"
4. Выберите репозиторий `Skorinov322/zorivaha`

## Шаг 2: Добавьте PostgreSQL базу данных

1. В вашем проекте нажмите "+ New"
2. Выберите "Database" → "Add PostgreSQL"
3. Railway автоматически создаст переменную `DATABASE_URL`

## Шаг 3: Настройте переменные окружения

Перейдите в Settings → Variables вашего сервиса и добавьте:

### Обязательные переменные:

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod
DEBUG=False
```

### Сгенерируйте SECRET_KEY:

Выполните локально:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Добавьте результат как:
```bash
SECRET_KEY=ваш-сгенерированный-ключ
```

### Настройте домены:

```bash
ALLOWED_HOSTS=*.railway.app
CSRF_TRUSTED_ORIGINS=https://ваш-проект.railway.app
```

После первого деплоя замените `ваш-проект` на реальный URL, который даст Railway.

### Опциональные переменные (Email):

```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш-email@gmail.com
EMAIL_HOST_PASSWORD=ваш-app-password
DEFAULT_FROM_EMAIL=Зори Ваха <noreply@zorivaha.ru>
CONTACT_EMAIL=info@zorivaha.ru
CONTACT_PHONE=+7 (928) 000-00-00
```

## Шаг 4: Деплой

1. Railway автоматически начнет деплой после подключения репозитория
2. Следите за логами в разделе "Deployments"
3. После успешного деплоя откройте URL проекта

## Шаг 5: Создайте суперпользователя

После первого успешного деплоя:

1. Перейдите в Settings → Variables
2. Добавьте временную команду или используйте Railway CLI:

```bash
railway run python manage.py createsuperuser
```

Или используйте веб-интерфейс setup wizard по адресу: `https://ваш-проект.railway.app/setup/`

## Проверка работоспособности

- Healthcheck: `https://ваш-проект.railway.app/health/`
- Админка: `https://ваш-проект.railway.app/admin/`
- Главная: `https://ваш-проект.railway.app/`

## Troubleshooting

### Ошибка "Healthcheck failed"
- Проверьте, что PostgreSQL база данных добавлена и переменная `DATABASE_URL` существует
- Проверьте логи деплоя на наличие ошибок миграций
- Убедитесь, что `SECRET_KEY` установлен

### Ошибка "DisallowedHost"
- Обновите `ALLOWED_HOSTS` с реальным URL Railway
- Обновите `CSRF_TRUSTED_ORIGINS` с полным HTTPS URL

### Статические файлы не загружаются
- Проверьте, что `collectstatic` выполнился успешно в логах сборки
- WhiteNoise должен автоматически обслуживать статику

## Дополнительные сервисы (опционально)

### Redis для кеширования и Celery:

1. Добавьте Redis: "+ New" → "Database" → "Add Redis"
2. Добавьте переменные:
```bash
CELERY_BROKER_URL=${{Redis.REDIS_URL}}/0
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}/1
```

### Мониторинг с Sentry:

1. Создайте проект на https://sentry.io
2. Добавьте переменную:
```bash
SENTRY_DSN=ваш-sentry-dsn
```
