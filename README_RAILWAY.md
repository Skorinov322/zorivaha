# 🚂 Деплой проекта "Зори Ваха" на Railway

## 📦 Что было сделано

Проект полностью подготовлен для деплоя на Railway:

### Созданные файлы:

1. **requirements.txt** - зависимости Python с поддержкой PostgreSQL
2. **Procfile** - команды для запуска веб-сервера и миграций
3. **runtime.txt** - версия Python (3.11.9)
4. **nixpacks.toml** - конфигурация сборки для Railway
5. **config/settings/prod.py** - обновлен для работы с PostgreSQL через DATABASE_URL

### Документация:

- **DEPLOY_QUICK_START.md** - быстрый старт (5 минут)
- **RAILWAY_DEPLOY.md** - полная инструкция со всеми деталями
- **CHECKLIST.md** - чеклист для проверки всех шагов
- **GIT_COMMANDS.md** - команды для коммита и пуша
- **.env.railway** - шаблон переменных окружения для Railway
- **railway_setup.sh** - скрипт для автоматической настройки

## 🚀 Быстрый старт (3 шага)

### 1. Закоммитьте изменения

```bash
git add .
git commit -m "feat: добавлена конфигурация для Railway"
git push origin main
```

### 2. Создайте проект на Railway

1. Откройте [railway.app](https://railway.app)
2. Войдите через GitHub
3. **New Project** → **Deploy from GitHub repo**
4. Выберите репозиторий `DP_zorivaha`

### 3. Настройте переменные окружения

В Railway добавьте:

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=ваш-секретный-ключ-50-символов
DEBUG=False
ALLOWED_HOSTS=*.railway.app
```

**Генерация SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4. Добавьте PostgreSQL

В проекте Railway:
- **+ New** → **Database** → **Add PostgreSQL**

Railway автоматически создаст `DATABASE_URL` и выполнит деплой!

## 📚 Документация

| Файл | Описание |
|------|----------|
| **DEPLOY_QUICK_START.md** | Быстрая инструкция для деплоя |
| **RAILWAY_DEPLOY.md** | Подробная документация |
| **CHECKLIST.md** | Чеклист всех шагов |
| **GIT_COMMANDS.md** | Команды Git |

## 🔧 Что настроено

### Backend
- ✅ Django 5.0.4
- ✅ PostgreSQL через psycopg2-binary
- ✅ Gunicorn WSGI сервер
- ✅ WhiteNoise для статических файлов
- ✅ Автоматические миграции при деплое

### Безопасность
- ✅ HTTPS редирект
- ✅ HSTS заголовки
- ✅ Secure cookies
- ✅ CSRF защита
- ✅ XSS защита

### Производительность
- ✅ Сжатие статических файлов
- ✅ Connection pooling для БД
- ✅ Redis кеширование (опционально)

## 🎯 Следующие шаги

1. **Прочитайте** `DEPLOY_QUICK_START.md`
2. **Выполните** команды из `GIT_COMMANDS.md`
3. **Следуйте** инструкциям по деплою
4. **Проверьте** все пункты в `CHECKLIST.md`

## 💡 Полезные ссылки

- [Railway Documentation](https://docs.railway.app/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)
- [PostgreSQL on Railway](https://docs.railway.app/databases/postgresql)

## 🆘 Помощь

Если возникли проблемы:

1. Проверьте логи в Railway (Deployments → View Logs)
2. Убедитесь, что все переменные окружения заданы
3. Проверьте, что PostgreSQL сервис запущен
4. Посмотрите раздел Troubleshooting в `RAILWAY_DEPLOY.md`

## 💰 Стоимость

- **$5** бесплатных кредитов в месяц
- Достаточно для небольшого проекта
- Оплата по факту использования после исчерпания кредитов

---

## ✨ Готово!

Ваш проект готов к деплою на Railway!

**Начните с файла `DEPLOY_QUICK_START.md` →**

---

*Создано для проекта "Зори Ваха" - система управления отелем*
