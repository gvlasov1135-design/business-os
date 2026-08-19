.PHONY: up down migrate test lint typecheck check logs smoke

up:
	docker compose up --build

down:
	docker compose down

migrate:
	docker compose run --rm api-migrate

test:
	docker compose --profile test build api-test
	docker compose --profile test run --rm api-test

lint:
	docker compose --profile test build web-check
	docker compose --profile test run --rm web-check sh -c "npm run lint"

typecheck:
	docker compose --profile test build web-check
	docker compose --profile test run --rm web-check sh -c "npm run typecheck"

check: test lint typecheck

smoke:
	bash scripts/smoke.sh

logs:
	docker compose logs -f
