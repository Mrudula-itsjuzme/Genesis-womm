from unittest.mock import MagicMock, patch

import pytest
from app.generation.groq_client import GroundedGenerator
from app.schemas.retrieval import EvidenceChunk


def test_mock_grounded_generator():
    generator = GroundedGenerator(use_mock=True)
    chunks = [
        EvidenceChunk(
            evidence_id="osa-p12",
            document_id="osa",
            title="Handbook",
            source_url="http://x",
            page_start=12,
            page_end=12,
            excerpt="Events require submission 14 days in advance.",
        )
    ]
    answer, status = generator.generate_answer(
        query="What is the deadline for event submission?", evidence_chunks=chunks
    )
    assert status == "grounded"
    assert "14 days" in answer


def test_mock_grounded_generator_abstention_on_empty_evidence():
    generator = GroundedGenerator(use_mock=True)
    answer, status = generator.generate_answer(
        query="What is the policy for drones?", evidence_chunks=[]
    )
    assert status == "insufficient_evidence"
    assert "Insufficient evidence" in answer


def test_default_use_mock_when_api_key_empty(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "groq_api_key", "")
    generator = GroundedGenerator()
    assert generator.use_mock is True


def test_real_groq_client_grounded_response(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "groq_api_key", "gsk-test-key")
    generator = GroundedGenerator(use_mock=False)
    assert generator.use_mock is False

    mock_chat_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Events require submission 14 days prior to date."
    mock_chat_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_chat_completion

    with patch("groq.Groq", return_value=mock_client):
        chunks = [
            EvidenceChunk(
                evidence_id="osa-p12",
                document_id="osa",
                title="Handbook",
                source_url="http://x",
                page_start=12,
                page_end=12,
                excerpt="Events require submission 14 days in advance.",
            )
        ]
        answer, status = generator.generate_answer(
            query="When to submit events?", evidence_chunks=chunks
        )
        assert status == "grounded"
        assert answer == "Events require submission 14 days prior to date."

        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == settings.groq_model
        assert call_kwargs["temperature"] == settings.groq_temperature
        messages = call_kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "Insufficient evidence" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert '<evidence id="osa-p12"' in messages[1]["content"]
        assert "Events require submission 14 days in advance." in messages[1]["content"]
        assert "When to submit events?" in messages[1]["content"]


def test_real_groq_client_abstention_on_insufficient_evidence_content(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "groq_api_key", "gsk-test-key")
    generator = GroundedGenerator(use_mock=False)

    mock_chat_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = (
        "INSUFFICIENT_EVIDENCE: The document does not specify."
    )
    mock_chat_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_chat_completion

    with patch("groq.Groq", return_value=mock_client):
        chunks = [
            EvidenceChunk(
                evidence_id="osa-p12",
                document_id="osa",
                title="Handbook",
                source_url="http://x",
                page_start=12,
                page_end=12,
                excerpt="Some general information.",
            )
        ]
        answer, status = generator.generate_answer(
            query="What about drones?", evidence_chunks=chunks
        )
        assert status == "insufficient_evidence"
        assert answer == "Insufficient evidence found in campus policy documents."


def test_real_groq_client_abstention_on_empty_evidence_bypasses_api(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "groq_api_key", "gsk-test-key")
    generator = GroundedGenerator(use_mock=False)

    with patch("groq.Groq") as mock_groq_cls:
        answer, status = generator.generate_answer(
            query="What is the policy for drones?", evidence_chunks=[]
        )
        assert status == "insufficient_evidence"
        assert "Insufficient evidence" in answer
        mock_groq_cls.assert_not_called()


