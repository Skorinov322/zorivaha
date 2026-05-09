# Инструкция по деплою на Railway

## Подготовка проекта

Все необходимые файлы уже созданы:
- ✅ `requirements.txt` - зависимости Python
- ✅ `Procfile` - команды для запуска
- ✅ `runtime.txt` - версия Python
- ✅ `nixpacks.toml` - конфигурация сборки

## Шаги деплоя

### 1. Создайте проект на Railway

1. Зайдите на [railway.app](https://railway.app)
2. Войдите через GitHub
3. Нажмите "New Project"
4. Выберите "Deploy from GitHub repo"
5. Выберите ваш репозиторий

### 2. Добавьте PostgreSQL базу данных

1. В проекте нажмите "+ New"
2. Выберите "Database" → "Add PostgreSQL"
3. Railway автоматически создаст переменную `DATABASE_URL`

### 3. Добавьте Redis (опционально, для Celery)

1. В проекте нажмите "+ New"
2. Выберите "Database" → "Add Redis"
3. Railway создаст переменную `REDIS_URL`

### 4. Настройте переменные окружения

В настройках вашего сервиса добавьте следующие переменные:

#### Обязательные:
```
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=ваш-секретный-ключ-минимум-50-символов
DEBUG=False
ALLOWED_HOSTS=*.railway.app,ваш-домен.com
```

#### Для HTTPS:
```
CSRF_TRUSTED_ORIGINS=https://ваш-проект.railway.app,https://ваш-домен.com
```

#### Email (если используется):
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш-email@gmail.com
EMAIL_HOST_PASSWORD=ваш-app-password
DEFAULT_FROM_EMAIL=noreply@ваш-домен.com
```

#### Celery (если используется):
```
CELERY_BROKER_URL=${{Redis.REDIS_URL}}/0
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}/1
```

### 5. Генерация SECRET_KEY

Выполните в терминале:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 6. Деплой

Railway автоматически:
1. Установит зависимости из `requirements.txt`
2. Соберет статические файлы (`collectstatic`)
3. Выполнит миграции (`migrate`)
4. Запустит Gunicorn сервер

### 7. Проверка деплоя

1. Откройте логи в Railway
2. Проверьте, что нет ошибок
3. Откройте URL вашего приложения
4. Проверьте, что сайт работает

### 8. Создание суперпользователя

После успешного деплоя:
1. Откройте терминал в Railway (Settings → Terminal)
2. Выполните:
```bash
python manage.py createsuperuser
```

### 9. Загрузка начальных данных (если есть)

```bash
python manage.py loaddata fixtures/initial_data.json
```

## Troubleshooting

### Ошибка "no buildpack available"
- Убедитесь, что `requirements.txt` в корне проекта
- Проверьте, что `runtime.txt` содержит корректную версию Python

### Ошибка миграций
- Проверьте, что `DATABASE_URL` правильно настроен
- Убедитесь, что PostgreSQL сервис запущен

### Статические файлы не загружаются
- Проверьте, что `collectstatic` выполнился успешно
- Убедитесь, что `STATIC_ROOT` настроен правильно

### Ошибки Redis/Celery
- Если не используете Celery, закомментируйте соответствующие настройки
- Проверьте, что Redis сервис запущен и `REDIS_URL` настроен

## Полезные команды Railway CLI

Установка CLI:
```bash
npm i -g @railway/cli
```

Логин:
```bash
railway login
```

Просмотр логов:
```bash
railway logs
```

Выполнение команд:
```bash
railway run python manage.py migrate
railway run python manage.py createsuperuser
```

## Настройка домена

1. В Railway перейдите в Settings → Domains
2. Нажмите "Generate Domain" для получения бесплатного поддомена
3. Или добавьте свой домен через "Custom Domain"
4. Обновите `ALLOWED_HOSTS` и `CSRF_TRUSTED_ORIGINS`

## Мониторинг

Railway предоставляет:
- Логи в реальном времени
- Метрики использования ресурсов
- Автоматические перезапуски при сбоях

## Стоимость

- Railway предоставляет $5 бесплатных кредитов в месяц
- После этого оплата по факту использования
- PostgreSQL и Redis включены в стоимость
