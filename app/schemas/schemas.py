from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID
import re 

# User Schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = Field(None, max_length=100)

    @validator('password')
    def password_complexity(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(v.encode('utf-8')) > 128:
            raise ValueError('Password is too long (maximum 128 characters)')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: Optional[str]
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: Optional[int] = 3600

class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    username: Optional[str] = None

# Conversation Schemas
class ConversationCreate(BaseModel):
    title: Optional[str] = Field("New Conversation", max_length=200)

class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    is_archived: Optional[bool] = None

class ConversationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    is_archived: bool
    message_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

# Message Schemas
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)

class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    emotions: Optional[Dict[str, float]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Analytics Schemas
class AnalyticsRequest(BaseModel):
    start_date: date
    end_date: date
    user_id: Optional[UUID] = None

class AnalyticsResponse(BaseModel):
    date: datetime
    avg_sentiment: Optional[float] = Field(None, ge=-1.0, le=1.0)
    max_risk_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    message_count: int = Field(..., ge=0)
    dominant_emotions: Optional[Dict[str, float]] = None
    
    class Config:
        from_attributes = True

class RiskAlert(BaseModel):
    id: UUID
    conversation_id: UUID
    risk_level: str = Field(..., pattern="^(low|medium|high|critical)$")
    risk_score: float = Field(..., ge=0.0, le=1.0)
    message_content: str
    timestamp: datetime
    is_resolved: bool = False
    
    class Config:
        from_attributes = True

# Combined Response Schemas
class ConversationWithMessages(ConversationResponse):
    messages: List[MessageResponse] = []

class UserWithConversations(UserResponse):
    conversations: List[ConversationResponse] = []

# Health Check Schema
class HealthCheck(BaseModel):
    status: str
    database: bool
    redis: bool
    model_loaded: bool
    timestamp: datetime