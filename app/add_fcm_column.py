import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "mysql+asyncmy://carrot_user:carrot123@127.0.0.1:3306/carrot"

async def add_fcm_token_column():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        try:
            # users 테이블에 fcm_token 컬럼 추가
            await conn.execute(text("ALTER TABLE users ADD COLUMN fcm_token VARCHAR(500) NULL AFTER neighborhood"))
            print("Successfully added 'fcm_token' column to 'users' table.")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("Column 'fcm_token' already exists.")
            else:
                print(f"Error adding column: {e}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_fcm_token_column())
