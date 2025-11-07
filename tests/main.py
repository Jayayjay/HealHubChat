from app.core.config import settings
print(f"DEBUG: DB Host={settings.POSTGRES_HOST}, User={settings.POSTGRES_USER}")
print(f"DEBUG: Full URL={settings.DATABASE_URL}")