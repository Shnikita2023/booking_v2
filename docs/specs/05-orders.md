# Спек шага 5 — Заказы и билеты

> Трассировка ТЗ: C-6 (бронь/покупка, только авторизованный), C-7 (отмена из
> кабинета), NF-1 (конкурентная бронь), D-1 (soft-delete), D-2/D-3 (аудит —
> шаг 7). Оплата — **заглушка** (реальный uniPayment → шаг 8, D-7).

## 1. Цель

Закрыть ядро продаж: авторизованный клиент бронирует билеты (квотная модель,
без мест), оплачивает (заглушка), может отменить бронь/заказ из кабинета.
Конкурентная бронь не допускает перерасхода квоты.

## 2. Принятые решения (утверждены)

- **Квотная модель (без мест):** билет = строка в `tickets`, привязанная к
  `ticket_types`; вместимость ограничена `ticket_types.quota`. Места/ряды — вне
  MVP.
- **TTL удержания = 15 минут** (`RESERVATION_TTL_MINUTES` в конфиге). Заказ в
  `RESERVED` автоматически отменяется по истечении `reserved_until`, квота
  освобождается.
- **Оплата — заглушка:** `POST /orders/{id}/pay` переводит `RESERVED → PAID`
  и ставит `payments.status = SUCCEEDED`. Реальный вызов uniPayment — шаг 8.
- **Конкурентность (NF-1):** резерв берёт строку `ticket_types` под
  `SELECT … FOR UPDATE` (row-level блокировка), атомарно проверяет
  `sold + qty <= quota` и инкрементит `sold`. Это сериализует правки квоты и
  исключает oversell. (Вариант `FOR UPDATE SKIP LOCKED` применим при
  дискретных строках инвентаря/мест — расширение шага 6; семантика защиты та
  же.)

## 3. Модель данных (миграция 0004)

### 3.1 Доработка `ticket_types` (из шага 4)
- `sold INTEGER NOT NULL DEFAULT 0` — счётчик занятых мест по тарифу.

### 3.2 Новые таблицы
- `orders`: `id UUID PK`, `client_id`→clients, `event_id`→events,
  `status` enum(`reserved`,`paid`,`cancelled`), `total_amount NUMERIC(12,2)`,
  `reserved_until TIMESTAMPTZ`, `created_at`, `updated_at`, `deleted_at`,
  `version`.
- `tickets`: `id UUID PK`, `order_id`→orders, `ticket_type_id`→ticket_types,
  `price NUMERIC(12,2)` (снимок цены на момент брони), `status` enum
  (`active`,`cancelled`), `created_at`, `updated_at`, `deleted_at`.
- `payments`: `id UUID PK`, `order_id`→orders, `status` enum
  (`pending`,`succeeded`,`failed`,`refunded`), `amount NUMERIC(12,2)`,
  `external_id VARCHAR` (заглушка), `created_at`, `updated_at`.

## 4. Статусная машина заказа

```
RESERVED ──pay──▶ PAID ──refund(шаг8)──▶ REFUNDED
   │                  │
   └─cancel / TTL──▶ CANCELLED
```
- `RESERVED`: квота забронирована, `reserved_until = now + 15m`.
- `PAID`: оплата подтверждена (заглушка).
- `CANCELLED`: отмена клиентом или истёк TTL → `tickets`→`cancelled`, квота
  (`sold`) уменьшается.
- Отмена уже оплаченного заказа в шаге 5 запрещена (`AppError`, код
  `paid_order_cannot_cancel`) — возврат через шаг 8.

## 5. Сервисный слой (`OrderService`)

- `reserve(*, client_id, event_id, items)` — валидация мероприятия
  (on_sale, не `sale_paused`), блокировка `ticket_types` `FOR UPDATE`,
  проверка квоты, создание `Order`+`Ticket`(снимок цены)+`Payment`(pending),
  инкремент `sold`; коммит в конце.
- `confirm_payment(order_id, client_id)` — `RESERVED → PAID`, `payments`
  `succeeded`; коммит.
- `cancel(order_id, client_id)` — только `RESERVED`; освобождение квоты,
  `tickets`→cancelled, `payments`→failed, `CANCELLED`; коммит.
- `list_for_client(client_id)` / `get_client_order(order_id, client_id)`.
- `cleanup_expired()` — находит `RESERVED` с `reserved_until < now`, отменяет
  (освобождая квоту). Вызывается фоновой задачей приложения (lifespan, раз в
  60с) и может дёргаться вручную.
- `EventService.count_free_tickets(event)` — реальный подсчёт:
  `SUM(quota − sold)` по активным тарифам мероприятия (вместо `null`).

Репозитории — flush-only; коммит в сервисе.

## 6. Транспортный слой

`routers/client/orders.py`, `require_client` (UserType.CLIENT):
- `POST /api/v1/orders` — бронь (`OrderCreateRequest`).
- `POST /api/v1/orders/{id}/pay` — заглушка оплаты.
- `POST /api/v1/orders/{id}/cancel` — отмена.
- `GET /api/v1/orders` — история кабинета (C-5/C-7).

Схемы (`schemas/order.py`) — только на границе: `OrderItemRequest`,
`OrderCreateRequest`, `TicketRead`, `OrderRead`, `OrderListResponse`. Деньги —
`Decimal`; время — ISO-8601 UTC.

## 7. Критерии приёмки

- [ ] Бронь уменьшает свободную квоту (`sold` растёт, `free_tickets` падает).
- [ ] Конкурентный тест: N параллельных броней на тариф с квотой X —
  суммарно продано ≤ X, перерасход невозможен (row-lock).
- [ ] Истёкший `reserved_until` → `cleanup_expired` отменяет заказ, квота
  возвращается.
- [ ] Отмена из кабинета освобождает квоту и ставит `CANCELLED`+`tickets`
  cancelled.
- [ ] `free_tickets` в афише/карточке — реальное число (не null), когда
  `show_free_tickets=true`.
- [ ] Неавторизованный → 401; авторизованный не-client → 403.
- [ ] Миграция `upgrade head` / `downgrade base` воспроизводима.
- [ ] ruff + mypy strict = 0; pytest зелёный (testcontainers, Postgres 16).
- [ ] curl на живом стеке: бронь → оплата(заглушка) → отмена.
