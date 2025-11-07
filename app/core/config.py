from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database - individual components
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: str = "5432"
    
    # Return DATABASE_URL as a string, not URL object
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
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