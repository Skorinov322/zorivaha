# 📝 Команды Git для деплоя

## Текущий статус

Созданы файлы для деплоя на Railway:
- ✅ requirements.txt
- ✅ Procfile
- ✅ runtime.txt
- ✅ nixpacks.toml
- ✅ config/settings/prod.py (обновлен для PostgreSQL)
- ✅ Документация (RAILWAY_DEPLOY.md, DEPLOY_QUICK_START.md, CHECKLIST.md)

## Команды для коммита

```bash
# 1. Добавить все новые файлы
git add requirements.txt Procfile runtime.txt nixpacks.toml
git add config/settings/prod.py
git add RAILWAY_DEPLOY.md DEPLOY_QUICK_START.md CHECKLIST.md
git add .env.railway railway_setup.sh

# 2. Создать коммит
git commit -m "feat: добавлена конфигурация для деплоя на Railway

- Добавлен requirements.txt с PostgreSQL
- Создан Procfile для запуска на Railway
- Настроен runtime.txt с Python 3.11.9
- Добавлен nixpacks.toml для конфигурации сборки
- Обновлены настройки prod.py для работы с PostgreSQL
- Добавлена документация по деплою"

# 3. Пуш в репозиторий
git push origin main
```

## Если есть конфликты

```bash
# Сначала получить изменения с сервера
git pull origin main --rebase

# Если есть конфликты, разрешить их и продолжить
git add .
git rebase --continue

# Затем запушить
git push origin main
```

## Альтернативный вариант (если нужен merge)

```bash
# Получить изменения
git pull origin main

# Разрешить конфликты (если есть)
git add .
git commit -m "merge: объединение с удаленной веткой"

# Запушить
git push origin main
```

## После пуша

1. Откройте [railway.app](https://railway.app)
2. Создайте новый проект
3. Подключите ваш GitHub репозиторий
4. Railway автоматически обнаружит конфигурацию и начнет деплой

## Проверка перед пушем

```bash
# Проверить, что все файлы добавлены
git status

# Посмотреть изменения
git diff config/settings/prod.py

# Проверить, что .env не добавлен (он в .gitignore)
git status | grep ".env"
```

## Важно! 🔒

**НЕ коммитьте файл `.env` с реальными секретами!**

Файл `.env.railway` - это только шаблон для Railway.
Реальные секреты добавляйте через веб-интерфейс Railway.

---

**Готово к пушу! После выполнения команд выше переходите к деплою на Railway.**
