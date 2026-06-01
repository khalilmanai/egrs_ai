from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "EGRS AI Service"
    debug: bool = False
    api_prefix: str = "/api/v1"

    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "orange_user"
    db_password: str = "orange_password"
    db_name: str = "E-GRS_DB"
    db_min_size: int = 5
    db_max_size: int = 20

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    @property
    def redis_url(self) -> str:
        pw = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{pw}{self.redis_host}:{self.redis_port}"

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout: int = 600

    vector_dimension: int = 12
    vector_similarity_metric: str = "cosine"

    chromium_path: str = ""

    report_storage_path: str = "reports/storage"
    report_ttl_days: int = 7

    cors_origins: list[str] = ["*"]

    class Config:
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
