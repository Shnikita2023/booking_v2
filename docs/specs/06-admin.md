# Спек 06 — Админ-API (мероприятия, клиенты, настройки)

**Шаг:** 6 · **Статус:** на реализации
**Покрывает ТЗ:** S-2 (управление мероприятиями), S-3 (управление клиентами и
пользователями системы), S-8 (настройки системы).
**Не входит (отложено):** S-4 (скидки/тарифы/акции) — отдельный шаг; D-9
(модуль обмена данными) — post-MVP.

## Контекст
Ядро MVP готово (шаги 1–5): клиент может смотреть афишу и бронировать билеты.
Сейчас нет инструмента управления контентом и пользователями со стороны
персонала. Шаг 6 закрывает админ-часть: создание/редактирование мероприятий и
тарифов, управление клиентами и персоналом, системные настройки.

## Решения (зафиксированы)
- **Цена мероприятия** — только производная от тарифов (`EventService.sync_price`);
  поле `price` админом не задаётся и не редактируется напрямую.
- **`system_settings`** — `value` хранится как JSON; на этом шаге только
  сохраняется/читается (без привязки к runtime-логике).
- **Блокировка персонала** — `SystemUser.is_active = False` (плюс сброс
  `active_session_id`); разблок — `is_active = True`.
- **Жизненный цикл мероприятия** — все действия: `publish`, `pause-sales`,
  `resume-sales`, `move`, `cancel`, `complete`, плюс `clone`.
- **Доступ (RBAC):** мероприятия и клиенты → `ADMIN` + `MANAGER`; персонал и
  настройки → только `ADMIN` (через `require_role`).

## Требования

### S-2 — Мероприятия
- `POST /api/v1/admin/events` — создать черновик (`status=DRAFT`); поля:
  `title, description, starts_at, duration_min, age_rating, venue,
  banner_small_url, banner_large_url, show_free_tickets, sale_paused`, опц.
  `ticket_types: [{name, price, quota}]`. `price` не передаётся.
- `GET /api/v1/admin/events` — список всех статусов (пагинация).
- `GET /api/v1/admin/events/{id}` — карточка (любой статус).
- `PATCH /api/v1/admin/events/{id}` — редактирование перечисленных полей
  (кроме `status` и `price`).
- Действия (только смена статуса/флагов, без редактирования полей):
  - `POST …/publish` → `ON_SALE`;
  - `POST …/pause-sales` → `sale_paused=True`;
  - `POST …/resume-sales` → `sale_paused=False`;
  - `POST …/move` (body `starts_at`) → `MOVED` + новое `starts_at`;
  - `POST …/cancel` → `CANCELLED`;
  - `POST …/complete` → `COMPLETED`;
  - `POST …/clone` → копия полей и тарифов (`sold=0`), `status=DRAFT`,
    `cloned_from_id` = исходный id.
- Тарифы (вложены в мероприятие):
  - `POST /api/v1/admin/events/{event_id}/ticket-types` → `{name, price, quota}`;
  - `PATCH /api/v1/admin/ticket-types/{id}` → редактирование `name/price/quota`
    с guard `quota >= sold` (иначе 409);
  - `DELETE /api/v1/admin/ticket-types/{id}` — soft-delete; при `sold > 0` → 409;
  - `GET /api/v1/admin/events/{event_id}/ticket-types` — список.
- После любого изменения тарифов — пересчёт `Event.price` через `sync_price`.

### S-3 — Клиенты и персонал
- Клиенты (`ADMIN`+`MANAGER`):
  - `GET/POST /api/v1/admin/clients` — список (пагинация) / создание
    (`email, password, phone?, full_name?, discount_percent, special_conditions`);
  - `GET/PATCH /api/v1/admin/clients/{id}` — карточка / редактирование;
  - `POST …/reset-password` (body `password`);
  - `POST …/block` → `locked_until` в далёкое будущее + сброс `failed_attempts`;
  - `POST …/unblock` → очистить `locked_until`/`failed_attempts`;
  - `DELETE /api/v1/admin/clients/{id}` — soft-delete (D-1).
- Персонал (`ADMIN`):
  - `GET/POST /api/v1/admin/users` — список / создание
    (`email, password, full_name?, role_code`);
  - `GET/PATCH /api/v1/admin/users/{id}` — карточка / редактирование
    (`full_name, role_code, is_active`);
  - `POST …/reset-password`;
  - `POST …/block` → `is_active=False` (+ сброс `active_session_id`);
  - `POST …/unblock` → `is_active=True`;
  - `DELETE /api/v1/admin/users/{id}` — soft-delete.

### S-8 — Настройки
- `GET /api/v1/admin/settings` — список всех ключей.
- `GET /api/v1/admin/settings/{key}` — значение ключа (404, если нет).
- `PUT /api/v1/admin/settings/{key}` (body `value`, опц. `description`) —
  upsert; `value` — произвольный JSON.

## Модель данных
- Новая таблица `system_settings(key PK str, value JSONB, description text,
  updated_by uuid nullable, …TimestampMixin)`.
- Остальные модели (`Event`, `TicketType`, `Client`, `SystemUser`, `Role`)
  уже существуют — новых колонок не требуется.

## Критерии приёмки
- Все эндпоинты задекларированы с `summary`, `description`, `response_model`.
- RBAC: не-админ (client) и неподходящая роль → 403; аноним → 401.
- Нельзя задать `price` мероприятия вручную — оно всегда из тарифов.
- Удаление тарифа с `sold>0` → 409; иначе soft-delete и `sync_price`.
- `clone` не копирует проданные билеты (`sold=0`), статус DRAFT.
- Блокировка персонала делает вход невозможным (`is_active=False`).
- `system_settings.value` корректно сохраняет/возвращает JSON (round-trip).
- `ruff` + `mypy strict` = 0 ошибок; тесты (testcontainers, Postgres 16) зелёные.

## Тесты (минимум)
- `test_admin_events.py`: CRUD, guard квоты, clone, pause/resume, move,
  статус-машина, запрет ручного `price`.
- `test_admin_clients.py`: CRUD, reset-password, block/unblock, soft-delete.
- `test_admin_users.py`: CRUD, создание с ролью, block/unblock, soft-delete.
- `test_admin_settings.py`: set/get/list, JSON round-trip, 404 на отсутствующий ключ.
- `test_admin_rbac.py` (или внутри перечисленных): 403 для client / неподходящей роли.
