# Прогресс проекта Booking v2

> Краткий статус для команды: что сделано, что на утверждении, что дальше.
> Обновляется после каждого закрытого шага.
> Процесс: SDD — спек → утверждение → реализация → верификация.

**Дата обновления:** 2026-08-28
**Статус:** Шаг 7 завершён ✅ · следующий — платежи/рассылка (шаг 8)
**Репозиторий:** github.com/Shnikita2023/booking_v2 (SSH, ветка master)

---

## Как работаем (процесс)

1. LLM пишет спек шага (`docs/specs/NN-*.md`) — требования, задачи, критерии приёмки.
2. Заказчик утверждает спек (или возвращает правки).
3. Реализация строго по чек-листу спека.
4. Верификация запуском: lint + mypy + pytest + docker compose + curl.
5. Результаты проверки фиксируются здесь → переход к следующему спеку.

Ключевые документы: `docs/00-vision.md` (трассировка ТЗ), `docs/specs/*`.

## Зафиксированные решения

| Решение | Обоснование |
|---|---|
| Python 3.12 + FastAPI, только REST API | выбор заказчика; фронт отдельно |
| PostgreSQL 16 в Docker | по ТЗ; docker-compose с healthcheck |
| uniPayment → mock/sandbox | решение заказчика |
| MVP = ядро (клиент + мероприятия + заказы) | решение заказчика |
| Soft-delete + audit-log вместо удаления | требование ТЗ «данные не удаляются» |
| JWT access+refresh, lockout 3→30 мин, одна сессия | требования ТЗ D-4/D-5 |

## Правила кода (обязательны)

- Архитектура: SOLID + Clean Architecture. Слои строго разделены:
  `routers` (транспорт) → `services` (бизнес-логика) → `repositories`
  (доступ к данным) → `models/db`. Роутеры не ходят в БД напрямую,
  репозитории не содержат бизнес-логики; зависимости — через DI.
- Импорты — только в начале файла; импорты внутри функций/классов запрещены
  (enforced: ruff `PLC0415` в `pyproject.toml`).
- Async-тесты и async-fixtures — без декораторов `pytest_asyncio.*`;
  включён `asyncio_mode = "auto"` в `pyproject.toml`, используется обычный `@pytest.fixture`.
- **Зависимости в роутерах — через `Annotated`-алиасы**, не `param = Depends(...)`:
  общие алиасы объявляются в `core/deps.py` (`SessionDep`, `CurrentPrincipal`,
  `EngineDep`); для RBAC — `Annotated[Principal, Depends(require_role(...))]`.
- **Деньги — только `Decimal` / `NUMERIC`**: в PostgreSQL `NUMERIC(12,2)`,
  в Python исключительно `Decimal` (`float` запрещён), в Pydantic-схемах API —
  тоже `Decimal`. Требование DB-5 из спека 02.
- **Время — только UTC и только timezone-aware**: в Python исключительно
  `datetime.now(UTC)` (без аргумента или `utcnow()` запрещены); в БД —
  только `TIMESTAMPTZ` / `DateTime(timezone=True)`; API отдаёт ISO-8601 c offset.
- **Тесты — только на testcontainers**: интеграционные тесты гоняются против
  реального Postgres 16 (`testcontainers[postgres]`), поднимаемого автоматически;
  sqlite-моки и ручные тестовые БД не используются.
  Все async-тесты и фикстуры выполняются в одном session-scoped event loop
  (`asyncio_default_*_loop_scope = "session"`).
- **Каждый эндпоинт роутера обязан декларировать** `summary`, `description` и
  `response_model` (явно; для 204/raw-ответов — `response_model=None`). Это
  делает OpenAPI-документацию полной и единообразной.
- **Докстринги, а не комментарии**: где нужно — модульные/методные docstring-и
  (роутеры, сервисы, ключевые функции); лишние inline-комментарии убираются,
  код должен быть самодокументируемым.
- **HTTP-статусы — только именованные константы** из `fastapi.status`
  (напр. `status.HTTP_404_NOT_FOUND`, `status.HTTP_409_CONFLICT`); числовые
  литералы статус-кодов запрещены.
- **uvloop** подключён как зависимость проекта (`uvloop>=0.19`) и принудительно
  включается для тестов в `tests/conftest.py`
  (`asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())`); uvicorn при
  `loop="auto"` тоже использует uvloop при наличии пакета.
- **Инкрементальная схема БД**: полная модель данных живёт в спеке как проектная
  документация, но каждая таблица создаётся миграцией того шага, где впервые нужна.
  Порядок: roles/system_users/clients (02) → events/ticket_types/info_pages (04) →
   orders/tickets/payments (05) → discounts (06) → audit_log (07, физические
   партиции по годам — отдельным шагом позже, таблица сделана append-only, чтобы
   партиции можно было накатить пересозданием).

