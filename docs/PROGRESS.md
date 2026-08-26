# Прогресс проекта Booking v2

> Краткий статус для команды: что сделано, что на утверждении, что дальше.
> Обновляется после каждого закрытого шага.
> Процесс: SDD — спек → утверждение → реализация → верификация.

**Дата обновления:** 2026-08-25
**Статус:** Шаг 2 завершён ✅ · следующий — спек Auth (шаг 3)

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
- **Инкрементальная схема БД**: полная модель данных живёт в спеке как проектная
  документация, но каждая таблица создаётся миграцией того шага, где впервые нужна.
  Порядок: roles/system_users/clients (02) → events/ticket_types/info_pages (04) →
  orders/tickets/payments (05) → discounts (06) → audit_log+партиции (07).

## Статус шагов

| # | Шаг | Спек | Статус | Верификация |
|---|-----|------|--------|-------------|
| 0 | Vision / декомпозиция ТЗ | `00-vision.md` | ✅ принят | — |
| 1 | Каркас: Docker, FastAPI, /health, CI-скрипты | `01-scaffolding.md` | ✅ принят и реализован | все критерии пройдены |
| 2 | Фундамент БД + срез Auth-таблиц (инкремент) | `02-database.md` | ✅ принят (пересмотрен) и реализован | все критерии пройдены |
| 3 | Auth + RBAC + сессии + lockout | `03-auth.md` | ✅ принят и реализован | все критерии пройдены |
| 4 | Публичное API (афиша, мероприятие, справка) | `04-public-api.md` | ⏳ пишется | — |
| 5 | Заказы и билеты (TTL-резерв, отмена) | `05-orders.md` | ⬜ | — |
| 6 | Админ-API (мероприятия, клиенты, настройки) | `06-admin.md` | ⬜ | — |
| 7 | Audit-лог + информирование о системе | `07-audit.md` | ⬜ | — |
| 8 | Платежи (mock uniPayment) + рассылка писем | `08-payments.md` | ⬜ | — |
| 9 | Отчёты (статистика/бухгалтерия) | `09-reports.md` | ⬜ | — |

## Журнал верификаций

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