def test_real_groq_client_empty_choices_handled(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "groq_api_key", "gsk-test-key")
    generator = GroundedGenerator(use_mock=False)

    mock_chat_completion = MagicMock()
    mock_chat_completion.choices = []

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_chat_completion

    with patch("groq.Groq", return_value=mock_client):
        chunks = [
            EvidenceChunk(
                evidence_id="osa-p12",
                document_id="osa",
                title="Handbook",
                source_url="http://x",
                page_start=12,
                page_end=12,
                excerpt="Some general information.",
            )
        ]
        answer, status = generator.generate_answer(
            query="When to submit events?", evidence_chunks=chunks
        )
        assert status == "insufficient_evidence"
        assert answer == "Insufficient evidence found in campus policy documents."


def test_real_groq_client_exception_handled(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "groq_api_key", "gsk-test-key")
    generator = GroundedGenerator(use_mock=False)

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception(
        "Groq API rate limit or network error"
    )

    with patch("groq.Groq", return_value=mock_client):
        chunks = [
            EvidenceChunk(
                evidence_id="osa-p12",
                document_id="osa",
                title="Handbook",
                source_url="http://x",
                page_start=12,
                page_end=12,
                excerpt="Some general information.",
            )
        ]
        with pytest.raises(RuntimeError) as exc_info:
            generator.generate_answer(
                query="When to submit events?", evidence_chunks=chunks
            )
        assert "Upstream generation provider unavailable" in str(exc_info.value)


def test_real_groq_client_configured_with_timeouts_and_retries(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "groq_api_key", "gsk-test-key")
    generator = GroundedGenerator(use_mock=False)

    with patch("groq.Groq") as mock_groq_cls:
        generator._get_client()
        mock_groq_cls.assert_called_once()
        _, kwargs = mock_groq_cls.call_args
        assert kwargs["api_key"] == "gsk-test-key"
        assert kwargs["max_retries"] == 2
        from httpx import Timeout

        assert kwargs["timeout"] == Timeout(15.0, connect=5.0)


def test_real_groq_client_caches_instance(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "groq_api_key", "gsk-test-key")
    generator = GroundedGenerator(use_mock=False)

    mock_choice = MagicMock()
    mock_choice.message.content = "Answer from groq"
    mock_chat_completion = MagicMock(choices=[mock_choice])

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_chat_completion

    with patch("groq.Groq", return_value=mock_client) as mock_groq_cls:
        chunks = [
            EvidenceChunk(
                evidence_id="osa-p12",
                document_id="osa",
                title="Handbook",
                source_url="http://x",
                page_start=12,
                page_end=12,
                excerpt="Info",
            )
        ]
        generator.generate_answer(query="Q1", evidence_chunks=chunks)
        generator.generate_answer(query="Q2", evidence_chunks=chunks)

        assert mock_groq_cls.call_count == 1
        assert mock_client.chat.completions.create.call_count == 2


def test_generator_wraps_evidence_in_xml_delimiters():
    generator = GroundedGenerator(api_key="mock-key", use_mock=False)
    chunk = EvidenceChunk(
        evidence_id="osa-p12-c01",
        document_id="osa",
        title="Handbook",
        source_url="https://example.com",
        page_start=12,
        page_end=12,
        excerpt="Important rule",
    )
    prompt = generator._build_user_prompt("What is rule?", [chunk])
    assert "<evidence_corpus>" in prompt
    assert '<evidence id="osa-p12-c01"' in prompt
    assert "<user_question>" in prompt
    assert "</user_question>" in prompt


def test_generator_raises_on_upstream_api_failure(monkeypatch):
    generator = GroundedGenerator(api_key="mock-key", use_mock=False)
    chunk = EvidenceChunk(
        evidence_id="osa-p12-c01",
        document_id="osa",
        title="Handbook",
        source_url="https://example.com",
        page_start=12,
        page_end=12,
        excerpt="Important rule",
    )

    class FailingClient:
        class chat:
            class completions:
                @staticmethod
                def create(*args, **kwargs):
                    raise ConnectionError("Groq API connection timeout")

    monkeypatch.setattr(generator, "_get_client", lambda: FailingClient())
    with pytest.raises(RuntimeError) as exc_info:
        generator.generate_answer("query", [chunk])
    assert "Upstream generation provider unavailable" in str(exc_info.value)
