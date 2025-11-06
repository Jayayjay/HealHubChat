from pydantic_settings import BaseSettings
from sqlalchemy.engine import URL

class Settings(BaseSettings):
    # Database - individual components
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: str = "5432"
    
    # Construct DATABASE_URL using SQLAlchemy URL object
    @property
    def DATABASE_URL(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,  # Raw password - no encoding needed!
            host=self.POSTGRES_HOST,
            port=int(self.POSTGRES_PORT),
            database=self.POSTGRES_DB,
        )
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Model paths
    MODEL_PATH: str = "/models/healhub-tinyllama-1.1B-Chat"
    BASE_MODEL_PATH: str = "jayayjay/TinyLlama-HealHub-FineTuned"
    
    # App
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()