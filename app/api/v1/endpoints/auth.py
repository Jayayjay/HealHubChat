from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta, datetime
from pydantic import BaseModel

from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import UserCreate, UserResponse, Token
from app.core.security import (
    verify_password, get_password_hash, create_access_token
)
from app.core.config import settings

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
        full_name=user_data.full_name
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
    
    Example:
    ```json
    {
        "username": "john_doe",
        "password": "securepassword123"
    }
    ```
    """
    # Find user by username or email
    result = await db.execute(
        select(User).where(
            (User.username == credentials.username) | 
            (User.email == credentials.username)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password with proper error handling
    try:
        password_valid = verify_password(credentials.password, user.password_hash)
    except Exception as e:
        # Password hash is invalid/corrupted - likely plain text
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account configuration error. Please re-register or contact support."
        )
    
    if not password_valid:
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
    
    Use application/x-www-form-urlencoded:
    - username: your_username
    - password: your_password
    """
    # Find user
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.password_hash):
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
    
    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }