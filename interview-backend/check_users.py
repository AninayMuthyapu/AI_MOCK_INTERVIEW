"""
Script to check users in the database.
Run with: python check_users.py
"""

import asyncio
from sqlalchemy import text
from database import AsyncSessionLocal

async def check_users():
    """Fetch and display all users from the database."""
    async with AsyncSessionLocal() as session:
        # Query all users
        result = await session.execute(text("""
            SELECT id, email, name, provider, created_at 
            FROM users 
            ORDER BY created_at DESC
        """))
        
        users = result.fetchall()
        
        if not users:
            print("No users found in the database.")
            return
        
        print(f"\n{'='*80}")
        print(f"Found {len(users)} user(s) in the database:")
        print(f"{'='*80}\n")
        
        for user in users:
            print(f"ID:       {user.id}")
            print(f"Email:    {user.email}")
            print(f"Name:     {user.name}")
            print(f"Provider: {user.provider}")
            print(f"Created:  {user.created_at}")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(check_users())
