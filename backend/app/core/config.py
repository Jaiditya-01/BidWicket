from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MONGO_URI: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENVIRONMENT: str = "development"

    FRONTEND_BASE_URL: str = "http://localhost:5173"

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    ALLOWED_HOSTS: str = "localhost,127.0.0.1"

    EMAIL_VERIFY_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    EMAIL_FROM: str = "no-reply@bidwicket.local"

    GEMINI_API_KEY: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
