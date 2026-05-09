# 📖 Документация Frontend - Зори Ваха

Добро пожаловать в документацию клиентской части проекта "Зори Ваха"!

## 🗂️ Навигация по документации

### 📘 Основные документы

1. **[README.md](README.md)** - Общая информация о проекте
   - Структура файлов
   - Дизайн-система
   - Адаптивность
   - Особенности

2. **[USAGE.md](USAGE.md)** - Руководство по использованию
   - Быстрый старт
   - Локальный сервер
   - Кастомизация
   - Деплой

3. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Архитектура
   - Архитектурные принципы
   - CSS архитектура
   - JavaScript архитектура
   - Производительность

4. **[COMPONENTS.md](COMPONENTS.md)** - Библиотека компонентов
   - Кнопки
   - Карточки
   - Формы
   - Навигация
   - Анимации

## 🚀 Быстрый старт

### 1. Открыть в браузере
```bash
# Windows
start index.html

# macOS
open index.html

# Linux
xdg-open index.html
```

### 2. Запустить локальный сервер
```bash
cd frontend
python -m http.server 8000
# Откройте http://localhost:8000
```

## 📁 Структура проекта

```
frontend/
├── 📄 index.html              # Главная страница
├── 📁 pages/                  # Остальные страницы
│   ├── rooms.html            # Каталог номеров
│   ├── room-detail.html      # Детальная страница
│   ├── about.html            # О гостинице
│   ├── contacts.html         # Контакты
│   └── gallery.html          # Галерея
├── 🎨 css/                    # Стили
│   ├── main.css              # Глобальные стили
│   ├── hotel.css             # Публичные страницы
│   ├── grand-soleil.css      # Дизайн-система
│   └── admin_custom.css      # Админка
├── ⚡ js/                     # JavaScript
│   ├── main.js               # Основной функционал
│   └── booking.js            # Бронирование
├── 🖼️ img/                    # Изображения
│   └── logoZV.png            # Логотип
└── 📚 Документация
    ├── README.md             # Общая информация
    ├── USAGE.md              # Руководство
    ├── ARCHITECTURE.md       # Архитектура
    ├── COMPONENTS.md         # Компоненты
    └── INDEX.md              # Этот файл
```

## 🎨 Дизайн-система

### Цветовая палитра

| Цвет | Hex | Использование |
|------|-----|---------------|
| 🟠 Orange | `#ff8e3c` | Основной акцент (кнопки, ссылки) |
| ⚪ Background | `#eff0f3` | Основной фон |
| ⚫ Headline | `#0d0d0d` | Заголовки |
| 🔘 Paragraph | `#2a2a2a` | Основной текст |
| ⬜ Secondary | `#ffffff` | Карточки, модалки |
| 🔴 Tertiary | `#d9376e` | Дополнительный акцент |

### Типографика

- **Заголовки**: Cormorant Garamond (serif)
- **Текст**: DM Sans (sans-serif)

### Компоненты

- ✅ Кнопки: 3 варианта
- ✅ Карточки: 5+ типов
- ✅ Формы: Полный набор
- ✅ Навигация: Header + Footer + Breadcrumbs
- ✅ Анимации: Reveal, Fade, Float, Pulse

## 📱 Адаптивность

| Устройство | Ширина | Брейкпоинт |
|------------|--------|------------|
| 📱 Mobile | < 768px | Base |
| 📱 Tablet | 768px - 1199px | md |
| 💻 Desktop | 1200px+ | lg, xl, xxl |

## ⚡ Основной функционал

### JavaScript возможности

**main.js**:
- ✅ Автозакрытие уведомлений
- ✅ Индикаторы загрузки
- ✅ Подтверждение действий
- ✅ Переключение видимости пароля
- ✅ Плавная прокрутка
- ✅ Тултипы Bootstrap
- ✅ Подсветка активной ссылки

**booking.js**:
- ✅ Маска телефона
- ✅ Расчет стоимости
- ✅ Валидация дат
- ✅ Управление формой

## 🎯 Страницы

### Публичные страницы

1. **[index.html](index.html)** - Главная
   - Hero секция
   - Поиск номеров
   - Популярные номера
   - Преимущества
   - CTA секция

2. **[pages/rooms.html](pages/rooms.html)** - Каталог
   - Фильтр по датам
   - Карточки номеров
   - Статусы доступности

3. **[pages/room-detail.html](pages/room-detail.html)** - Детальная
   - Галерея фотографий
   - Описание номера
   - Спецификации
   - Отзывы
   - Форма бронирования

4. **[pages/about.html](pages/about.html)** - О нас
   - История
   - Миссия
   - Услуги
   - Статистика

