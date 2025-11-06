import asyncio
from app.db.database import AsyncSessionLocal
from app.models.models import User, Conversation, Message
from app.core.security import get_password_hash
from datetime import datetime, timedelta
import random

async def seed_data():
    async with AsyncSessionLocal() as db:
        # Create test users
        users_data = [
            {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "password123",
                "full_name": "John Doe"
            },
            {
                "username": "jane_smith",
                "email": "jane@example.com",
                "password": "password123",
                "full_name": "Jane Smith"
            }
        ]
        
        users = []
        for user_data in users_data:
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=get_password_hash(user_data["password"]),
                full_name=user_data["full_name"]
            )
            db.add(user)
            users.append(user)
        
        await db.commit()
        
        # Create conversations and messages
        for user in users:
            await db.refresh(user)
            
            # Create 2 conversations per user
            for i in range(2):
                conversation = Conversation(
                    user_id=user.id,
                    title=f"Conversation {i+1}",
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                )
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
                
                # Add sample messages
                sample_messages = [
                    {"role": "user", "content": "I've been feeling anxious lately.", "sentiment": -0.3, "risk": 0.2},
                    {"role": "assistant", "content": "I understand that you're feeling anxious. Can you tell me more about what's been triggering these feelings?", "sentiment": 0.5, "risk": 0.0},
                    {"role": "user", "content": "It's mostly work stress. I have so many deadlines.", "sentiment": -0.4, "risk": 0.3},
                    {"role": "assistant", "content": "Work stress is very common. Have you tried any stress management techniques?", "sentiment": 0.4, "risk": 0.0},
                ]
                
                for msg_data in sample_messages:
                    message = Message(
                        conversation_id=conversation.id,
                        role=msg_data["role"],
                        content=msg_data["content"],
                        sentiment_score=msg_data["sentiment"],
                        risk_score=msg_data["risk"],
                        created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48))
                    )
                    db.add(message)
                
                await db.commit()
        
        print("Database seeded successfully!")
        print("\nTest credentials:")
        print("Username: john_doe, Password: password123")
        print("Username: jane_smith, Password: password123")

if __name__ == "__main__":
    asyncio.run(seed_data())