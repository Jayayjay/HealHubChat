#!/usr/bin/env python3
import asyncio
import logging
from app.db.database import AsyncSessionLocal
from app.models.models import User
from app.core.security import is_password_hash_valid, get_password_hash
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_invalid_passwords():
    """Find and fix users with invalid password hashes"""
    db = AsyncSessionLocal()
    try:
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        fixed_count = 0
        for user in users:
            if user.password and not is_password_hash_valid(user.password):
                logger.info(f"Fixing invalid hash for user: {user.username}")
                # Set a temporary password that user must change
                user.password = get_password_hash("TempPassword123!")
                fixed_count += 1
        
        if fixed_count > 0:
            await db.commit()
            logger.info(f"Fixed {fixed_count} user passwords")
        else:
            logger.info("No invalid password hashes found")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        await db.rollback()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(migrate_invalid_passwords())