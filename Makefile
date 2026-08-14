.PHONY: help up down restart logs ps build rebuild psql migrate upgrade downgrade test health clean

COMPOSE        := docker compose
APP_SERVICE    := backend
POSTGRES_SERVICE := postgres
DB_NAME        := flowdocs
DB_USER        := flowdocs

help:
	@echo "FlowDocs V2 — common targets:"
	@echo "  make up        Start Postgres + backend (detached)"
	@echo "  make down      Stop everything, keep volumes"
	@echo "  make restart   Restart services"
	@echo "  make logs      Tail backend logs"
	@echo "  make ps        Show container status"
	@echo "  migrate        Apply Alembic migrations"
	@echo "  downgrade      Roll back the last Alembic migration"
	@echo "  test           Run pytest inside the backend container"
	@echo "  health         Curl the /health endpoint"
	@echo "  clean          Stop services and delete volumes (DESTRUCTIVE)"

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f $(APP_SERVICE)

ps:
	$(COMPOSE) ps

migrate:
	$(COMPOSE) exec $(APP_SERVICE) alembic upgrade head

downgrade:
	$(COMPOSE) exec $(APP_SERVICE) alembic downgrade -1

test:
	$(COMPOSE) exec $(APP_SERVICE) pytest -v

health:
	@curl -fsS http://localhost:8000/health && echo

clean:
	$(COMPOSE) down -v
