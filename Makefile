# Makefile for Loopin Backend Docker Management

.PHONY: help build up down restart logs shell migrate collectstatic test clean

# Default target
help:
	@echo "Loopin Backend Docker Management"
	@echo "================================"
	@echo ""
	@echo "Available commands:"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start all services (development)"
	@echo "  make dev            - Start development environment (Django runserver)"
	@echo "  make prod           - Start production environment (Nginx + Gunicorn)"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - Show logs for all services"
	@echo "  make logs-web       - Show logs for web service"
	@echo "  make shell          - Open shell in web container"
	@echo "  make migrate        - Run Django migrations"
	@echo "  make collectstatic  - Collect static files"
	@echo "  make test           - Run Django tests"
	@echo "  make clean          - Clean up containers and volumes"
	@echo "  make clean-all      - Clean up everything including images"
	@echo ""

# Build Docker images
build:
	docker-compose build

# Start all services (development)
up:
	docker-compose up -d

# Start development environment
dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Start production environment
prod:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Stop all services
down:
	docker-compose down

# Restart all services
restart:
	docker-compose restart

# Show logs
logs:
	docker-compose logs -f

# Show logs for specific service
logs-web:
	docker-compose logs -f web

logs-celery:
	docker-compose logs -f celery

logs-postgres:
	docker-compose logs -f postgres

logs-redis:
	docker-compose logs -f redis

# Open shell in web container
shell:
	docker-compose exec web bash

# Django management commands
migrate:
	docker-compose exec web python3 manage.py migrate

makemigrations:
	docker-compose exec web python3 manage.py makemigrations

collectstatic:
	docker-compose exec web python3 manage.py collectstatic --noinput

createsuperuser:
	docker-compose exec web python3 manage.py createsuperuser

# Run tests
test:
	docker-compose exec web python3 manage.py test

# Database operations
db-reset:
	docker-compose exec web python3 manage.py flush --noinput

# Celery operations
celery-shell:
	docker-compose exec celery celery -A loopin_backend shell

celery-purge:
	docker-compose exec celery celery -A loopin_backend purge

# Monitoring
flower:
	@echo "Flower monitoring available at: http://localhost:5555"


# Cleanup
clean:
	docker-compose down -v
	docker system prune -f

clean-all:
	docker-compose down -v --rmi all
	docker system prune -af

# Health checks
health:
	@echo "Checking service health..."
	@docker-compose ps
	@echo ""
	@echo "Web service health:"
	@curl -f http://localhost:8000/api/health/ || echo "Web service not responding"
	@echo ""
	@echo "Redis health:"
	@docker-compose exec redis redis-cli ping || echo "Redis not responding"
	@echo ""
	@echo "PostgreSQL health:"
	@docker-compose exec postgres pg_isready -U postgres || echo "PostgreSQL not responding"

# Development helpers
install-deps:
	docker-compose exec web pip install -r requirements.txt

update-deps:
	docker-compose exec web pip install -r requirements.txt --upgrade

# Quick start for new developers
setup:
	@echo "Setting up Loopin Backend development environment..."
	@make build
	@make dev
	@make migrate
	@make collectstatic
	@echo ""
	@echo "Setup complete! Services running:"
	@echo "  Web: http://localhost:8000"
	@echo "  Flower: http://localhost:5555"
