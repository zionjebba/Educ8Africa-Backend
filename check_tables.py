from app.core.database import session_manager
from sqlalchemy import text
import asyncio

async def list_tables():
    # Initialize the session manager first
    await session_manager.init()

    async with session_manager.get_session() as db:
        result = await db.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public';
        """))
        tables = [row[0] for row in result]
        print("✅ Tables in database:", tables)

asyncio.run(list_tables())