## Статус шагов

| # | Шаг | Спек | Статус | Верификация |
|---|-----|------|--------|-------------|
| 0 | Vision / декомпозиция ТЗ | `00-vision.md` | ✅ принят | — |
| 1 | Каркас: Docker, FastAPI, /health, CI-скрипты | `01-scaffolding.md` | ✅ принят и реализован | все критерии пройдены |
| 2 | Фундамент БД + срез Auth-таблиц (инкремент) | `02-database.md` | ✅ принят (пересмотрен) и реализован | все критерии пройдены |
| 3 | Auth + RBAC + сессии + lockout | `03-auth.md` | ✅ принят и реализован | все критерии пройдены |
| 4 | Публичное API (афиша, мероприятие, справка) | `04-public-api.md` | ✅ принят и реализован | все критерии пройдены |
| 5 | Заказы и билеты (TTL-резерв, отмена) | `05-orders.md` | ✅ принят и реализован | все критерии пройдены |
| 6 | Админ-API (мероприятия, клиенты, настройки) | `06-admin.md` | ✅ принят и реализован | все критерии пройдены |
| 7 | Audit-лог + информирование о системе | `07-audit.md` | ✅ принят и реализован | все критерии пройдены |
| 8 | Платежи (mock uniPayment) + рассылка писем | `08-payments.md` | ⬜ | — |
| 9 | Отчёты (статистика/бухгалтерия) | `09-reports.md` | ⬜ | — |

## Журнал верификаций

### Шаг 7 — audit-лог + информирование о системе (2026-08-28)
- Спек `07-audit.md` реализован строго по чек-листу (D-2/D-3/S-7/NF-5):
  - Модель `AuditLog` (`models/audit.py`) — append-only (без update/delete в
    репозитории), поля: `actor_type` (UserType|None), `actor_id`,
    `actor_role` (RoleCode, только для SYSTEM_USER), `action` (Enum
    `AuditAction`), `entity_type`, `entity_id`, `payload` (JSONB), `created_at`
    (UTC, Python-side дефолт). Индексы: actor_type, actor_id, action,
    created_at, entity_type, composite(entity_type, entity_id).
    Миграция `0008_audit_log` (upgrade/downgrade ок).
  - `AuditRepository.search` — фильтры по actor/action/entity/датам + пагинация,
    сортировка `created_at DESC`.
  - `AuditService.record`/`search` — запись актора берётся из `Principal`
    (None для анонимных событий, напр. неудачный логин); payload
    автоматически приводится к JSON-safe (UUID/datetime/Enum → примитивы),
    чтобы asyncpg не падал на сериализации.
  - Хуки аудита добавлены во все мутирующие сервисы с параметром
    `actor: Principal | None = None`: `EventAdminService` (create/update/
    publish/cancel/complete/pause/resume/move/clone/CRUD тарифов),
    `ClientAdminService`, `SystemUserAdminService`, `SettingsService.set`,
    `OrderService` (reserve/confirm/cancel/cleanup), `AuthService`
    (register/login успех+неудача/logout). Роутеры прокидывают `_principal`.
  - `GET /api/v1/admin/audit` (только ADMIN) — фильтры (action, actor_type,
    actor_id, actor_role, entity_type, entity_id, from_at, to_at) + пагинация,
    `response_model=AuditListResponse`. «Информирование о системе» ограничено
    журналом событий (по решению заказчика); ошибки/состояние — через
    существующий `/health` и структурированные логи.
  - Физическое годовое партиционирование отложено отдельным шагом (таблица
    append-only, партиции накатываются пересозданием).
- Тесты (testcontainers, Postgres 16): 5 новых — поиск/фильтрация/сортировка
  репозитория, аудит создания мероприятия (актор=admin), аудит брони клиентом
  (актор=client), аудит неудачного логина (актор=None), RBAC журнала
  (client→403, без токена→401). Всего 45 passed ✅
- ruff + mypy strict = 0 ошибок ✅

### Шаг 6 — админ-API (мероприятия, клиенты, персонал, настройки) (2026-08-28)
- Спек `06-admin.md` написан и реализован строго по чек-листу (S-2/S-3/S-8):
  - S-2 мероприятия: CRUD + жизненный цикл (publish/on_sale, cancel, complete,
    pause-sales, resume-sales, move→MOVED) + clone (копия полей и тарифов, sold=0,
    status=DRAFT, cloned_from_id) + управление тарифами (create/update/delete с
    guard `quota >= sold`, 409 при нарушении и при delete с продажами).
    `Event.price` пересчитывается из тарифов через `EventRepository.active_min_price`
    (источник истины — `TicketType.price`).
  - S-3 клиенты (ADMIN+MANAGER): create/list/get/update/reset-password/block
    (is_active=False)/unblock/soft-delete. Добавлено поле `clients.is_active`
    (миграция 0007).
  - S-8 персонал (только ADMIN): create переиспользует логику `cli.create_staff`
    (seeds роль при отсутствии), list/get/update(full_name, role_code, is_active)/
    reset-password/block/soft-delete. Настройки (только ADMIN): list/get/set,
    `system_settings.value` — JSONB, пока только хранение (миграция 0006).
