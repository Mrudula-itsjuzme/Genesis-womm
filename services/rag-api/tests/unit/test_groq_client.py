from unittest.mock import MagicMock, patch
from app.schemas.retrieval import EvidenceChunk
from app.generation.groq_client import GroundedGenerator


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
        assert "INSUFFICIENT_EVIDENCE" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "[osa-p12] Events require submission 14 days in advance." in messages[1]["content"]
        assert "When to submit events?" in messages[1]["content"]


def test_real_groq_client_abstention_on_insufficient_evidence_content(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "groq_api_key", "gsk-test-key")
    generator = GroundedGenerator(use_mock=False)

    mock_chat_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "INSUFFICIENT_EVIDENCE: The document does not specify."
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
