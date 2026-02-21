import asyncio
from sqlalchemy import text
from database import engine
import sys

async def list_tables():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public';"))
            print("\nTables found in 'public' schema:")
            tables = [row[0] for row in result]
            if not tables:
                print("No tables found.")
            else:
                for table in tables:
                    print(f"- {table}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(list_tables())
