from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.endpoints import auth, conversations, analytics
from app.services.ml_service import ml_service
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Initializing ML models...")
    await ml_service.initialize()
    print("Application started!")
    yield
    # Shutdown
    print("Shutting down...")

app = FastAPI(
    title="HealHub Chat API",
    description="Mental Health Support Chat System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["Conversations"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])

@app.get("/")
async def root():
    return {"message": "HealHub Chat API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}