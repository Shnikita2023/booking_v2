# Spec 01: Каркас проекта (scaffolding)

Статус: **DRAFT — на утверждении**
Реализует: NF-1…NF-6 (инфраструктурная база), без бизнес-логики.

## 1. Цель шага

Поднять работающий скелет системы: FastAPI-приложение в Docker с PostgreSQL,
healthcheck, конфигурацией через переменные окружения, линтерами и тестовым
контуром. Критерий завершения: `docker compose up` поднимает API и БД,
`GET /health` отвечает, тесты и линтер проходят.

## 2. Требования

| ID | Требование |
|----|-----------|
| SC-1 | Приложение запускается в Docker (python:3.12-slim) |
| SC-2 | PostgreSQL 16 в docker-compose с healthcheck; app стартует после готовности БД |
| SC-3 | Конфигурация строго из env / .env (12-factor); секреты не в git |
| SC-4 | `GET /health` → `{"status": "ok", "db": "ok"}`; проверяет соединение с БД |
| SC-5 | Асинхронный движок SQLAlchemy 2 + пул соединений; подключение к БД через DI (`Depends`) |
| SC-6 | Единый формат ошибок: `{"detail": ..., "code": ...}` через кастомные exception handlers |
| SC-7 | Structured logging (JSON) с request-id middleware |
| SC-8 | ruff (lint+format) и mypy настроены, проходят без замечаний |
| SC-9 | pytest + pytest-asyncio; smoke-тест health-эндпоинта проходит в CI-режиме |
| SC-10 | Makefile: `make run`, `make test`, `make lint`, `make migrate` |

## 3. Структура репозитория

```
booking_v2/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml          # deps + [tool.ruff] [tool.mypy] [tool.pytest]
├── Makefile
├── .env.example
├── alembic.ini             # появится на шаге 2
├── src/
│   ├── main.py             # create_app(), include routers
│   ├── core/
│   │   ├── config.py       # pydantic-settings
│   │   ├── logging.py      # JSON logger + request-id
│   │   └── errors.py       # AppError + handlers
│   └── db/
│       ├── engine.py       # async engine, sessionmaker
│       └── deps.py         # get_session dependency
└── tests/
    ├── conftest.py         # httpx AsyncClient fixture
    └── test_health.py
```

## 4. Контракт health-эндпоинта

```
GET /health → 200
{ "status": "ok", "db": "ok", "version": "0.1.0" }
```
БД недоступна → `503 {"status": "degraded", "db": "error"}`.

## 5. Конфигурация (.env.example)

```
APP_ENV=dev            # dev | test | prod
DATABASE_URL=postgresql+asyncpg://booking:booking@db:5432/booking
LOG_LEVEL=INFO
JWT_SECRET=change-me   # используется с шага 3
ACCESS_TTL_MIN=15
REFRESH_TTL_DAYS=14
```

## 6. Задачи (чек-лист)

- [ ] pyproject.toml: зависимости (fastapi, uvicorn[standard], sqlalchemy[asyncio],
      asyncpg, pydantic-settings), dev-deps (pytest, httpx, ruff, mypy)
- [ ] src/core/config.py — Settings(BaseSettings)
- [ ] src/db/engine.py + deps.py
- [ ] src/core/errors.py + логирование с request-id
- [ ] src/main.py: create_app, /health c ping БД (`SELECT 1`)
- [ ] Dockerfile (multi-stage, non-root user)
- [ ] docker-compose.yml: db (pg16, volume, healthcheck pg_isready) + api
- [ ] tests/test_health.py (мок БД для unit, реальная БД для интеграции)
- [ ] Makefile + .env.example + .gitignore (+.dockerignore)

## 7. Критерии приёмки

1. `cp .env.example .env && make run` → оба контейнера healthy.
2. `curl localhost:8000/health` → 200, `"db": "ok"`.
3. `make lint` → 0 ошибок ruff+mypy.
4. `make test` → тесты зелёные.
5. Остановка БД при работающем API → `/health` отдаёт 503 `"db": "error"`.

## 8. Вне рамок шага

Модели данных, миграции, аутентификация, любые бизнес-роуты.
