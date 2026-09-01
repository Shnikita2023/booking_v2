# Booking API

REST API для бронирования и продажи билетов на мероприятия (SDD-подход). MVP-версия: шаги 1–9 реализованы.

## Стек

- **Python 3.12** + FastAPI (REST API)
- **PostgreSQL 16** (Docker Compose)
- **SQLAlchemy 2** (async) + Alembic (миграции)
- **Pydantic v2** (схемы + валидация)
- **JWT** (access + refresh) + Argon2 (хеши паролей)
- **uvloop** + **APScheduler** (очистка броней)

## Быстрый старт

```bash
# 1. Клонируем
git clone git@github.com:Shnikita2023/booking_v2.git
cd booking_v2

# 2. Создаём .env из примера
cp .env.example .env

# 3. Запускаем (PostgreSQL + API + Worker)
docker compose up --build -d

# 4. Миграции (автоматически при старте API)
# Или вручную:
docker compose exec api alembic upgrade head

# 5. Swagger-документация
open http://localhost:8000/docs
```

## Конфигурация (.env)

| Переменная | Описание | По умолчанию |
|---|---|---|
| `APP_ENV` | `dev` / `prod` | `dev` |
| `DATABASE_URL` | URL подключения к PostgreSQL | `postgresql+asyncpg://booking:booking@db:5432/booking` |
| `JWT_SECRET` | Секрет для подписи JWT | `change-me` |
| `WEBHOOK_SECRET` | Секрет для верификации webhook'ов | `webhook-change-me` |
| `ACCESS_TTL_MIN` | Время жизни access-токена (мин) | `15` |
| `REFRESH_TTL_DAYS` | Время жизни refresh-токена (дни) | `14` |
| `RESERVATION_TTL_MIN` | Время жизни брони до отмены (мин) | `15` |
| `POSTGRES_PORT` | Порт PostgreSQL | `5432` |
| `API_PORT` | Порт API | `8000` |

> В режиме `prod` **обязательно** задать `JWT_SECRET` и `WEBHOOK_SECRET` (≥32 символа).

## Архитектура

```
src/booking/
├── core/          # Конфиг, DI, ошибки, логирование, rate-limiting
├── models/        # SQLAlchemy-модели (User, Client, Event, Order, Ticket, Payment, Discount, AuditLog)
├── schemas/       # Pydantic-схемы (request/response)
├── repositories/  # Доступ к данным (async SQLAlchemy)
├── services/      # Бизнес-логика (auth, orders, discounts, reports)
├── integrations/  # Внешние сервисы (платежи, email)
├── routers/       # HTTP-эндпоинты (transport layer)
│   ├── admin/     # Админ-панель (EVENTS, MANAGER, ADMIN)
│   ├── client/    # Клиентские эндпоинты (CLIENT)
│   ├── staff_panel/ # Кассир + отчёты (CASHIER, MANAGER, ADMIN)
│   └── public/    # Публичные (webhook)
└── worker/        # Фоновый воркер (очистка броней)
```

## Роли

| Роль | Описание | Доступ |
|---|---|---|
| `ADMIN` | Полный доступ | Всё |
| `MANAGER` | Управление мероприятиями + клиентами + персонал | Админ-API (мероприятия, клиенты, персонал) |
| `CASHIER` | Продажа/возврат билетов на кассе | Кассир-панель |
| `CLIENT` | Бронирование и оплата билетов | Клиентский профиль, заказы, оплата |

## API-эндпоинты

### Авторизация
- `POST /api/v1/auth/client/register` — регистрация клиента
- `POST /api/v1/auth/client/login` — вход клиента
- `POST /api/v1/auth/staff/login` — вход персонала
- `POST /api/v1/auth/refresh` — обновление токена
- `POST /api/v1/auth/logout` — выход

### Мероприятия (публичные)
- `GET /api/v1/events` — каталог мероприятий
- `GET /api/v1/events/{id}` — детали мероприятия

### Клиент
- `GET /api/v1/client/profile` — мой профиль
- `PUT /api/v1/client/profile` — обновить профиль
- `POST /api/v1/orders` — создать бронь
- `GET /api/v1/orders` — мои заказы
- `POST /api/v1/orders/{id}/pay` — оплатить заказ
- `POST /api/v1/orders/{id}/refund` — вернуть заказ

### Кассир
- `POST /api/v1/staff/orders` — продажа билетов (сразу оплата)
- `POST /api/v1/staff/orders/{id}/refund` — возврат
- `POST /api/v1/staff/orders/{id}/cancel` — отмена брони
- `GET /api/v1/staff/orders` — список всех заказов

### Отчёты
- `GET /api/v1/staff/reports/revenue` — выручка по мероприятиям
- `GET /api/v1/staff/reports/revenue-by-date` — выручка по дням
- `GET /api/v1/staff/reports/sales` — продажи по статусам
- `GET /api/v1/staff/reports/occupancy` — загрузка мероприятий
- `GET /api/v1/staff/reports/top-clients` — лучшие клиенты
- `GET /api/v1/staff/reports/audit-stats` — статистика аудита

### Админ-панель
- `GET/POST /api/v1/admin/events` — управление мероприятиями
- `GET/POST /api/v1/admin/clients` — управление клиентами
- `GET/POST /api/v1/admin/users` — управление персоналом
- `GET/POST /api/v1/admin/discounts` — управление скидками
- `GET /api/v1/admin/audit` — журнал аудита
- `GET/PUT /api/v1/admin/settings` — настройки системы

### Webhook
- `POST /api/v1/payments/webhook` — callback от платёжной системы (HMAC-SHA256)
- `POST /api/v1/payments/mock-confirm` — тестовое подтверждение оплаты (dev)

## Доступ

| Сервис | URL |
|---|---|
| API | `http://localhost:8000` |
| Swagger | `http://localhost:8000/docs` |
| PostgreSQL | `localhost:5432` |

## Тесты

```bash
# Сборка тестов
pytest --collect-only

# Запуск (требуется Docker для testcontainers)
pytest -v

# Линтер
ruff check src/ tests/

# Типизация
mypy src/booking/ --strict
```

## Миграции

```bash
# Применить все миграции
alembic upgrade head

# Создать новую миграцию
alembic revision --autogenerate -m "description"
```

## Лицензия

Proprietary — внутренний проект.
