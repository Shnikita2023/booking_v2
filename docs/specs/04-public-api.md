# Spec 04: Публичное API — афиша, мероприятие, справка

Статус: **DRAFT — на утверждении**
Реализует: C-1/C-2 (афиша и карточка мероприятия), C-3 (справочная информация),
S-2 частично (модель мероприятия), DB-5 (Decimal для денег).

## 1. Цель шага

Публичные (без авторизации) эндпоинты каталога мероприятий и справки.
Первая миграция с доменными таблицами: `events`, `ticket_types`, `info_pages`.

## 2. Требования

| ID | Требование |
|----|-----------|
| E-1 | Афиша: только `status = on_sale` и не удалённые; сортировка по `starts_at`; пагинация `limit/offset`; ответ содержит total |
| E-2 | Афиша: мини-баннер в выдаче; если `show_free_tickets=true` — кол-во свободных билетов |
| E-3 | Карточка: все поля мероприятия + крупный баннер; `404 event_not_found` для отсутствующего/скрытого |
| E-4 | Справка: `GET /pages/{slug}` → `{slug, title, content}`; `404 page_not_found` |
| E-5 | Деньги: `price` — `NUMERIC(12,2)` / Python `Decimal` (float запрещён) |
| E-6 | Время: только TIMESTAMPTZ, API отдаёт ISO-8601 c UTC offset |

## 3. Модель данных (миграция 0003)

### events
`title`, `description?`, `starts_at`, `duration_min?`, `age_rating?`,
`venue?`, `price NUMERIC(12,2)?`, `status ENUM(draft/on_sale/paused/
cancelled/moved/completed)`, `banner_small_url?`, `banner_large_url?`,
`show_free_tickets bool=false`, `sale_paused bool=false`,
`cloned_from_id FK→events?`; индекс `(status, starts_at)`.

### ticket_types
`event_id FK`, `name`, `price NUMERIC(12,2)`, `quota`;
CHECK price >= 0, quota >= 0.

### info_pages
`slug UNIQUE`, `title`, `content TEXT`, `updated_by UUID?`, `version`.

## 4. API-контракт

```
GET /api/v1/events?limit=20&offset=0
→ 200 { items: [EventShort], total: int }
EventShort: id, title, starts_at, venue?, age_rating?, banner_small_url?,
            free_tickets? (int | null)

GET /api/v1/events/{id}
→ 200 EventDetail: + description, duration_min, price (Decimal), status,
   banner_large_url, show_free_tickets, sale_paused, free_tickets?

GET /api/v1/pages/{slug}
→ 200 PageResponse { slug, title, content }
```
Валидация: `limit` 1..100 (default 20), `offset` >= 0.
Ошибки: `404 event_not_found`, `404 page_not_found`, `422 validation_error`.

## 5. Архитектура (слои)

```
routers/events.py, routers/pages.py   # транспорт, Annotated-зависимости
services/event_service.py             # бизнес-логика: афиша, счётчик free_tickets
repositories/event.py                 # EventRepository, InfoPageRepository
models/events.py                      # Event, TicketType (+ InfoPage в clients.py)
schemas/event.py                      # Pydantic v2 контракты
```

Правила: Decimal везде; роутер без обращений к БД; сервис не знает про HTTP;
импорты в начале файла; UTC-only.

Подсчёт free_tickets: агрегатом `COUNT(tickets WHERE status='free')` по
`ticket_types.event_id` — одним запросом к списку (N+1 запрещён).

## 6. Задачи

- [ ] models/events.py: Event, TicketType (+values_callable для enum)
- [ ] models/clients.py: InfoPage; миграция 0003 (таблицы + индексы)
- [ ] repositories/event.py: list_on_sale (join count), get_on_sale, InfoPageRepository.get_by_slug
- [ ] services/event_service.py: список с free_tickets, деталь, страница справки
- [ ] schemas/event.py: EventShort, EventDetail, PageResponse, query-параметры
- [ ] routers/events.py, routers/pages.py (публичные, без auth)
- [ ] Тесты (testcontainers): фильтр on_sale + soft-delete, пагинация+total,
      404, Decimal в ответе (строка без float), free_tickets считается верно,
      N+1 отсутствует (число SQL-запросов ограничено)

## 7. Критерии приёмки

1. pytest зелёный, включая сценарии раздела 6.
2. curl-прогон на живом стеке: seed мероприятия через CLI/SQL → афиша, карточка, справка.
3. ruff + mypy strict = 0 ошибок; grep: нет float при деньгах, нет utcnow.
4. Миграция 0003 накатывается; downgrade/upgrade воспроизводим.

## 8. Вне рамок шага

Админ-CRUD мероприятий (шаг 6), покупка билетов (шаг 5), поиск/фильтры по
атрибутам, кэширование.
