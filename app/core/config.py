import json
from typing import List, Literal, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    ENVIRONMENT: Literal["development", "testing", "staging", "production"] = "development"
    PROJECT_NAME: str = "Payment Service"
    API_V1_STR: str = "/api/v1"

    # Database Settings
    DATABASE_URL: str = "sqlite:///./payment.db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # Security Settings
    SECRET_KEY: str = "supersecretkeyplaceholder"
    API_KEY: str = "localdevapikeyplaceholder"

    # CORS Origins
    BACKEND_CORS_ORIGINS: Union[List[str], str] = []

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            if isinstance(v, str):
                try:
                    return json.loads(v)
                except Exception:
                    return [v]
            return v
        return []

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            insecure_secrets = ("supersecretkeyplaceholder", "devsecretkey12345678901234567890")
            insecure_api_keys = ("localdevapikeyplaceholder", "devapikey123")
            if self.SECRET_KEY in insecure_secrets:
                raise ValueError("Insecure default SECRET_KEY cannot be used in a production environment!")
            if self.API_KEY in insecure_api_keys:
                raise ValueError("Insecure default API_KEY cannot be used in a production environment!")
        return self


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
