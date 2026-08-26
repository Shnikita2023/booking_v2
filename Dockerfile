FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --prefix=/install ".[dev]"

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src \
    XDG_CACHE_HOME=/tmp/.cache HOME=/tmp
RUN groupadd -r app && useradd -r -g app app
WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=app:app src ./src
COPY --chown=app:app tests ./tests
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini pyproject.toml ./
USER app
EXPOSE 8000
CMD ["uvicorn", "booking.main:app", "--host", "0.0.0.0", "--port", "8000"]
