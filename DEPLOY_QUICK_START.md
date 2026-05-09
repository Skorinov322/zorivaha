# 🚂 Быстрый старт: Деплой на Railway

## 1️⃣ Подготовка (уже сделано ✅)

Все необходимые файлы созданы:
- `requirements.txt` - зависимости
- `Procfile` - команды запуска
- `runtime.txt` - версия Python
- `nixpacks.toml` - конфигурация сборки

## 2️⃣ Создание проекта на Railway

1. Откройте [railway.app](https://railway.app)
2. Войдите через GitHub
3. **New Project** → **Deploy from GitHub repo**
4. Выберите ваш репозиторий `DP_zorivaha`

## 3️⃣ Добавление базы данных

В проекте Railway:
1. Нажмите **+ New** → **Database** → **Add PostgreSQL**
2. Railway автоматически создаст переменную `DATABASE_URL`

## 4️⃣ Настройка переменных окружения

В настройках сервиса (**Settings** → **Variables**) добавьте:

### Обязательные переменные:

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=ваш-секретный-ключ-50-символов
DEBUG=False
ALLOWED_HOSTS=*.railway.app
```

### Генерация SECRET_KEY:

Выполните локально:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Для HTTPS (после получения домена):

```bash
CSRF_TRUSTED_ORIGINS=https://ваш-проект.railway.app
```

## 5️⃣ Деплой

Railway автоматически:
- ✅ Установит зависимости
- ✅ Соберет статические файлы
- ✅ Выполнит миграции
- ✅ Запустит сервер

Следите за процессом в разделе **Deployments**.

## 6️⃣ Создание суперпользователя

После успешного деплоя:

1. Откройте **Settings** → **Terminal** в Railway
2. Выполните:
```bash
python manage.py createsuperuser
```

## 7️⃣ Получение домена

1. **Settings** → **Domains**
2. **Generate Domain** - получите бесплатный домен `*.railway.app`
3. Обновите переменную `ALLOWED_HOSTS` с новым доменом

## 8️⃣ Проверка

Откройте ваш домен и проверьте:
- ✅ Главная страница загружается
- ✅ Статические файлы работают
- ✅ Админка доступна по `/admin/`

---

## 🔧 Опциональные настройки

### Redis (для Celery)

Если используете Celery:
1. **+ New** → **Database** → **Add Redis**
2. Добавьте переменные:
```bash
CELERY_BROKER_URL=${{Redis.REDIS_URL}}/0
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}/1
```

### Email

Для отправки писем добавьте:
```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш-email@gmail.com
EMAIL_HOST_PASSWORD=ваш-app-password
```

**Для Gmail:** используйте App Password (не обычный пароль):
- Google Account → Security → 2-Step Verification → App passwords

---

## 🐛 Решение проблем

### Ошибка при деплое
- Проверьте логи в разделе **Deployments**
- Убедитесь, что все переменные окружения заданы

### Статика не загружается
- Проверьте, что `collectstatic` выполнился успешно
- Посмотрите логи сборки

### База данных не подключается
- Убедитесь, что PostgreSQL сервис запущен
- Проверьте, что `DATABASE_URL` создан автоматически

---

## 📚 Полная документация

Подробная инструкция в файле `RAILWAY_DEPLOY.md`

## 💰 Стоимость

- **$5** бесплатных кредитов в месяц
- Этого достаточно для небольшого проекта
- После этого оплата по факту использования

---

**Готово! Ваш проект на Railway! 🎉**