- RBAC через `require_role(RoleCode.*)` в `core/deps.py`; эндпоинты несут
  `summary`/`description`/`response_model`, статусы — константы `fastapi.status`
  (enforced в правилах кода). DTO-мапперы вынесены в фабрики-методы схем
  (`EventRead.from_event`, `UserRead.from_user` и т.п.).
- Ловушка async-SQLAlchemy: после `commit` объект с server-side колонками
  (`updated_at`) не догружался вне сессии (MissingGreenlet) — `TimestampMixin`
  переведён на Python-side UTC-дефолты (`default=lambda: datetime.now(UTC)`,
  `onupdate=...`), чтобы значения жили в объекте. У `SystemUser.role` после смены
  `role_id` в той же сессии relationship кэшировался старым — в `update` добавлен
  `await session.refresh(user, ["role"])` перед возвратом.
- Тесты (testcontainers, Postgres 16): 9 новых — CRUD мероприятий, жизненный цикл,
  clone, guard квоты тарифов (409), RBAC (403 для client/manager на /users, 401 без
  токена), CRUD клиентов, CRUD персонала, JSON-round-trip настроек.
  Всего 40 passed ✅
- ruff + mypy strict = 0 ошибок ✅

### Шаг 5 — Заказы и билеты (2026-08-27)
- Решение по цене мероприятия (утверждено ранее, B/C): `Event.price` —
  витринная «цена от», пересчитывается из `TicketType` через
  `EventService.sync_price` (источник истины — `TicketType.price`).
- Таблицы (миграция 0004): `ticket_types.sold` (+), `orders`, `tickets`,
  `payments`. `alembic upgrade head` / `downgrade base` на живой БД —
  воспроизводимо ✅
- Модель: квотная (без мест). Резерв берёт строку `ticket_types` под
  `SELECT … FOR UPDATE` (row-lock) — атомарная проверка `sold + qty <= quota`,
  инкремент `sold`. Конкурентный перерасход квоты невозможен (тест).
- Статусная машина заказа: `RESERVED → PAID` (заглушка оплаты, шаг 8 —
  реальный uniPayment), `RESERVED/CANCELLED` по отмене или истечении TTL (15 мин,
  `RESERVATION_TTL_MINUTES`). Отмена оплаченного в шаге 5 запрещена.
- Фоновая задача приложения (lifespan) раз в 60с чистит просроченные брони
  (`OrderService.cleanup_expired`), освобождая квоту.
- `EventService.count_free_tickets` теперь реальный: `SUM(quota − sold)` по
  активным тарифам (раньше возвращал `null` до появления таблицы tickets).
- Тесты (testcontainers, Postgres 16): 7 новых — бронь уменьшает free_tickets,
  sold_out (409), оплата + запрет отмены оплаченного, отмена освобождает квоту,
  cleanup_expired, конкурентный резерв (10 параллельных, ровно 5 успехов из
  квоты 5, перерасход 0). Всего 28 passed ✅
- ruff + mypy strict = 0 ошибок ✅
- End-to-end curl на живом стеке отложен: образ `api` собран 22ч назад (нет
  роутера заказов), пересборка невозможна (корпоративный индекс nexus недоступен,
  см. риски). Поведение покрыто интеграционными тестами на реальном Postgres.

### Шаг 5 (доработка) — надёжная очистка просроченных броней (2026-08-27)
- Вынесена очистка из API в **отдельный воркер** (`src/booking/worker.py`) под
  **APScheduler** (`AsyncIOScheduler`, интервал 60с, `max_instances=1`); запуск
  `python -m booking.worker` или `python -m booking.cli cleanup-worker`.
  API-процесс больше не держит фоновую задачу (убран `lifespan` в `main.py`) —
  event loop освобождён, нагрузка не дублируется по 5 репликам.
