# 🏗️ Архитектура клиентской части

Подробное описание архитектуры frontend части проекта "Зори Ваха".

## 📊 Общая схема

```
┌─────────────────────────────────────────────────────────────┐
│                    КЛИЕНТСКАЯ ЧАСТЬ                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Django     │  │   Bootstrap  │  │   Vanilla    │      │
│  │  Templates   │  │      5       │  │  JavaScript  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                           │                                  │
│              ┌────────────▼────────────┐                     │
│              │   Server-Side Rendering │                     │
│              │   (SSR) + Progressive   │                     │
│              │     Enhancement (PE)    │                     │
│              └─────────────────────────┘                     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Архитектурные принципы

### 1. Server-Side Rendering (SSR)
- HTML генерируется на сервере (Django)
- Полностью рабочий контент без JavaScript
- SEO-оптимизация из коробки
- Быстрая первая отрисовка (FCP)

### 2. Progressive Enhancement
- Базовая функциональность работает без JS
- JavaScript добавляет улучшения (анимации, валидация)
- Graceful degradation для старых браузеров

### 3. Mobile-First
- Дизайн начинается с мобильных устройств
- Адаптивная верстка через медиа-запросы
- Touch-friendly интерфейс

### 4. Accessibility (A11y)
- Семантическая HTML разметка
- ARIA атрибуты где необходимо
- Keyboard navigation
- Screen reader friendly

## 📁 Структура файлов

```
frontend/
├── index.html                 # Главная страница
├── pages/                     # Остальные страницы
│   ├── rooms.html            # Каталог номеров
│   ├── room-detail.html      # Детальная страница
│   ├── about.html            # О гостинице
│   ├── contacts.html         # Контакты
│   └── gallery.html          # Галерея
├── css/                       # Стили
│   ├── main.css              # Глобальные стили
│   ├── hotel.css             # Публичные страницы
│   ├── grand-soleil.css      # Дизайн-система
│   └── admin_custom.css      # Админка
├── js/                        # JavaScript
│   ├── main.js               # Основной функционал
│   └── booking.js            # Бронирование
└── img/                       # Изображения
    └── logoZV.png            # Логотип
```

## 🎨 CSS Архитектура

### Слои стилей

```
┌─────────────────────────────────────┐
│  1. Внешние библиотеки              │
│     - Bootstrap 5                   │
│     - Bootstrap Icons               │
│     - Google Fonts                  │
├─────────────────────────────────────┤
│  2. Дизайн-система (grand-soleil)  │
│     - CSS переменные                │
│     - Базовые стили                 │
│     - Анимации                      │
├─────────────────────────────────────┤
│  3. Глобальные стили (main.css)    │
│     - Reset & Base                  │
│     - Bootstrap overrides           │
│     - Утилиты                       │
├─────────────────────────────────────┤
│  4. Компонентные стили (hotel.css) │
│     - Кнопки                        │
│     - Карточки                      │
│     - Формы                         │
├─────────────────────────────────────┤
│  5. Страничные стили                │
│     - Inline <style> в шаблонах    │
│     - Специфичные для страницы      │
└─────────────────────────────────────┘
```

### CSS Методология

**BEM-подобный подход** (упрощенный):
```css
/* Блок */
.room-card { }

/* Элемент */
.room-card-body { }
.room-card-footer { }

/* Модификатор */
.room-card.featured { }
```

**Утилитарные классы** (Bootstrap):
```html
<div class="d-flex justify-content-between mb-3">
```

### CSS Переменные

```css
:root {
  /* Цвета */
  --background: #eff0f3;
  --headline: #0d0d0d;
  --button: #ff8e3c;
  
  /* Размеры */
  --radius-sm: 10px;
  --radius-md: 16px;
  
  /* Анимации */
  --ease-out: cubic-bezier(.16,1,.3,1);
}
```

## ⚡ JavaScript Архитектура

### Модульная структура

```javascript
// main.js - Глобальный функционал
├── Auto-dismiss alerts
├── Form loading states
├── Confirm dialogs
├── Password visibility toggle
├── Smooth scroll
├── Tooltip initialization
└── Active nav highlight

