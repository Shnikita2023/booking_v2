# Spec 03: Аутентификация, сессии, RBAC

Статус: **DRAFT — на утверждении**
Реализует: C-4 (регистрация/авторизация клиента), S-1 (авторизация персонала),
D-4 (lockout 3→30 мин), D-5 (одна активная сессия), NF-2 (безопасность).

## 1. Цель шага

Работающий auth-контур: регистрация и вход клиентов, вход персонала,
JWT-токены, защита эндпоинтов зависимостями FastAPI. Верифицируется тестами
и ручным прогоном через curl.

## 2. Требования

| ID | Требование |
|----|-----------|
| A-1 | Пароли — только Argon2id (`argon2-cffi`), никогда не логируются и не возвращаются |
| A-2 | JWT: access (15 мин) + refresh (14 дней), HS256, секрет из env; payload: sub, type, exp, jti |
| A-3 | Refresh-токены хранятся в БД (таблица `refresh_tokens`): revocable, ротация при обновлении |
| A-4 | Lockout: 3 неудачных входа подряд → `locked_until = now(UTC) + 30 мин`; успех сбрасывает счётчик |
| A-5 | Одна активная сессия: повторный вход персонала инвалидирует предыдущий refresh-токен |
| A-6 | RBAC: роли admin/manager/cashier; зависимость `require_role(...)` для защищённых эндпоинтов |
| A-7 | Регистрация клиента: email + password (+ опц. имя/телефон); email уникален, пароль ≥ 8 символов |
| A-8 | Все временные сравнения — timezone-aware UTC (`datetime.now(UTC)`) |

## 3. API-контракт

```
POST /api/v1/auth/register   → 201 {id, email}          # клиент
POST /api/v1/auth/login      → 200 {access_token, refresh_token, token_type}
POST /api/v1/auth/refresh    → 200 {access_token, refresh_token}
POST /api/v1/auth/logout     → 204                      # Bearer access
GET  /api/v1/auth/me         → 200 {id, email, role | null, discount_percent?}

POST /api/v1/staff/login     → 200 {...как login}       # персонал (system_users)
```
Ошибки (единый формат `{detail, code}`):
`401 invalid_credentials`, `403 account_locked` (+ `retry_after`),
`409 email_taken`, `422 validation_error`.

## 4. Архитектура (слои)

```
routers/auth.py          # транспорт: схемы запросов/ответов, HTTP-статусы
services/auth_service.py # бизнес-логика: register/login/refresh/logout, lockout
services/security.py     # argon2 hash/verify, jwt encode/decode (чистые функции)
repositories/            # ClientRepository (есть), SystemUserRepository, RefreshTokenRepository
models/users.py          # + модель RefreshToken (миграция 0002)
schemas/auth.py          # Pydantic v2 контракты
core/deps.py             # get_current_principal, require_role(...)
```

Principal = унифицированный объект текущего пользователя (client | system_user).

### Модель refresh_tokens (миграция 0002)
`id UUID PK`, `user_type ENUM(client/system_user)`, `user_id UUID`,
`jti UUID UNIQUE`, `expires_at TIMESTAMPTZ`, `revoked_at TIMESTAMPTZ?`,
`created_at`; индекс `(user_type, user_id)`.

### Схема lockout (A-4)
На `SystemUser.failed_attempts/locked_until`. Для клиентов — те же поля
добавляются миграцией 0002 (спам-защита регистрации/входа).

## 5. Задачи

- [ ] deps: `argon2-cffi`, `pyjwt`
- [ ] models: RefreshToken; поля lockout для Client; миграция 0002
- [ ] services/security.py: hash_password, verify_password, create/decode JWT
- [ ] repositories: RefreshTokenRepository, SystemUserRepository (вынести из теста)
- [ ] services/auth_service.py: register_client, client_login, staff_login,
      refresh, logout (логика lockout + single-session внутри)
- [ ] schemas/auth.py + routers/auth.py (+ routers/staff.py)
- [ ] core/deps.py: get_current_principal, require_role
- [ ] Тесты: happy-path всех эндпоинтов; неверный пароль; lockout на 3-й попытке;
      повторный staff-login инвалидирует старый refresh; просроченный/чужой JWT → 401;
      RBAC: клиент не проходит require_role

## 6. Критерии приёмки

1. pytest: все сценарии раздела 5 зелёные.
2. curl-прогон: register → login → me → refresh → logout; второй staff-login
   делает первый refresh невалидным.
3. ruff + mypy strict = 0 ошибок.
4. В коде нет `utcnow`/наивных datetime (grep-проверка).

## 7. Вне рамок шага

White/black IP (шаг 10), подтверждение email, восстановление пароля,
эндпоинты админ-управления пользователями (шаг 6).
