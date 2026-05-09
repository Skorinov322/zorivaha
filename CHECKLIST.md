# ✅ Чеклист деплоя на Railway

## Подготовка проекта (✅ Готово)

- [x] `requirements.txt` - зависимости Python с PostgreSQL
- [x] `Procfile` - команды для запуска и миграций
- [x] `runtime.txt` - версия Python 3.11.9
- [x] `nixpacks.toml` - конфигурация сборки
- [x] Настройки PostgreSQL в `config/settings/prod.py`
- [x] Инструкции по деплою

## Действия на Railway

### 1. Создание проекта
- [ ] Зарегистрироваться на [railway.app](https://railway.app)
- [ ] Войти через GitHub
- [ ] Создать новый проект
- [ ] Подключить репозиторий `DP_zorivaha`

### 2. База данных
- [ ] Добавить PostgreSQL (+ New → Database → PostgreSQL)
- [ ] Убедиться, что создана переменная `DATABASE_URL`

### 3. Переменные окружения

#### Обязательные:
- [ ] `DJANGO_SETTINGS_MODULE=config.settings.prod`
- [ ] `SECRET_KEY=` (сгенерировать командой ниже)
- [ ] `DEBUG=False`
- [ ] `ALLOWED_HOSTS=*.railway.app`

**Генерация SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### После получения домена:
- [ ] `CSRF_TRUSTED_ORIGINS=https://ваш-проект.railway.app`
- [ ] Обновить `ALLOWED_HOSTS` с реальным доменом

### 4. Деплой
- [ ] Дождаться завершения автоматического деплоя
- [ ] Проверить логи на наличие ошибок
- [ ] Убедиться, что миграции выполнились

### 5. Настройка домена
- [ ] Settings → Domains → Generate Domain
- [ ] Скопировать полученный домен
- [ ] Обновить переменные `ALLOWED_HOSTS` и `CSRF_TRUSTED_ORIGINS`

### 6. Создание суперпользователя
- [ ] Открыть Settings → Terminal
- [ ] Выполнить: `python manage.py createsuperuser`
- [ ] Ввести email и пароль

### 7. Проверка работы
- [ ] Открыть главную страницу
- [ ] Проверить загрузку статических файлов
- [ ] Войти в админку `/admin/`
- [ ] Проверить основные функции сайта

## Опциональные настройки

### Redis (для Celery)
- [ ] Добавить Redis (+ New → Database → Redis)
- [ ] Добавить переменные:
  - `CELERY_BROKER_URL=${{Redis.REDIS_URL}}/0`
  - `CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}/1`

### Email
- [ ] Настроить SMTP (Gmail/Yandex/Mail.ru)
- [ ] Добавить переменные:
  - `EMAIL_HOST=smtp.gmail.com`
  - `EMAIL_PORT=587`
  - `EMAIL_USE_TLS=True`
  - `EMAIL_HOST_USER=ваш-email@gmail.com`
  - `EMAIL_HOST_PASSWORD=app-password`

### Sentry (мониторинг ошибок)
- [ ] Зарегистрироваться на [sentry.io](https://sentry.io)
- [ ] Создать проект Django
- [ ] Добавить переменную `SENTRY_DSN=ваш-dsn`

### Свой домен
- [ ] Добавить Custom Domain в Railway
- [ ] Настроить DNS записи у регистратора
- [ ] Обновить `ALLOWED_HOSTS` и `CSRF_TRUSTED_ORIGINS`

## Загрузка данных

### Начальные данные (если есть)
- [ ] `railway run python manage.py loaddata fixtures/initial_data.json`

### Медиа файлы
- [ ] Настроить S3/Cloudinary для хранения медиа (опционально)
- [ ] Или загрузить через админку

## Мониторинг

- [ ] Настроить уведомления о деплоях
- [ ] Проверить метрики использования ресурсов
- [ ] Настроить алерты при ошибках

## Документация

📖 Подробные инструкции:
- `DEPLOY_QUICK_START.md` - быстрый старт
- `RAILWAY_DEPLOY.md` - полная документация
- `.env.railway` - пример переменных окружения

## Полезные команды

```bash
# Установка Railway CLI
npm i -g @railway/cli

# Логин
railway login

# Просмотр логов
railway logs

# Выполнение команд
railway run python manage.py migrate
railway run python manage.py createsuperuser
railway run python manage.py collectstatic --noinput
```

## Стоимость

- 💰 $5 бесплатных кредитов в месяц
- 📊 Мониторинг использования в Dashboard
- 💳 Оплата по факту после исчерпания кредитов

---

**Статус:** Проект готов к деплою! 🚀

**Следующий шаг:** Откройте `DEPLOY_QUICK_START.md` и следуйте инструкциям.
