.PHONY: run test lint fmt migrate down

run:
	docker compose up --build -d

down:
	docker compose down

test:
	docker compose build api >/dev/null
	docker compose run --rm --no-deps \
	  -e RUFF_CACHE_DIR=/tmp/.cache/ruff -e MYPY_CACHE_DIR=/tmp/.cache/mypy \
	  api sh -c "pip install -q pytest pytest-asyncio httpx aiosqlite ruff mypy && python -m pytest tests -q -p no:cacheprovider"

lint:
	docker compose build api >/dev/null
	docker compose run --rm --no-deps \
	  -e RUFF_CACHE_DIR=/tmp/.cache/ruff -e MYPY_CACHE_DIR=/tmp/.cache/mypy \
	  api sh -c "pip install -q ruff mypy && python -m ruff check src tests && python -m mypy src tests"

fmt:
	python3 -m ruff format src tests && python3 -m ruff check --fix src tests

migrate:
	docker compose exec api alembic upgrade head