5. **[pages/contacts.html](pages/contacts.html)** - Контакты
   - Контактная информация
   - Карта
   - Форма обратной связи

6. **[pages/gallery.html](pages/gallery.html)** - Галерея
   - Фотогалерея
   - Фильтры
   - Lightbox

## 🛠️ Технологии

### Frontend Stack

| Технология | Версия | Назначение |
|------------|--------|------------|
| HTML5 | - | Разметка |
| CSS3 | - | Стилизация |
| JavaScript | ES6+ | Интерактивность |
| Bootstrap | 5.3.3 | UI Framework |
| Bootstrap Icons | 1.11.3 | Иконки |
| Google Fonts | - | Типографика |

### Архитектурные паттерны

- ✅ **SSR** (Server-Side Rendering)
- ✅ **Progressive Enhancement**
- ✅ **Mobile-First**
- ✅ **BEM-like CSS**
- ✅ **Atomic Design**
- ✅ **Class-based JS**

## 📊 Производительность

### Целевые метрики

| Метрика | Цель | Описание |
|---------|------|----------|
| FCP | < 1.8s | First Contentful Paint |
| LCP | < 2.5s | Largest Contentful Paint |
| FID | < 100ms | First Input Delay |
| CLS | < 0.1 | Cumulative Layout Shift |

### Оптимизации

- ✅ Lazy loading изображений
- ✅ Defer JavaScript
- ✅ Минификация CSS/JS (prod)
- ✅ Сжатие ресурсов
- ✅ CDN для библиотек

## 🔐 Безопасность

- ✅ XSS Prevention
- ✅ CSRF Protection (Django)
- ✅ Content Security Policy
- ✅ Secure Headers

## ♿ Доступность

- ✅ Семантическая HTML разметка
- ✅ ARIA атрибуты
- ✅ Keyboard navigation
- ✅ Screen reader friendly
- ✅ WCAG 2.1 Level AA

## 🧪 Тестирование

### Поддерживаемые браузеры

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

### Тестовые устройства

- ✅ Desktop (1920x1080, 1366x768)
- ✅ Tablet (768x1024)
- ✅ Mobile (375x667, 414x896)

## 📚 Полезные ссылки

### Внешние ресурсы

- [Bootstrap 5 Docs](https://getbootstrap.com/docs/5.3/)
- [Bootstrap Icons](https://icons.getbootstrap.com/)
- [Google Fonts](https://fonts.google.com/)
- [MDN Web Docs](https://developer.mozilla.org/)
- [Can I Use](https://caniuse.com/)

### Инструменты

- [VS Code](https://code.visualstudio.com/) - Редактор кода
- [Live Server](https://marketplace.visualstudio.com/items?itemName=ritwickdey.LiveServer) - Локальный сервер
- [Chrome DevTools](https://developer.chrome.com/docs/devtools/) - Отладка
- [Lighthouse](https://developers.google.com/web/tools/lighthouse) - Аудит производительности

## 🚫 Ограничения

Эта статическая копия **НЕ включает**:

- ❌ Backend функционал (Django)
- ❌ Базу данных
- ❌ Аутентификацию
- ❌ Реальное бронирование
- ❌ Отправку форм
- ❌ Динамическую загрузку
- ❌ Личный кабинет
- ❌ Админ-панель

Для полного функционала используйте основной Django проект.

## 🔄 Обновление

Чтобы обновить статическую копию после изменений в Django шаблонах:

```bash
python frontend/generate_static.py
```

## 📞 Поддержка

Если возникли вопросы:

1. Проверьте документацию
2. Изучите исходный код
3. Посмотрите примеры в компонентах
4. Обратитесь к команде разработки

## 📝 Changelog

### v1.0.0 (2026-05-08)
- ✅ Первый релиз статической копии
- ✅ 6 страниц
- ✅ Полная документация
- ✅ Адаптивный дизайн
- ✅ Анимации и интерактивность

## 📄 Лицензия

Эта статическая копия является частью проекта "Зори Ваха" и распространяется под той же лицензией.

---

## 🎯 Следующие шаги

1. **Изучите** [USAGE.md](USAGE.md) для начала работы
2. **Прочитайте** [ARCHITECTURE.md](ARCHITECTURE.md) для понимания структуры
3. **Используйте** [COMPONENTS.md](COMPONENTS.md) как справочник
4. **Откройте** `index.html` и начните экспериментировать!

---

**Создано**: 2026-05-08  
**Версия**: 1.0.0  
**Проект**: Зори Ваха - Система управления гостиницей  
**Команда**: Frontend Team

🌟 **Приятной работы!** 🌟
