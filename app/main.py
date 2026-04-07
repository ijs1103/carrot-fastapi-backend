from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import engine, Base
from app.api import auth, products, posts, reports

app = FastAPI(title=settings.PROJECT_NAME)

# CORS setup for future React Native / Frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(posts.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    # Automatically create tables for Local Development purpose without Alembic
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
def root():
    return {"message": "Welcome to Carrot Market FastAPI Backend"}
