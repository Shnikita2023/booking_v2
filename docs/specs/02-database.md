# Spec 02: Фундамент БД + срез таблиц для Auth (пересмотрен)

Статус: **ПЕРЕСМОТРЕН — инкрементальная реализация** (был big-bang)
Реализует: D-1 (soft-delete), инфраструктуру миграций, срез данных для шага 3 (Auth).

> **Принцип после пересмотра:** полная схема БД — проектная документация,
> но каждая таблица рождается в том шаге, где впервые нужна, со своей
> миграцией. Каждый шаг доставляет работающий срез и проверяется запуском.

## 1. Цель шага

Инфраструктура данных + первая миграция с таблицами, необходимыми шагу 3:
`roles`, `system_users`, `clients`.

## 2. Слои (Clean Architecture)

```
src/booking/
├── db/                  # движок, сессии                       [есть]
├── models/              # ORM-модели: base.py + по агрегату
├── repositories/        # доступ к данным: base.py (generic CRUD)
└── services/            # бизнес-логика (каркас)
```

Правила: репозиторий без бизнес-логики; сервис не знает про HTTP;
роутер не ходит в БД напрямую; зависимости через DI.

## 3. Требования

| ID | Требование |
|----|-----------|
| DB-1 | Никаких физических удалений: `deleted_at` у доменных таблиц, чтение фильтрует удалённые |
| DB-2 | Изменяемые записи: `version`; история — решение ADR-002 (позже) |
| DB-3 | Миграции только через Alembic, forward-only |
| DB-4 | Все таблицы: `id UUID PK`, `created_at`, `updated_at` |
| DB-5 | Деньги `NUMERIC(12,2)`, даты `TIMESTAMPTZ` |

## 4. Модель данных этого шага

### roles
`code UNIQUE` (admin/manager/cashier), `name`

### system_users
`email UNIQUE`, `password_hash`, `full_name?`, `role_id FK→roles`,
`is_active`, `failed_attempts` (lockout D-4), `locked_until` (D-4),
`active_session_id` (одна сессия D-5)

### clients
`email UNIQUE`, `password_hash`, `phone?`, `full_name?`,
`discount_percent`, `special_conditions?`, `version`

Общие миксины: UUID PK, created_at/updated_at, deleted_at (soft-delete).

## 5. Проектная модель данных (реализуется по шагам)

| Таблица | Шаг |
|---|---|
| roles, system_users, clients | **02 (этот)** |
| events, ticket_types, info_pages | 04 |
| orders, tickets, payments | 05 |
| discounts | 06 |
| audit_log (+партиции по годам) | 07 |

Ключевые ограничения будущих таблиц: tickets UNIQUE(ticket_type_id, seat) +
TTL-резерв; payments idempotency_key UNIQUE; audit_log append-only.

## 6. Задачи

- [x] `models/base.py`: Base(UUID PK, timestamps) + SoftDeleteMixin + VersionedMixin
- [x] Модели Role, SystemUser, Client
- [x] Alembic: alembic.ini, env.py (async), script.py.mako
- [ ] Миграция `0001`: roles, system_users, clients
- [x] `repositories/base.py`: generic CRUD с soft-delete фильтром и version++
- [ ] Каркас services/
- [ ] Тесты против реального Postgres: миграция, CRUD, soft-delete фильтр

## 7. Критерии приёмки

1. `alembic upgrade head` на чистой БД — без ошибок.
2. `downgrade base && upgrade head` — воспроизводимо.
3. pytest против реального Postgres: create/get/update/soft_delete — зелёные.
4. ruff + mypy strict = 0 ошибок.

## 8. Вне рамок шага

Auth-логика (шаг 3), остальные таблицы (шаги 4–7), API-эндпоинты.
