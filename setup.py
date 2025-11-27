from setuptools import setup, find_packages

setup(
    name="HealHub_Bimpe_AI",
    version="2.0.1",
    packages=find_packages(),
    author="Vongchak Jonathan",
    description="Mental Health Chatbot",
    python_requires=">=3.11",
)





# Database
DATABASE_URL=postgresql://healhub:healhub321@db:5432/healhub_db
# PostgreSQL connection settings
POSTGRES_USER=healhub
POSTGRES_PASSWORD=healhub321
POSTGRES_DB=healhub_db
POSTGRES_HOST=db
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/0

SECRET_KEY=Nz8$+GHAS5YSR@!
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Iine  Tunned model paths
MODEL_PATH=/models/healhub-tinyllama-1.1B-Chat
SENTIMENT_MODEL_PATH=/models/sentiment_model

# App
ENVIRONMENT=development
DEBUG=True # In development Mode

TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJraW5ndm9uIiwiZXhwIjoxNzYzMzI3NTY4fQ.PemipbzG7cfAJQSeHSeiUB3HxWoP5GNuyLbLNZOriWc