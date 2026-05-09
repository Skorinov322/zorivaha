#!/bin/bash
# Railway Setup Script
# Этот скрипт поможет настроить проект для деплоя на Railway

echo "🚂 Railway Setup для Зори Ваха"
echo "================================"
echo ""

# Проверка наличия Railway CLI
if ! command -v railway &> /dev/null; then
    echo "⚠️  Railway CLI не установлен"
    echo "Установите его командой: npm i -g @railway/cli"
    echo "Или продолжите настройку через веб-интерфейс Railway"
    echo ""
    read -p "Продолжить без CLI? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Генерация SECRET_KEY
echo "🔑 Генерация SECRET_KEY..."
SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
echo "SECRET_KEY сгенерирован: $SECRET_KEY"
echo ""

# Проверка requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt не найден!"
    exit 1
fi
echo "✅ requirements.txt найден"

# Проверка Procfile
if [ ! -f "Procfile" ]; then
    echo "❌ Procfile не найден!"
    exit 1
fi
echo "✅ Procfile найден"

# Проверка runtime.txt
if [ ! -f "runtime.txt" ]; then
    echo "❌ runtime.txt не найден!"
    exit 1
fi
echo "✅ runtime.txt найден"

echo ""
echo "📋 Следующие шаги:"
echo "1. Создайте проект на railway.app"
echo "2. Подключите GitHub репозиторий"
echo "3. Добавьте PostgreSQL базу данных"
echo "4. Добавьте Redis (если используете Celery)"
echo "5. Добавьте переменные окружения:"
echo ""
echo "   DJANGO_SETTINGS_MODULE=config.settings.prod"
echo "   SECRET_KEY=$SECRET_KEY"
echo "   DEBUG=False"
echo "   ALLOWED_HOSTS=*.railway.app"
echo "   CSRF_TRUSTED_ORIGINS=https://ваш-проект.railway.app"
echo ""
echo "6. Railway автоматически выполнит деплой"
echo ""
echo "📖 Подробная инструкция в файле RAILWAY_DEPLOY.md"
echo ""

# Если Railway CLI установлен
if command -v railway &> /dev/null; then
    echo "🚀 Railway CLI обнаружен!"
    read -p "Хотите инициализировать проект сейчас? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        railway login
        railway init
        echo ""
        echo "✅ Проект инициализирован!"
        echo "Теперь добавьте переменные окружения через веб-интерфейс"
    fi
fi

echo ""
echo "✨ Готово! Удачного деплоя!"
