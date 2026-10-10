from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    campus_timezone: str = Field(default="Asia/Kolkata")
    rag_api_port: int = Field(default=8002)
    agent_model_provider: str = Field(default="groq")
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    groq_temperature: float = Field(default=0.0)

    rag_embedding_provider: str = Field(default="local")
    rag_embedding_model: str = Field(default="BAAI/bge-base-en-v1.5")
    rag_embedding_device: str = Field(default="cpu")
    rag_sparse_provider: str = Field(default="splade")

    data_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data")
    log_level: str = Field(default="INFO")


settings = Settings()
