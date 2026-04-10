import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "mysql+asyncmy://carrot_user:carrot123@127.0.0.1:3306/carrot"

async def check_tokens():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT id, username, fcm_token FROM users WHERE fcm_token IS NOT NULL"))
        rows = result.fetchall()
        if not rows:
            print("No users with FCM tokens found.")
        for row in rows:
            print(f"User ID: {row[0]}, Username: {row[1]}, Token prefix: {row[2][:20]}...")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_tokens())
