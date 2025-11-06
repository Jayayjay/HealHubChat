from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta
from typing import List, Dict
from app.db.database import get_db
from app.models.models import User, Message, UserAnalytics, Conversation
from app.schemas.schemas import AnalyticsResponse, RiskAlert
from app.core.security import get_current_user

router = APIRouter()

@router.get("/dashboard", response_model=Dict)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = 7
):
    # Get user's messages from last N days
    start_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(
            func.date(Message.created_at).label('date'),
            func.avg(Message.sentiment_score).label('avg_sentiment'),
            func.max(Message.risk_score).label('max_risk'),
            func.count(Message.id).label('message_count')
        )
        .join(Conversation)
        .where(
            Conversation.user_id == current_user.id,
            Message.created_at >= start_date,
            Message.role == 'user'
        )
        .group_by(func.date(Message.created_at))
        .order_by(desc('date'))
    )
    
    daily_stats = result.all()
    
    return {
        "user_id": str(current_user.id),
        "period_days": days,
        "daily_analytics": [
            {
                "date": stat.date,
                "avg_sentiment": stat.avg_sentiment,
                "max_risk_score": stat.max_risk,
                "message_count": stat.message_count
            }
            for stat in daily_stats
        ]
    }

@router.get("/risk-alerts", response_model=List[RiskAlert])
async def get_risk_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    threshold: float = 0.5
):
    result = await db.execute(
        select(Message)
        .join(Conversation)
        .where(
            Conversation.user_id == current_user.id,
            Message.role == 'user',
            Message.risk_score >= threshold
        )
        .order_by(desc(Message.created_at))
        .limit(10)
    )
    
    messages = result.scalars().all()
    
    alerts = []
    for msg in messages:
        risk_level = "low"
        if msg.risk_score >= 0.8:
            risk_level = "critical"
        elif msg.risk_score >= 0.6:
            risk_level = "high"
        elif msg.risk_score >= 0.4:
            risk_level = "medium"
        
        alerts.append(RiskAlert(
            conversation_id=msg.conversation_id,
            risk_level=risk_level,
            risk_score=msg.risk_score,
            message_content=msg.content[:200],
            timestamp=msg.created_at
        ))
    
    return alerts
