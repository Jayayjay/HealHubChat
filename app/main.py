from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager

from app.api.v1.endpoints import auth, conversations, analytics
from app.core.config import settings
from app.services.ml_service import ml_service

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("Starting HealHub API...")
    try:
        logger.info("Initializing ML Service...")
        await ml_service.initialize()
        logger.info("ML Service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize ML Service: {str(e)}", exc_info=True)
        # Don't fail the app startup, but log the error
    
    yield
    
    # Shutdown
    logger.info("Shutting down HealHub API...")

app = FastAPI(
    title="HealHub API",
    description="Mental Health Support Chat System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
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
    """Root endpoint"""
    return {
        "message": "HealHub API",
        "version": "1.0.0",
        "ml_service_initialized": ml_service.is_initialized
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "ml_service": "ready" if ml_service.is_initialized else "initializing"
    }