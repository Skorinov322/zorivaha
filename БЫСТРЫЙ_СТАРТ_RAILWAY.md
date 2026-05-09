# 🚀 Быстрый старт на Railway

## Что было исправлено:

✅ Добавлены миграции базы данных в `build.sh`  
✅ Улучшен healthcheck - теперь не падает без Redis/Celery  
✅ Создана таблица кеша автоматически при сборке  

## Что нужно сделать на Railway:

### 1. Добавьте PostgreSQL базу данных
В вашем проекте: **+ New** → **Database** → **Add PostgreSQL**

### 2. Установите минимальные переменные окружения

Перейдите в **Settings → Variables** и добавьте:

```
DJANGO_SETTINGS_MODULE=config.settings.prod
DEBUG=False
SECRET_KEY=<сгенерируйте ключ - см. ниже>
ALLOWED_HOSTS=*.railway.app
```

### Как сгенерировать SECRET_KEY:

Выполните локально в терминале:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Скопируйте результат и вставьте как значение `SECRET_KEY`.

### 3. Запустите деплой

Railway автоматически начнет новый деплой после push на GitHub.

### 4. После успешного деплоя обновите домены

Когда Railway даст вам URL (например, `zorivaha-production.up.railway.app`), обновите переменные:

```
ALLOWED_HOSTS=zorivaha-production.up.railway.app,*.railway.app
CSRF_TRUSTED_ORIGINS=https://zorivaha-production.up.railway.app
```

### 5. Создайте администратора

Откройте в браузере: `https://ваш-проект.railway.app/setup/`

Или через Railway CLI:
```bash
railway run python manage.py createsuperuser
```

## Проверка работы:

- ✅ Healthcheck: `/health/` - должен вернуть `{"status": "ok", "db": "ok", ...}`
- ✅ Главная страница: `/`
- ✅ Админка: `/admin/`

## Опционально: Email настройки

Для отправки писем добавьте:

```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш-email@gmail.com
EMAIL_HOST_PASSWORD=ваш-app-password-от-google
DEFAULT_FROM_EMAIL=Зори Ваха <noreply@zorivaha.ru>
CONTACT_EMAIL=info@zorivaha.ru
CONTACT_PHONE=+7 (928) 000-00-00
```

## Если что-то пошло не так:

1. Проверьте логи деплоя в Railway
2. Убедитесь, что PostgreSQL база добавлена
3. Проверьте, что все обязательные переменные установлены
4. Откройте `/health/` чтобы увидеть статус компонентов

---

📖 Подробная инструкция: `RAILWAY_SETUP_INSTRUCTIONS.md`
