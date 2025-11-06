# HealHub Chat System - Backend

A production-ready mental health support chat system built with FastAPI, PostgreSQL, and Docker.

## Features

- User authentication and authorization (JWT)
- Real-time chat with AI mental health assistant
- Conversation persistence and history
- Sentiment analysis on messages
- Mental health risk scoring
- User analytics dashboard
- Risk alerts and monitoring
- RESTful API with automatic OpenAPI documentation
- Dockerized deployment
- PostgreSQL database with async support
- Redis caching (ready for integration)

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15
- **Caching**: Redis 7
- **ORM**: SQLAlchemy 2.0 (async)
- **ML Models**: 
  - HealHub TinyLlama 1.1B (Fine-tuned for mental health)
  - DistilBERT for sentiment analysis
- **Authentication**: JWT with OAuth2
- **Containerization**: Docker & Docker Compose

## Project Structure

```
healhub-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── auth.py
│   │           ├── conversations.py
│   │           └── analytics.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   └── database.py
│   ├── models/
│   │   └── models.py
│   ├── schemas/
│   │   └── schemas.py
│   ├── services/
│   │   └── ml_service.py
│   └── main.py
├── alembic/
│   ├── versions/
│   └── env.py
├── scripts/
│   ├── init_db.py
│   ├── seed_data.py
│   └── start.sh
├── tests/
│   └── test_api.py
├── models/
│   └── healhub-tinyllama-1.1B-Chat/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env
└── README.md
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Your fine-tuned model files in `./models/healhub-tinyllama-1.1B-Chat/`

### 1. Clone and Setup

```bash
# Create project directory
mkdir healhub-backend && cd healhub-backend

# Create necessary directories
mkdir -p app/api/v1/endpoints app/core app/db app/models app/schemas app/services
mkdir -p alembic/versions scripts tests models

# Copy your fine-tuned model
cp -r /path/to/your/model ./models/healhub-tinyllama-1.1B-Chat/
```

### 2. Create .env file

```bash
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://healhub:healhub_password@db:5432/healhub_db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
MODEL_PATH=/models/healhub-tinyllama-1.1B-Chat
BASE_MODEL_PATH=TinyLlama/TinyLlama-1.1B-Chat-v1.0
ENVIRONMENT=production
DEBUG=False
EOF
```

### 3. Start Services

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d

# View logs
docker-compose logs -f api
```

### 4. Initialize Database

```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Seed sample data (optional)
docker-compose exec api python scripts/seed_data.py
```

### 5. Access the API

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token

### Conversations

- `POST /api/v1/conversations/` - Create new conversation
- `GET /api/v1/conversations/` - Get user's conversations
- `GET /api/v1/conversations/{id}` - Get specific conversation
- `GET /api/v1/conversations/{id}/messages` - Get conversation messages
- `POST /api/v1/conversations/{id}/messages` - Send message and get AI response
- `DELETE /api/v1/conversations/{id}` - Delete conversation

### Analytics

- `GET /api/v1/analytics/dashboard?days=7` - Get user analytics dashboard
- `GET /api/v1/analytics/risk-alerts?threshold=0.5` - Get risk alerts

## Usage Examples

### Register a User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepass123",
    "full_name": "John Doe"
  }'
```

### Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john_doe&password=securepass123"
```

### Create Conversation and Send Message

```bash
# Get token from login response
TOKEN="your_jwt_token_here"

# Create conversation
CONV_ID=$(curl -X POST "http://localhost:8000/api/v1/conversations/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "My First Chat"}' | jq -r '.id')

# Send message
curl -X POST "http://localhost:8000/api/v1/conversations/$CONV_ID/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "I have been feeling anxious lately"}'
```

### Get Analytics

```bash
curl -X GET "http://localhost:8000/api/v1/analytics/dashboard?days=7" \
  -H "Authorization: Bearer $TOKEN"
```

## Database Schema

### Users Table
- `id` (UUID, PK)
- `username` (String, Unique)
- `email` (String, Unique)
- `password_hash` (String)
- `full_name` (String)
- `created_at` (Timestamp)
- `last_active` (Timestamp)
- `is_active` (Boolean)
- `metadata` (JSONB)

### Conversations Table
- `id` (UUID, PK)
- `user_id` (UUID, FK)
- `title` (String)
- `created_at` (Timestamp)
- `updated_at` (Timestamp)
- `is_archived` (Boolean)

### Messages Table
- `id` (UUID, PK)
- `conversation_id` (UUID, FK)
- `role` (String: 'user' or 'assistant')
- `content` (Text)
- `sentiment_score` (Float: -1 to 1)
- `risk_score` (Float: 0 to 1)
- `emotions` (JSONB)
- `created_at` (Timestamp)

### User Analytics Table
- `id` (UUID, PK)
- `user_id` (UUID, FK)
- `date` (Date)
- `avg_sentiment` (Float)
- `max_risk_score` (Float)
- `message_count` (Integer)
- `dominant_emotions` (JSONB)

## Development

### Running Tests

```bash
docker-compose exec api pytest tests/ -v
```

### Database Migrations

```bash
# Create new migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec api alembic upgrade head

# Rollback
docker-compose exec api alembic downgrade -1
```

### Accessing Database

```bash
docker-compose exec db psql -U healhub -d healhub_db
```

### Accessing Redis

```bash
docker-compose exec redis redis-cli
```