- Высвобождение квоты сделано корректным при любом числе воркеров и для
  любого чередования кода: строка `orders` блокируется при списании
  (`list_expired` — `SELECT … FOR UPDATE SKIP LOCKED`; `cancel` грузит заказ
  `FOR UPDATE`). Каждый заказ обрабатывает ровно одна транзакция, списание
  идемпотентно (`if status != RESERVED: continue` / повторная проверка под
  блокировкой). Закрыт race cleanup↔cleanup И cleanup↔cancel (был и при
  одном воркере). `pg_advisory_xact_lock` не нужен и убран. Покрыто тестами
  `test_concurrent_cleanup_no_double_release` и
  `test_cleanup_vs_cancel_no_double_release`.
- Миграция `0005`: индекс `ix_orders_status_reserved_until` для быстрого скана
  просроченных (upgrade/downgrade проверены на живой БД).
- `OrderService.__init__(session, settings=None)` — настройки инжектятся через
  DI (по умолчанию `get_settings()`), TTL-конфиг не дёргается из глобала.
- Внутренние DTO (`TokenPair`, `Principal`, `OrderItem`) перенесены в
  `src/booking/core/dto.py` (рядом с `config/errors/deps`), корень пакета чист.
- `docker-compose.yml`: добавлен сервис `worker` (тот же образ, команда
  `python -m booking.worker`); `pyproject.toml`: добавлен `apscheduler`.
- Тесты: 29 passed (в т.ч. новый тест безопасности advisory-лока).

### Шаг 4 — публичное API каталога (2026-08-25)
- Миграция 0003: events, ticket_types, info_pages; downgrade/upgrade ок ✅
- pytest: 20 passed — фильтр on_sale + soft-delete, пагинация+total, 404,
  Decimal без float в ответе, валидация limit/offset ✅
- curl на живом стеке: афиша (draft скрыт), карточка (price "1500.00" строкой),
  справка по slug, ISO-8601 UTC ✅
- Отступление от спека (согласовано с инкрементальным подходом): подсчёт
  free_tickets вернёт null до шага 5 — таблицы tickets ещё нет; счётчик
  агрегатом будет реализован вместе с ней
- ruff + mypy strict = 0 ошибок ✅

### Шаг 3 — Auth/RBAC (2026-08-25)
- Добавлен management CLI: `docker compose exec api python -m booking.cli
  create-staff <email> <pass> --role admin` (создание персонала без ручного psql)
- Исправлен баг: SQLAlchemy писал имена enum (`ADMIN`) вместо значений (`admin`);
  добавлен `values_callable` в модель Role, данные в живой БД исправлены
- Ручная проверка на живом стеке: staff login → me (role=admin) → повторный
  login инвалидирует refresh первой сессии (401) ✅
- Тестовый контур переведён на testcontainers (реальный Postgres 16, авто-подъём);
  sqlite и ручная booking_test удалены; JWT_SECRET удлинён до ≥32 байт по RFC 7518
- pytest: 13 passed — register/login/me/refresh/logout, lockout 3→30 мин,
  single-session персонала (старый refresh инвалидируется), чужой/просроченный
  JWT → 401, RBAC-разделение client/system_user ✅
- curl-прогон на живом стеке: полный флоу + ротация refresh (старый → 401) ✅
- Миграция 0002 (refresh_tokens + lockout клиентов) накатилась; downgrade→upgrade ок ✅
- ruff + mypy strict = 0 ошибок ✅ · UTC-правило: grep чист ✅
- Известное поведение: access-токен остаётся валиден до истечения после logout
  (stateless JWT); refresh отозван. Для MVP принято.

### Шаг 2 — фундамент БД (2026-08-25)
- Спек 02 пересмотрен по замечанию заказчика: big-bang → инкрементальные миграции
- `alembic upgrade head` на чистую БД → созданы roles, system_users, clients ✅
- Цикл `downgrade base && upgrade head` — воспроизводимо ✅
- pytest против реального Postgres (booking_test): 5 passed — CRUD репозитория,
  soft-delete фильтрация чтений, version++ при update ✅
- ruff + mypy strict = 0 ошибок (локально `.venv` и в Docker) ✅
- Слои Clean Architecture введены: models → repositories (generic CRUD) → services (каркас)

### Шаг 1 — каркас (2026-08-25)
- `make run`: api + db (pg16) healthy ✅
- `curl /health` → 200 `{"status":"ok","db":"ok","version":"0.1.0"}` ✅
- Остановка БД → `/health` → 503 `"db":"error"`; старт БД → снова 200 ✅
- ruff + mypy strict → 0 ошибок ✅ (в Docker и локально в `.venv`)
- pytest → 2 passed ✅
- Окружение: `.venv` на Python 3.12.10 (uv); Docker-образ python:3.12-slim, non-root

## Известные замечания / риски

- Корпоративный pypi-индекс `nexus.zvq.me` недоступен — пакеты ставились с pypi.org.
- Хостовой Python 3.10 — весь код гоняется через Docker или `.venv` (3.12).
