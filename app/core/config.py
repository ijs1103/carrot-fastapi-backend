from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Carrot Market Backend"
    
    # Database connection string using asyncmy driver for MySQL
    DATABASE_URL: str = "mysql+asyncmy://carrot_user:carrot123@127.0.0.1:3306/carrot"
    
    # Secret key for JWT encode/decode
    SECRET_KEY: str = "carrot_market_super_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days expire

    class Config:
        env_file = ".env"

settings = Settings()
