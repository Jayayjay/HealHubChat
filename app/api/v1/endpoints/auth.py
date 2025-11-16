from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta, datetime
from pydantic import BaseModel
import logging

from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import UserCreate, UserResponse, Token
from app.core.security import (
    verify_password, get_password_hash, create_access_token
)
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# JSON login request model
class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    # Check if user exists
    result = await db.execute(
        select(User).where(
            (User.username == user_data.username) | (User.email == user_data.email)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        created_at=datetime.utcnow(),
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/login/json", response_model=Token)
async def login_json(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with JSON body (accepts username or email)
    """
    logger.info(f"Login attempt for: {credentials.username}")
    
    # Find user by username or email
    result = await db.execute(
        select(User).where(
            (User.username == credentials.username) | 
            (User.email == credentials.username)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        logger.warning(f"User not found: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not getattr(user, 'is_active', True):
        logger.warning(f"Inactive user attempt: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Debug logging
    logger.info(f"User found: {user.username}, checking password...")
    logger.info(f"Password hash present: {bool(user.password_hash)}")
    
    # Verify password with comprehensive error handling
    try:
        password_valid = verify_password_with_fallbacks(credentials.password, user.password_hash)
        logger.info(f"Password verification result: {password_valid}")
        
    except Exception as e:
        logger.error(f"Password verification error for user {user.username}: {str(e)}")
        
        # Check if password might be stored in plain text
        if user.password_hash == credentials.password:
            logger.warning(f"Plain text password detected for user {user.username}. Rehashing...")
            # Rehash the password properly
            user.password_hash = get_password_hash(credentials.password)
            await db.commit()
            password_valid = True
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication system error. Please try again."
            )
    
    if not password_valid:
        logger.warning(f"Invalid password for user: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last active timestamp
    user.last_active = datetime.utcnow()
    await db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    
    logger.info(f"Successful login for user: {user.username}")
    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible login with form data (for Swagger UI)
    """
    logger.info(f"Form login attempt for: {form_data.username}")
    
    # Find user by username or email
    result = await db.execute(
        select(User).where(
            (User.username == form_data.username) | 
            (User.email == form_data.username)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        logger.warning(f"User not found (form): {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not getattr(user, 'is_active', True):
        logger.warning(f"Inactive user attempt (form): {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    try:
        password_valid = verify_password(form_data.password, user.password_hash)
        
        # Check for plain text password fallback
        if not password_valid and user.password_hash == form_data.password:
            logger.warning(f"Plain text password detected (form) for {user.username}. Rehashing...")
            user.password_hash = get_password_hash(form_data.password)
            await db.commit()
            password_valid = True
            
    except Exception as e:
        logger.error(f"Password verification error (form) for {user.username}: {str(e)}")
        password_valid = False
    
    if not password_valid:
        logger.warning(f"Invalid password (form) for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last active timestamp
    user.last_active = datetime.utcnow()
    await db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    
    logger.info(f"Successful form login for user: {user.username}")
    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }

# Debug endpoint to check user data
@router.get("/debug/user/{username}")
async def debug_user(username: str, db: AsyncSession = Depends(get_db)):
    """Debug endpoint to check user data"""
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return {"error": "User not found"}
    
    return {
        "username": user.username,
        "email": user.email,
        "has_password_hash": hasattr(user, 'password_hash') and bool(user.password_hash),
        "password_hash_length": len(user.password_hash) if hasattr(user, 'password_hash') and user.password_hash else 0,
        "password_hash_prefix": user.password_hash[:20] if hasattr(user, 'password_hash') and user.password_hash else None,
        "is_active": getattr(user, 'is_active', True),
        "created_at": getattr(user, 'created_at', None)
    }