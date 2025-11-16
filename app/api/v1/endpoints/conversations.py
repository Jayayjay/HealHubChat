from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List
from uuid import UUID
import logging
from datetime import datetime

from app.db.database import get_db
from app.models.models import User, Conversation, Message
from app.schemas.schemas import (
    ConversationCreate, ConversationResponse,
    MessageCreate, MessageResponse
)
from app.core.security import get_current_user
from app.services.ml_service import ml_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation"""
    try:
        conversation = Conversation(
            user_id=current_user.id,
            title=conversation_data.title,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        logger.info(f"Created conversation {conversation.id} for user {current_user.id}")
        return conversation
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create conversation"
        )

@router.get("/", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """Get all conversations for the current user"""
    try:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == current_user.id)
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
        )
        conversations = result.scalars().all()
        logger.info(f"Retrieved {len(conversations)} conversations for user {current_user.id}")
        return conversations
    except Exception as e:
        logger.error(f"Error fetching conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch conversations"
        )

@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific conversation"""
    try:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch conversation"
        )

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all messages in a conversation"""
    try:
        # Verify conversation belongs to user
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id
            )
        )
        if not result.scalar_one_or_none():
            logger.warning(f"Conversation {conversation_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()
        logger.info(f"Retrieved {len(messages)} messages from conversation {conversation_id}")
        return messages
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching messages for conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch messages"
        )

@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: UUID,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a message in a conversation and get AI response"""
    try:
        logger.info(f"Processing message in conversation {conversation_id}")
        
        # Verify conversation
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Analyze user message with error handling
        try:
            sentiment = await ml_service.analyze_sentiment(message_data.content)
            risk_score = await ml_service.calculate_risk_score(
                message_data.content,
                sentiment.get('score', 0)
            )
        except Exception as ml_error:
            logger.warning(f"ML service error: {str(ml_error)}. Using default values.")
            sentiment = {'score': 0, 'label': 'neutral'}
            risk_score = 0
        
        # Save user message
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=message_data.content,
            sentiment_score=sentiment.get('score'),
            risk_score=risk_score,
            emotions={"primary": sentiment.get('label', 'neutral')},
            created_at=datetime.utcnow()
        )
        db.add(user_message)
        await db.commit()
        await db.refresh(user_message)
        logger.info(f"User message saved: {user_message.id}")
        
        # Get conversation history for context
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()
        history = [{"role": msg.role, "content": msg.content} for msg in messages]
        
        # Generate AI response with error handling
        logger.info("Generating AI response...")
        try:
            ai_response = await ml_service.generate_response(history)
            logger.info(f"AI response generated: {ai_response[:100]}...")
        except Exception as ai_error:
            logger.error(f"AI response generation failed: {str(ai_error)}", exc_info=True)
            ai_response = "I apologize, but I'm having trouble processing your request right now. Please try again."
        
        # Save AI message
        ai_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_response,
            sentiment_score=0.0,
            risk_score=0.0,
            emotions={},
            created_at=datetime.utcnow()
        )
        db.add(ai_message)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(ai_message)
        
        logger.info(f"Message sent in conversation {conversation_id}, AI response generated")
        
        # FIXED: Return AI message instead of user message
        return ai_message
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error sending message in conversation {conversation_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not send message: {str(e)}"
        )

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation and all its messages"""
    try:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found for deletion by user {current_user.id}")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        await db.delete(conversation)
        await db.commit()
        logger.info(f"Deleted conversation {conversation_id} for user {current_user.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete conversation"
        )