// booking.js - Специфичный функционал
├── PhoneMask class
│   ├── handleInput()
│   ├── handleKeydown()
│   └── formatValue()
└── BookingPriceCalculator class
    ├── init()
    ├── updatePreview()
    └── calculatePrice()
```

### Паттерны

**1. Class-based компоненты**
```javascript
class PhoneMask {
  constructor(input) {
    this.input = input;
    this.init();
  }
  
  init() {
    this.input.addEventListener('input', (e) => this.handleInput(e));
  }
  
  handleInput(e) {
    // Логика
  }
}
```

**2. Event Delegation**
```javascript
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', handleConfirm);
  });
});
```

**3. Intersection Observer для анимаций**
```javascript
const observer = new IntersectionObserver(
  entries => entries.forEach(e => {
    if (e.isIntersecting) e.target.classList.add('visible');
  }),
  { threshold: 0.1 }
);
```

## 🎭 Компонентная модель

### Атомарный дизайн (упрощенный)

```
Атомы (Atoms)
├── Кнопки (.btn-luxury)
├── Иконки (<i class="bi bi-*">)
├── Инпуты (.lux-input)
└── Текст (.eyebrow, .section-heading)

Молекулы (Molecules)
├── Поле формы (label + input)
├── Карточка цены (price-box)
├── Спецификация (spec-item)
└── Бейдж доступности (avail-badge)

Организмы (Organisms)
├── Навбар (navbar)
├── Карточка номера (room-card)
├── Форма поиска (search-form)
└── Футер (footer)

Шаблоны (Templates)
├── Главная страница
├── Каталог
├── Детальная страница
└── Контакты

Страницы (Pages)
└── Конкретные экземпляры с данными
```

## 📱 Адаптивная стратегия

### Брейкпоинты

```css
/* Mobile First подход */

/* Base: 320px+ (Mobile) */
.container { padding: 0 16px; }

/* Small: 576px+ */
@media (min-width: 576px) {
  .container { padding: 0 24px; }
}

/* Medium: 768px+ (Tablet) */
@media (min-width: 768px) {
  .container { max-width: 720px; }
}

/* Large: 992px+ */
@media (min-width: 992px) {
  .container { max-width: 960px; }
}

/* XL: 1200px+ (Desktop) */
@media (min-width: 1200px) {
  .container { max-width: 1140px; }
}

/* XXL: 1400px+ */
@media (min-width: 1400px) {
  .container { max-width: 1320px; }
}
```

### Адаптивные компоненты

**Grid система**:
```html
<div class="row">
  <div class="col-12 col-md-6 col-lg-4">
    <!-- 12 колонок на mobile, 6 на tablet, 4 на desktop -->
  </div>
</div>
```

**Адаптивная типографика**:
```css
.hero-title {
  font-size: clamp(2rem, 5vw, 4rem);
  /* min: 2rem, preferred: 5vw, max: 4rem */
}
```

## 🎬 Анимации и переходы

### Типы анимаций

**1. Появление при скролле (Reveal)**
```css
.reveal {
  opacity: 0;
  transform: translateY(24px);
  transition: opacity .7s var(--ease-out), 
              transform .7s var(--ease-out);
}

.reveal.visible {
  opacity: 1;
  transform: translateY(0);
}
```

**2. Hover эффекты**
```css
.room-card {
  transition: transform .35s var(--ease-out);
}

.room-card:hover {
  transform: translateY(-8px);
}
```

**3. Keyframe анимации**
```css
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.floating-element {
  animation: float 7s ease-in-out infinite;
}
```

### Performance

- Используем `transform` и `opacity` (GPU-accelerated)
- Избегаем анимации `width`, `height`, `top`, `left`
- `will-change` для критичных анимаций
- `requestAnimationFrame` для JS анимаций

## 🔄 Жизненный цикл страницы

```
1. HTML загружен
   ↓
