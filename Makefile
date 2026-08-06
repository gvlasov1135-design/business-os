.PHONY: up down test lint typecheck check logs

up:
	docker compose up --build

down:
	docker compose down

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

logs:
	docker compose logs -f
