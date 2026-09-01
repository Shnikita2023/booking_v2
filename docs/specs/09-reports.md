# Спек шага 9 — Отчёты (статистика / бухгалтерия)

> Трассировка ТЗ: S-6 (отчёты: статистические и бухгалтерские).

## 1. Цель

Предоставить staff-пользователям (ADMIN, MANAGER) REST-API для получения
статистических и бухгалтерских отчётов по продажам, выручке, загрузке
мероприятий, активности клиентов и аудиту.

## 2. Принятые решения

- **Только read-only** — отчёты не изменяют данные, только агрегируют.
- **Без миграции** — все данные уже есть в `orders`, `payments`, `ticket_types`,
  `clients`, `audit_log`.
- **Пагинация** — `limit` (дефолт 50, макс 200) + `offset` (дефолт 0).
- **Фильтры по дате** — `from_date`, `to_date` (ISO 8601, опциональные).
- **Доступ** — `require_role(ADMIN, MANAGER)`.
- **N+1 не допускается** — все запросы через `GROUP BY` + SQL-агрегации.

## 3. Эндпоинты

### 3.1 Выручка по мероприятиям

```
GET /api/v1/staff/reports/revenue?from_date=&to_date=
```

Response: `RevenueReport[]`
```json
[
  {
    "event_id": "uuid",
    "event_title": "Concert",
    "event_starts_at": "2026-03-15T19:00:00Z",
    "total_revenue": "150000.00",
    "payment_count": 42
  }
]
```

SQL: `payments JOIN orders JOIN events WHERE payments.status = 'succeeded'
GROUP BY event_id`

### 3.2 Выручка по дням

```
GET /api/v1/staff/reports/revenue-by-date?from_date=&to_date=
```

Response: `RevenueByDateReport[]`
```json
[
  {
    "date": "2026-03-15",
    "total_revenue": "25000.00",
    "payment_count": 7
  }
]
```

SQL: `payments WHERE status = 'succeeded' GROUP BY DATE_TRUNC('day', paid_at)`

### 3.3 Продажи по статусам

```
GET /api/v1/staff/reports/sales?from_date=&to_date=
```

Response: `SalesReport[]`
```json
[
  {
    "status": "paid",
    "order_count": 120,
    "total_amount": "350000.00"
  }
]
```

SQL: `orders WHERE deleted_at IS NULL GROUP BY status`

### 3.4 Загрузка мероприятий

```
GET /api/v1/staff/reports/occupancy
```

Response: `OccupancyReport[]`
```json
[
  {
    "event_id": "uuid",
    "event_title": "Concert",
    "event_starts_at": "2026-03-15T19:00:00Z",
    "total_quota": 500,
    "total_sold": 320,
    "occupancy_pct": 64.0
  }
]
```

SQL: `ticket_types GROUP BY event_id → SUM(quota), SUM(sold), ROUND(sold/quota*100, 1)`

### 3.5 Топ клиентов

```
GET /api/v1/staff/reports/top-clients?limit=10&offset=0
```

Response: `TopClientReport[]`
```json
[
  {
    "client_id": "uuid",
    "full_name": "Иванов Иван",
    "email": "ivan@example.com",
    "total_orders": 15,
    "total_spent": "45000.00"
  }
]
```

SQL: `orders JOIN clients WHERE status = 'paid' AND deleted_at IS NULL
GROUP BY client_id ORDER BY SUM(total_amount) DESC`

### 3.6 Статистика аудита

```
GET /api/v1/staff/reports/audit-stats?from_date=&to_date=
```

Response: `AuditStatsReport[]`
```json
[
  {
    "action": "auth_login_ok",
    "actor_role": "admin",
    "count": 35
  }
]
```

SQL: `audit_log WHERE created_at BETWEEN :from AND :to
GROUP BY action, actor_role ORDER BY count DESC`

## 4. Схемы ответов

Все response-модели наследуют `BaseModel`. Поля с деньгами — `Decimal`.
Поля с UUID — `uuid.UUID`. Поля с датами — `datetime | None`.

## 5. Критерии приёмки

- [ ] 6 эндпоинтов доступны через `GET /api/v1/staff/reports/*`
- [ ] Доступ только для ADMIN и MANAGER (403 для CASHIER и клиентов)
- [ ] Фильтры `from_date`/`to_date` работают
- [ ] Пагинация `limit`/`offset` работает
- [ ] Нет N+1 — все агрегации через SQL
- [ ] Тесты покрывают все 6 эндпоинтов + пагинацию + фильтры
