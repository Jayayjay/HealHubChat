import asyncio
from app.db.database import engine, Base
from app.models.models import User, Conversation, Message, UserAnalytics

async def init_db():
    async with engine.begin() as conn:
        # Drop all tables (use with caution!)
        # await conn.run_sync(Base.metadata.drop_all)
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())