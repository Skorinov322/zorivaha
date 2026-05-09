# ER-диаграмма базы данных системы управления гостиницей (DBML)

## Полная схема в формате DBML

```dbml
// ============================================
// ACCOUNTS (Пользователи и роли)
// ============================================

Table users {
  id integer [primary key]
  email varchar(100) [not null, unique]
  password varchar(255) [not null]
  role varchar(20) [not null, note: 'user|receptionist|manager|admin|super_admin']
  first_name varchar(50)
  last_name varchar(50)
  phone varchar(30)
  date_of_birth date
  avatar varchar(255)
  passport_series varchar(10)
  passport_number varchar(20)
  passport_issued_by varchar(255)
  passport_issued_date date
  preferred_language varchar(10) [default: 'ru']
  marketing_consent boolean [default: false]
  email_notifications boolean [default: true]
  is_active boolean [not null, default: true]
  is_staff boolean [not null, default: false]
  is_superuser boolean [not null, default: false]
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

// ============================================
// HOTEL (Номера и категории)
// ============================================

Table amenities {
  id integer [primary key]
  name varchar(100) [not null, unique]
  icon varchar(50)
  category varchar(20) [note: 'comfort|tech|food|wellness|service']
  is_highlighted boolean [default: false]
  sort_order integer [default: 0]
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

Table room_categories {
  id integer [primary key]
  name varchar(100) [not null, unique]
  slug varchar(100) [not null, unique]
  description text
  short_description varchar(255)
  max_guests integer [not null]
  bed_type varchar(20) [note: 'single|double|twin|king|bunk']
  area_sqm integer
  base_price_per_night decimal(10,2) [not null]
  weekend_price_per_night decimal(10,2)
  thumbnail varchar(255)
  is_active boolean [not null, default: true]
  is_featured boolean [default: false]
  sort_order integer [default: 0]
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

Table room_category_amenities {
  id integer [primary key]
  room_category_id integer [not null]
  amenity_id integer [not null]
  
  indexes {
    (room_category_id, amenity_id) [unique]
  }
}

Table room_images {
  id integer [primary key]
  category_id integer [not null]
  image varchar(255) [not null]
  caption varchar(255)
  alt_text varchar(255)
  is_primary boolean [default: false]
  sort_order integer [default: 0]
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

Table rooms {
  id integer [primary key]
  category_id integer [not null]
  number varchar(20) [not null]
  subdivision varchar(10) [note: 'а, б, в для подразделений']
  floor integer
  max_guests_per_room integer [not null]
  status varchar(20) [not null, note: 'available|occupied|maintenance|cleaning|blocked']
  has_balcony boolean [default: false]
  has_sea_view boolean [default: false]
  has_mountain_view boolean [default: false]
  notes text
  last_cleaned_at timestamp
  created_at timestamp [not null]
  updated_at timestamp [not null]
  
  indexes {
    (number, subdivision) [unique]
  }
}

Table room_extra_amenities {
  id integer [primary key]
  room_id integer [not null]
  amenity_id integer [not null]
  
  indexes {
    (room_id, amenity_id) [unique]
  }
}

Table seasonal_prices {
  id integer [primary key]
  category_id integer [not null]
  name varchar(100) [not null]
  start_date date [not null]
  end_date date [not null]
  price_per_night decimal(10,2) [not null]
  min_nights integer [default: 1]
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

Table room_reviews {
  id integer [primary key]
  category_id integer [not null]
  guest_id integer [not null]
  booking_id uuid [not null, unique, note: 'OneToOne']
  rating integer [not null, note: '1-5']
  cleanliness_rating integer
  service_rating integer
  comfort_rating integer
  title varchar(200)
  body text
  is_approved boolean [default: false]
  approved_by_id integer
  approved_at timestamp
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

// ============================================
// BOOKINGS (Бронирования)
// ============================================

Table bookings {
  id uuid [primary key]
  confirmation_number varchar(20) [not null, unique, note: 'ZV-XXXXXXXX']
  guest_id integer
  room_category_id integer [not null]
  room_id integer [note: 'Назначается при заселении']
  group_id uuid [note: 'Группа броней']
  organization_id integer
  guest_first_name varchar(50) [not null]
  guest_last_name varchar(50) [not null]
  guest_patronymic varchar(50)
  guest_phone varchar(30) [not null]
  guest_email varchar(100)
  check_in date [not null]
  check_out date [not null]
  adults integer [not null]
  children integer [default: 0]
  occupancy_type varchar(20) [note: 'solo|newlyweds|friends|two_guests']
  price_per_night decimal(10,2) [not null]
  total_price decimal(10,2) [not null]
  discount_amount decimal(10,2) [default: 0]
  discount_reason varchar(255)
  status varchar(20) [not null, note: 'pending|confirmed|checked_in|checked_out|cancelled|no_show']
  payment_status varchar(20) [not null, note: 'unpaid|partial|paid|refunded|failed']
  source varchar(20) [note: 'website|phone|walk_in|ota|corporate']
  auto_cancel_at timestamp
  special_requests text
  arrival_time time
  departure_time time
  early_check_in boolean [default: false]
  internal_notes text
  created_by_id integer
  cancelled_at timestamp
  cancellation_reason text
  cancelled_by_id integer
  created_at timestamp [not null]
  updated_at timestamp [not null]
  
  indexes {
    (guest_id, status)
    (room_id, check_in, check_out)
    (status, check_in)
  }
}

Table booking_history {
  id integer [primary key]
  booking_id uuid [not null]
  action varchar(30) [not null, note: 'created|confirmed|checked_in|checked_out|cancelled|no_show|payment|note_added|modified|undo_check_in|undo_check_out']
  status_after varchar(20)
  changed_by_id integer
  note text
  snapshot json
  created_at timestamp [not null]
  
  indexes {
    (booking_id, created_at)
  }
}

Table payments {
  id uuid [primary key]
  booking_id uuid [not null]
  amount decimal(10,2) [not null]
  method varchar(20) [not null, note: 'cash|card|transfer|online']
  payment_type varchar(10) [not null, note: 'charge|refund']
  transaction_id varchar(100)
  is_confirmed boolean [default: false]
  confirmed_at timestamp
  processed_by_id integer
  notes text
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

// ============================================
// CRM (Управление клиентами)
// ============================================

Table organizations {
  id integer [primary key]
  name varchar(255) [not null, unique]
  short_name varchar(100)
  org_type varchar(20) [note: 'company|government|ngo|individual']
  inn varchar(12)
  kpp varchar(9)
  ogrn varchar(15)
  legal_address text
  actual_address text
  phone varchar(30)
  email varchar(100)
  website varchar(255)
  contact_person varchar(150)
  corporate_discount_pct decimal(5,2) [default: 0]
  credit_limit decimal(12,2) [default: 0]
  payment_terms_days integer [default: 0]
  assigned_manager_id integer
  notes text
  is_active boolean [default: true]
  is_approved boolean [default: false]
  created_by_user_id integer
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

Table client_profiles {
  id integer [primary key]
  user_id integer [not null, unique, note: 'OneToOne']
  organization_id integer
  client_type varchar(20) [note: 'individual|organization']
  guest_type varchar(20) [note: 'leisure|business|corporate|vip']
  status varchar(20) [default: 'active', note: 'active|vip|inactive|blacklisted']
  loyalty_tier varchar(20) [default: 'standard', note: 'standard|silver|gold|platinum']
  loyalty_points integer [default: 0]
  total_stays integer [default: 0]
  total_nights integer [default: 0]
  total_spent decimal(12,2) [default: 0]
  first_stay_date date
  last_stay_date date
  preferred_room_category_id integer
  preferred_floor integer
  dietary_requirements text
  special_needs text
  assigned_manager_id integer
  vip_notes text
  is_blacklisted boolean [default: false]
  blacklist_reason text
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

Table admin_comments {
  id integer [primary key]
  client_id integer [not null]
  author_id integer [not null]
  body text [not null]
  is_pinned boolean [default: false]
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

Table interactions {
  id integer [primary key]
  client_id integer [not null]
  staff_id integer [not null]
  booking_id uuid
  interaction_type varchar(20) [not null, note: 'call|email|in_person|chat|note|complaint']
  subject varchar(255)
  body text
  outcome varchar(255)
  is_resolved boolean [default: false]
  follow_up_date date
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

Table tasks {
  id integer [primary key]
  title varchar(255) [not null]
  description text
  created_by_id integer [not null]
  assigned_to_id integer
  client_id integer
  booking_id uuid
  priority varchar(10) [default: 'medium', note: 'low|medium|high|urgent']
  status varchar(20) [default: 'open', note: 'open|in_progress|done|cancelled']
  due_date date
  completed_at timestamp
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

Table messages {
  id integer [primary key]
  sender_id integer [not null]
  recipient_id integer [not null]
  booking_id uuid
  client_profile_id integer
  message_type varchar(20) [note: 'inquiry|complaint|request|feedback|internal']
  subject varchar(255)
  body text [not null]
  attachment varchar(255)
  parent_id integer [note: 'Ответ на сообщение']
  status varchar(20) [default: 'unread', note: 'unread|read|replied|archived']
  read_at timestamp
  is_urgent boolean [default: false]
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

// ============================================
// ANALYTICS (Аналитика)
// ============================================

Table daily_metrics {
  id integer [primary key]
  date date [not null, unique]
  total_rooms integer [not null]
  occupied_rooms integer [not null]
  available_rooms integer [not null]
  occupancy_rate decimal(5,2) [not null]
  total_revenue decimal(12,2) [not null]
  adr decimal(10,2) [note: 'Average Daily Rate']
  revpar decimal(10,2) [note: 'Revenue Per Available Room']
  new_bookings integer [default: 0]
  confirmed_bookings integer [default: 0]
  cancelled_bookings integer [default: 0]
  checkins integer [default: 0]
  checkouts integer [default: 0]
  no_shows integer [default: 0]
  total_guests integer [default: 0]
  new_guests integer [default: 0]
  calculated_at timestamp [not null]
}

Table page_views {
  id integer [primary key]
  page_type varchar(30) [note: 'home|room_list|room_detail|booking_form|booking_success|about|contacts|other']
  path varchar(255) [not null]
  referrer varchar(255)
  user_id integer
  session_key varchar(100)
  ip_address varchar(45)
  user_agent text
  room_category_id integer
  viewed_at timestamp [not null]
  
  indexes {
    (page_type, viewed_at)
    (session_key, viewed_at)
  }
}

Table booking_funnel {
  id integer [primary key]
  session_key varchar(100) [not null]
  user_id integer
  stage varchar(20) [not null, note: 'search|room_view|form_open|form_submit|success|abandoned']
  room_category_id integer
  booking_id uuid
  search_check_in date
  search_check_out date
  search_guests integer
  started_at timestamp [not null]
  updated_at timestamp [not null]
  
  indexes {
    (session_key, stage)
  }
}

Table revenue_snapshots {
  id integer [primary key]
  year integer [not null]
  month integer [not null]
  total_revenue decimal(12,2) [not null]
  total_bookings integer [not null]
  total_nights integer [not null]
  avg_occupancy decimal(5,2)
  avg_adr decimal(10,2)
  calculated_at timestamp [not null]
  
  indexes {
    (year, month) [unique]
  }
}

// ============================================
// NOTIFICATIONS (Уведомления)
// ============================================

Table email_logs {
  id integer [primary key]
  recipient_email varchar(100) [not null]
  recipient_name varchar(150)
  recipient_user_id integer
  email_type varchar(30) [not null, note: 'booking_confirmation|booking_cancelled|booking_reminder|booking_checkout|password_reset|welcome|marketing|custom']
  subject varchar(255) [not null]
  body_html text
  body_text text
  booking_id uuid
  status varchar(20) [default: 'pending', note: 'pending|sent|failed|bounced']
  sent_at timestamp
  error_message text
  retry_count integer [default: 0]
  task_id varchar(100)
  created_at timestamp [not null]
  updated_at timestamp [not null]
  
  indexes {
    (recipient_email, created_at)
    (status, created_at)
  }
}

Table notification_templates {
  id integer [primary key]
  email_type varchar(30) [not null, unique]
  name varchar(100) [not null]
  subject varchar(255) [not null]
  body_html text [not null]
  body_text text
  is_active boolean [default: true]
  updated_by_id integer
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

Table push_notifications {
  id integer [primary key]
  recipient_id integer [not null]
  notification_type varchar(30) [note: 'booking_confirmed|booking_cancelled|checkin_reminder|checkout_reminder|loyalty_upgrade|contact_form|system']
  title varchar(255) [not null]
  body text [not null]
  action_url varchar(255)
  booking_id uuid
  is_read boolean [default: false]
  read_at timestamp
  created_at timestamp [not null]
  updated_at timestamp [not null]
  
  indexes {
    (recipient_id, is_read)
  }
}

Table contact_messages {
  id integer [primary key]
  sender_user_id integer
  sender_name varchar(150) [not null]
  sender_email varchar(100) [not null]
  sender_phone varchar(30)
  subject varchar(255) [not null]
  message text [not null]
  status varchar(20) [default: 'new', note: 'new|in_work|answered|closed']
  assigned_to_id integer
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

Table contact_replies {
  id integer [primary key]
  message_id integer [not null]
  author_id integer [not null]
  body text [not null]
  is_staff_reply boolean [default: false]
  is_read_by_guest boolean [default: false]
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

// ============================================
// CONTENT (Контент сайта)
// ============================================

Table site_content {
  id integer [primary key]
  key varchar(100) [not null, unique]
  label varchar(255) [not null]
  content_type varchar(20) [not null, note: 'text|html|image|url']
  value_text text
  value_image varchar(255)
  is_active boolean [default: true]
  updated_by_id integer
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

Table faqs {
  id integer [primary key]
  question varchar(255) [not null]
  answer text [not null]
  category varchar(20) [note: 'booking|checkin|services|payment|general']
  is_active boolean [default: true]
  sort_order integer [default: 0]
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

Table hotel_gallery {
  id integer [primary key]
  image varchar(255) [not null]
  title varchar(255)
  alt_text varchar(255)
  section varchar(20) [note: 'exterior|lobby|restaurant|spa|pool|conference|territory|other']
  is_active boolean [default: true]
  is_featured boolean [default: false]
  sort_order integer [default: 0]
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

Table testimonials {
  id integer [primary key]
  user_id integer
  author_name varchar(150) [not null]
  author_title varchar(100)
  author_avatar varchar(255)
  text text [not null]
  rating integer [note: '1-5']
  is_active boolean [default: true]
  source varchar(50)
  sort_order integer [default: 0]
  created_at timestamp [not null]
  updated_at timestamp [not null]
}

// ============================================
// СВЯЗИ (Relationships)
// ============================================

// User relationships
Ref: bookings.guest_id > users.id
Ref: bookings.created_by_id > users.id
Ref: bookings.cancelled_by_id > users.id
Ref: booking_history.changed_by_id > users.id
Ref: payments.processed_by_id > users.id
Ref: room_reviews.guest_id > users.id
Ref: room_reviews.approved_by_id > users.id
Ref: client_profiles.user_id - users.id [note: 'OneToOne']
Ref: organizations.assigned_manager_id > users.id
Ref: organizations.created_by_user_id > users.id
Ref: client_profiles.assigned_manager_id > users.id
Ref: admin_comments.author_id > users.id
Ref: interactions.staff_id > users.id
Ref: tasks.created_by_id > users.id
Ref: tasks.assigned_to_id > users.id
Ref: messages.sender_id > users.id
Ref: messages.recipient_id > users.id
Ref: email_logs.recipient_user_id > users.id
Ref: notification_templates.updated_by_id > users.id
Ref: push_notifications.recipient_id > users.id
Ref: contact_messages.sender_user_id > users.id
Ref: contact_messages.assigned_to_id > users.id
Ref: contact_replies.author_id > users.id
Ref: site_content.updated_by_id > users.id
Ref: testimonials.user_id > users.id
Ref: page_views.user_id > users.id
Ref: booking_funnel.user_id > users.id

// Hotel relationships
Ref: room_category_amenities.room_category_id > room_categories.id
Ref: room_category_amenities.amenity_id > amenities.id
Ref: room_images.category_id > room_categories.id
Ref: rooms.category_id > room_categories.id
Ref: room_extra_amenities.room_id > rooms.id
Ref: room_extra_amenities.amenity_id > amenities.id
Ref: seasonal_prices.category_id > room_categories.id
Ref: room_reviews.category_id > room_categories.id
Ref: client_profiles.preferred_room_category_id > room_categories.id
Ref: page_views.room_category_id > room_categories.id
Ref: booking_funnel.room_category_id > room_categories.id

// Booking relationships
Ref: bookings.room_category_id > room_categories.id
Ref: bookings.room_id > rooms.id
Ref: bookings.organization_id > organizations.id
Ref: booking_history.booking_id > bookings.id
Ref: payments.booking_id > bookings.id
Ref: room_reviews.booking_id - bookings.id [note: 'OneToOne']
Ref: interactions.booking_id > bookings.id
Ref: tasks.booking_id > bookings.id
Ref: messages.booking_id > bookings.id
Ref: email_logs.booking_id > bookings.id
Ref: push_notifications.booking_id > bookings.id
Ref: booking_funnel.booking_id > bookings.id

// CRM relationships
Ref: client_profiles.organization_id > organizations.id
Ref: admin_comments.client_id > client_profiles.id
Ref: interactions.client_id > client_profiles.id
Ref: tasks.client_id > client_profiles.id
Ref: messages.client_profile_id > client_profiles.id

// Message relationships
Ref: messages.parent_id > messages.id
Ref: contact_replies.message_id > contact_messages.id
```