2. CSS применен (FOUC prevention)
   ↓
3. DOMContentLoaded
   ├── Инициализация компонентов
   ├── Event listeners
   └── Intersection Observers
   ↓
4. Изображения загружены
   ↓
5. window.onload
   └── Финальные настройки
```

### Критический путь рендеринга

```
HTML → CSS → JavaScript → Render → Paint
  ↓      ↓        ↓          ↓       ↓
 Fast   Fast   Deferred   Fast    Fast
```

**Оптимизации**:
- Inline критичный CSS
- Defer некритичный JS
- Preconnect к внешним ресурсам
- Lazy loading изображений

## 🎯 Паттерны взаимодействия

### 1. Формы

```
Пользователь вводит данные
   ↓
Валидация на клиенте (JS)
   ↓
Визуальная обратная связь
   ↓
Отправка на сервер
   ↓
Обработка ответа
   ↓
Уведомление пользователя
```

### 2. Навигация

```
Клик по ссылке
   ↓
Плавная прокрутка (если якорь)
   ↓
Переход на страницу
   ↓
Подсветка активного пункта
```

### 3. Модальные окна

```
Триггер (клик)
   ↓
Открытие модалки
   ↓
Блокировка скролла body
   ↓
Фокус на модалке
   ↓
Закрытие (ESC / клик вне / кнопка)
   ↓
Восстановление скролла
```

## 🔐 Безопасность

### XSS Prevention
- Все пользовательские данные экранируются Django
- Использование `textContent` вместо `innerHTML` в JS
- CSP заголовки (в Django)

### CSRF Protection
- Django CSRF токены в формах
- Проверка на backend

## 📊 Производительность

### Метрики

- **FCP** (First Contentful Paint): < 1.8s
- **LCP** (Largest Contentful Paint): < 2.5s
- **FID** (First Input Delay): < 100ms
- **CLS** (Cumulative Layout Shift): < 0.1

### Оптимизации

**HTML**:
- Семантическая разметка
- Минификация (в продакшене)

**CSS**:
- Критичный CSS inline
- Остальное async
- Минификация и сжатие

**JavaScript**:
- Defer/async загрузка
- Code splitting
- Минификация

**Изображения**:
- Lazy loading
- WebP формат
- Responsive images

## 🧪 Тестирование

### Браузеры
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Устройства
- Desktop (1920x1080, 1366x768)
- Tablet (768x1024)
- Mobile (375x667, 414x896)

### Accessibility
- WCAG 2.1 Level AA
- Keyboard navigation
- Screen reader testing

## 📚 Зависимости

### Внешние библиотеки

```html
<!-- Bootstrap 5.3.3 -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>

<!-- Bootstrap Icons 1.11.3 -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">

<!-- Google Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600;700&family=DM+Sans:wght@300;400;500&display=swap">
```

### Почему эти библиотеки?

**Bootstrap 5**:
- Проверенная grid система
- Готовые компоненты
- Хорошая документация
- Без jQuery

**Bootstrap Icons**:
- Единый стиль иконок
- SVG формат
- Легковесные

**Google Fonts**:
- Красивая типографика
- Быстрая загрузка
- Кроссбраузерность

## 🔮 Будущие улучшения

1. **PWA** - Progressive Web App
2. **Service Worker** - Offline support
3. **Web Components** - Переиспользуемые компоненты
4. **CSS Grid** - Более гибкие layouts
5. **Intersection Observer v2** - Лучшая производительность
6. **View Transitions API** - Плавные переходы между страницами

---

**Версия**: 1.0.0  
**Дата**: 2026-05-08  
**Автор**: Команда Зори Ваха
