# ✅ Чеклист настройки Railway

## Перед деплоем:

- [x] Код отправлен на GitHub (https://github.com/Skorinov322/zorivaha.git)
- [x] Исправлен `build.sh` - добавлены миграции
- [x] Улучшен healthcheck

## На Railway:

### Шаг 1: Создание проекта
- [ ] Зарегистрирован на https://railway.app
- [ ] Создан новый проект
- [ ] Подключен GitHub репозиторий `Skorinov322/zorivaha`

### Шаг 2: База данных
- [ ] Добавлена PostgreSQL база данных (+ New → Database → PostgreSQL)
- [ ] Переменная `DATABASE_URL` создана автоматически

### Шаг 3: Переменные окружения (Settings → Variables)

#### Обязательные:
- [ ] `DJANGO_SETTINGS_MODULE=config.settings.prod`
- [ ] `DEBUG=False`
- [ ] `SECRET_KEY=<сгенерированный ключ>`
- [ ] `ALLOWED_HOSTS=*.railway.app`

#### После первого деплоя (когда получите URL):
- [ ] Обновить `ALLOWED_HOSTS=ваш-проект.railway.app,*.railway.app`
- [ ] Добавить `CSRF_TRUSTED_ORIGINS=https://ваш-проект.railway.app`

#### Опционально (Email):
- [ ] `EMAIL_HOST=smtp.gmail.com`
- [ ] `EMAIL_PORT=587`
- [ ] `EMAIL_USE_TLS=True`
- [ ] `EMAIL_HOST_USER=ваш-email@gmail.com`
- [ ] `EMAIL_HOST_PASSWORD=app-password`
- [ ] `DEFAULT_FROM_EMAIL=Зори Ваха <noreply@zorivaha.ru>`
- [ ] `CONTACT_EMAIL=info@zorivaha.ru`
- [ ] `CONTACT_PHONE=+7 (928) 000-00-00`

### Шаг 4: Деплой
- [ ] Деплой запущен автоматически
- [ ] Сборка прошла успешно (Build completed)
- [ ] Healthcheck прошел успешно
- [ ] Приложение запущено

### Шаг 5: Проверка
- [ ] Открывается `/health/` - показывает `{"status": "ok"}`
- [ ] Открывается главная страница `/`
- [ ] Открывается `/admin/` (может показать ошибку входа - это нормально)

### Шаг 6: Создание администратора
- [ ] Открыт `/setup/` и создан первый суперпользователь
  ИЛИ
- [ ] Использован Railway CLI: `railway run python manage.py createsuperuser`

### Шаг 7: Финальная проверка
- [ ] Вход в админку работает
- [ ] Можно создать тестовую бронь
- [ ] Email отправляется (если настроен)

## Команды для генерации SECRET_KEY:

### Python:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Или онлайн:
https://djecrety.ir/

## Полезные ссылки:

- 📖 Подробная инструкция: `RAILWAY_SETUP_INSTRUCTIONS.md`
- 🚀 Быстрый старт: `БЫСТРЫЙ_СТАРТ_RAILWAY.md`
- 🔗 GitHub репозиторий: https://github.com/Skorinov322/zorivaha
- 🚂 Railway Dashboard: https://railway.app/dashboard

## Troubleshooting:

### Healthcheck failed
✅ Проверьте, что PostgreSQL добавлен  
✅ Проверьте логи сборки - миграции должны выполниться  
✅ Убедитесь, что `SECRET_KEY` установлен  

### DisallowedHost at /
✅ Обновите `ALLOWED_HOSTS` с реальным URL Railway  
✅ Добавьте `CSRF_TRUSTED_ORIGINS` с https://  

### Static files не загружаются
✅ Проверьте логи - `collectstatic` должен выполниться  
✅ WhiteNoise включен в настройках  

### Не могу войти в админку
✅ Создайте суперпользователя через `/setup/` или CLI  
