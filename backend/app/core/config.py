from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List
import json


class Settings(BaseSettings):
    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "ai_cv_skillgap"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""

    # JWT
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    # CÃ¡c model há»— trá»£: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo
    OPENAI_MODEL: str = "gpt-4o-mini"

    # App
    APP_NAME: str = "AI CV Skill Gap"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    ALLOW_DEV_RESET_TOKEN: bool = False
    UPLOAD_DIR: str = "uploads/cvs"
    MAX_FILE_SIZE_MB: int = 10
    TESSERACT_CMD: str = ""
    OCR_LANGUAGES: str = "vie+eng"
    CORS_ORIGINS: str = '["http://localhost:5173","http://localhost:3000"]'

    @model_validator(mode="after")
    def validate_production_config(self):
        if self.ENVIRONMENT.lower() in {"production", "prod"}:
            if len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in production")
            if not self.DB_PASSWORD:
                raise ValueError("DB_PASSWORD is required in production")
            if self.DEBUG:
                raise ValueError("DEBUG must be false in production")
        return self

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.CORS_ORIGINS)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

