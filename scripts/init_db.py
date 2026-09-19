import asyncio
import os
from app.db.base import Base
from app.db.session import engine, AsyncSessionLocal
from app.db.models import user, group, document, question, review
from app.core.security import get_password_hash
from sqlalchemy import select

async def main():
    os.makedirs("data/storage", exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database schema successfully created!")

    # Seed demo user
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(user.User).where(user.User.email == "demo@docintel.com"))
        existing = res.scalar_one_or_none()
        if not existing:
            demo_user = user.User(
                email="demo@docintel.com",
                hashed_password=get_password_hash("DemoPassword123!")
            )
            db.add(demo_user)
            await db.commit()
            print("Demo user created: demo@docintel.com / DemoPassword123!")
        else:
            print("Demo user already exists: demo@docintel.com")

if __name__ == "__main__":
    asyncio.run(main())
