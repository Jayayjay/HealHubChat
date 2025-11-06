from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List
from uuid import UUID
from app.db.database import get_db
from app.models.models import User, Conversation, Message
from app.schemas.schemas import (
    ConversationCreate, ConversationResponse,
    MessageCreate, MessageResponse
)
from app.core.security import get_current_user
from app.services.ml_service import ml_service
# from functools import func

router = APIRouter()

@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    conversation = Conversation(
        user_id=current_user.id,
        title=conversation_data.title
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation

@router.get("/", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(desc(Conversation.updated_at))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify conversation belongs to user
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get messages
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return result.scalars().all()

@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: UUID,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify conversation
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Analyze user message
    sentiment = await ml_service.analyze_sentiment(message_data.content)
    risk_score = await ml_service.calculate_risk_score(
        message_data.content,
        sentiment['score']
    )
    
    # Save user message
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=message_data.content,
        sentiment_score=sentiment['score'],
        risk_score=risk_score,
        emotions={"primary": sentiment['label']}
    )
    db.add(user_message)
    await db.commit()
    
    # Get conversation history
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    history = [{"role": msg.role, "content": msg.content} for msg in messages]
    
    # Generate AI response
    ai_response = await ml_service.generate_response(history)
    
    # Save AI message
    ai_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=ai_response
    )
    db.add(ai_message)
    
    # Update conversation timestamp
    conversation.updated_at = func.now()
    await db.commit()
    await db.refresh(user_message)
    
    return user_message

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    await db.delete(conversation)
    await db.commit()