## Примеры данных (Records)

```dbml
// Роли пользователей
Records users(id, email, role, first_name, last_name, is_active, is_staff, created_at) {
  1, 'admin@zoryvakha.ru', 'super_admin', 'Админ', 'Системный', true, true, '2026-01-01 00:00:00'
  2, 'manager@zoryvakha.ru', 'manager', 'Менеджер', 'Главный', true, true, '2026-01-01 00:00:00'
  3, 'receptionist@zoryvakha.ru', 'receptionist', 'Администратор', 'Стойки', true, true, '2026-01-01 00:00:00'
  4, 'guest1@example.com', 'user', 'Иван', 'Иванов', true, false, '2026-01-02 10:00:00'
  5, 'guest2@example.com', 'user', 'Петр', 'Петров', true, false, '2026-01-02 11:00:00'
}

// Удобства
Records amenities(id, name, category, is_highlighted, sort_order) {
  1, 'Wi-Fi', 'tech', true, 1
  2, 'Кондиционер', 'comfort', true, 2
  3, 'Телевизор', 'tech', false, 3
  4, 'Мини-бар', 'food', false, 4
  5, 'Сейф', 'comfort', false, 5
}

// Категории номеров
Records room_categories(id, name, slug, max_guests, bed_type, base_price_per_night, is_active) {
  1, 'Стандарт', 'standard', 2, 'double', 3500.00, true
  2, 'Делюкс', 'deluxe', 3, 'king', 5000.00, true
  3, 'Люкс', 'suite', 4, 'king', 8000.00, true
}

// Номера
Records rooms(id, category_id, number, subdivision, floor, max_guests_per_room, status) {
  1, 1, '101', NULL, 1, 2, 'available'
  2, 1, '102', NULL, 1, 2, 'available'
  3, 2, '201', NULL, 2, 3, 'available'
  4, 3, '303', 'а', 3, 2, 'available'
  5, 3, '303', 'б', 3, 2, 'available'
}

// Организации
Records organizations(id, name, org_type, corporate_discount_pct, is_active, is_approved) {
  1, 'ООО "Рога и Копыта"', 'company', 10.00, true, true
  2, 'ИП Иванов И.И.', 'individual', 5.00, true, true
}

// Бронирования
Records bookings(id, confirmation_number, guest_id, room_category_id, guest_first_name, guest_last_name, guest_phone, check_in, check_out, adults, total_price, status, payment_status, source) {
  '550e8400-e29b-41d4-a716-446655440001', 'ZV-20260320', 4, 1, 'Иван', 'Иванов', '+79990001122', '2026-03-20', '2026-03-23', 2, 10500.00, 'confirmed', 'paid', 'website'
  '550e8400-e29b-41d4-a716-446655440002', 'ZV-20260401', 5, 3, 'Петр', 'Петров', '+79990003344', '2026-04-01', '2026-04-05', 2, 32000.00, 'confirmed', 'partial', 'phone'
}
```

## Визуализация

Скопируйте весь DBML код выше и вставьте на сайт:
**https://dbdiagram.io/d**

Вы получите интерактивную диаграмму со всеми связями!

---

**Всего таблиц:** 35  
**Модулей:** 7 (Accounts, Hotel, Bookings, CRM, Analytics, Notifications, Content)  
**Дата создания:** Май 2026
