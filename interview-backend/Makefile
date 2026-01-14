# AI Mock Interview Backend - Makefile
# Usage: make [target]

.PHONY: help install run dev docker-build docker-run clean

# Default target
help:
	@echo "AI Mock Interview Backend"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install      Install dependencies in virtual environment"
	@echo "  run          Start the backend server (production)"
	@echo "  dev          Start the backend server with auto-reload"
	@echo "  docker-build Build Docker image"
	@echo "  docker-run   Run in Docker container"
	@echo "  clean        Remove virtual environment and cache"
	@echo ""
	@echo "Quick start: make dev"

# Install dependencies
install:
	@echo "📦 Setting up virtual environment..."
	@test -d venv || python3 -m venv venv
	@echo "📦 Upgrading pip and setuptools..."
	@./venv/bin/pip install -q --upgrade pip setuptools wheel
	@echo "📦 Installing dependencies..."
	@./venv/bin/pip install -q -r requirements.txt
	@echo "✅ Installation complete!"
	@echo ""
	@echo "Python: $$(./venv/bin/python --version)"
	@echo "Environment: ./venv"

# Run production server
run: install
	@echo "🚀 Starting server on http://localhost:8000"
	@./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000

# Run development server with auto-reload
dev: install
	@echo "🚀 Starting dev server on http://localhost:8000 (auto-reload enabled)"
	@./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Build Docker image
docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t ai-mock-interview-backend .

# Run in Docker
docker-run:
	@echo "🐳 Running in Docker..."
	docker run -p 8000:8000 --env-file .env ai-mock-interview-backend

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	rm -rf venv __pycache__ *.pyc
	@echo "✅ Cleanup complete!"
