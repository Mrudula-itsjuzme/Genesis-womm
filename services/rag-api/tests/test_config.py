import pytest
from app.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.rag_api_port == 8002
    assert settings.rag_embedding_provider == "local"
    assert settings.rag_embedding_model == "all-MiniLM-L6-v2"
    assert settings.agent_model_provider == "groq"
    assert settings.rag_sparse_provider == "splade"


def test_settings_override(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_12345")
    monkeypatch.setenv("RAG_API_PORT", "8010")
    settings = Settings()
    assert settings.groq_api_key == "gsk_test_12345"
    assert settings.rag_api_port == 8010
