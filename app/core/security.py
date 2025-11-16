from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import re
from app.core.config import settings
from app.models.models import User
from app.db.database import get_db

# Set up logging
logger = logging.getLogger(__name__)

pwd_context = CryptContext(
    schemes=["argon2"],  # Use only argon2
    deprecated="auto"
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hashed password.
    Handles bcrypt's 72-byte limit by truncating.
    """
    if not plain_password or not hashed_password:
        return False
    
    try:
        # Truncate password to 72 bytes for bcrypt compatibility
        password_bytes = plain_password.encode('utf-8')[:72]
        password_to_verify = password_bytes.decode('utf-8', errors='ignore')
        
        return pwd_context.verify(password_to_verify, hashed_password.strip())
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False

def get_password_hash(password: str) -> str:
    """
    Hash a password using the configured password context.
    Handles bcrypt's 72-byte limit by truncating.
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    # Truncate password to 72 bytes for bcrypt compatibility
    password_bytes = password.encode('utf-8')[:72]
    password_to_hash = password_bytes.decode('utf-8', errors='ignore')
    
    if len(password.encode('utf-8')) > 72:
        logger.warning(f"Password exceeded 72 bytes and was truncated")
    
    return pwd_context.hash(password_to_hash)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token with the provided data.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def validate_jwt_token(token: str) -> dict:
    """
    Validate JWT token with comprehensive error handling
    """
    if not token:
        logger.error("Empty token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided"
        )
    
    # Basic JWT format validation (should have 3 segments separated by dots)
    if token.count('.') != 2:
        logger.error(f"Invalid JWT format: {token[:50]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    
    # Check token length (basic sanity check)
    if len(token) < 10:
        logger.error(f"Token too short: {token}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT decoding failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from the JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = validate_jwt_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {str(e)}")
        raise credentials_exception
    
    try:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user is None:
            raise credentials_exception
        return user
    except Exception as e:
        logger.error(f"Database error during user lookup: {str(e)}")
        raise credentials_exception