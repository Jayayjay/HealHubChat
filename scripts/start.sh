#!/bin/bash

echo "Starting HealHub Chat System..."

# Wait for postgres
echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "PostgreSQL started"

# Wait for redis
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "Redis started"

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Initialize database
echo "Initializing database..."
python scripts/init_db.py

# Start application
# echo "Starting FastAPI application..."
# uvicorn app.main:app --host 0.0.0.0 --port 8000