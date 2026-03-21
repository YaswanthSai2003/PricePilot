from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PricePilot"
    app_version: str = "1.0.0"
    debug: bool = True

    database_url: str = "sqlite:///./pricepilot.db"
    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str = ""
    openai_model: str = "stepfun/step-3.5-flash:free"

    site_url: str = "http://localhost:8000"
    site_name: str = "PricePilot"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
