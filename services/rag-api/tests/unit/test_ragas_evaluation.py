from app.evaluation.ragas_eval import (
    evaluate_retrieval_metrics,
    evaluate_with_ragas,
    load_golden_dataset,
)
from app.schemas.retrieval import EvidenceChunk


def test_load_golden_dataset():
    dataset = load_golden_dataset()
    assert len(dataset) >= 20

    first = dataset[0]
    required_keys = {"id", "user_input", "reference", "reference_contexts", "evidence_id", "category"}
    assert required_keys.issubset(set(first.keys()))
    assert len(first["user_input"]) > 10
    assert len(first["reference"]) > 10
    assert len(first["reference_contexts"]) >= 1


def test_evaluate_retrieval_metrics_perfect_hit():
    samples = [
        {
            "user_input": "Auditorium booking form",
            "evidence_id": "osa_handbook_cbr-p24-c01",
        },
        {
            "user_input": "Student affairs office",
            "evidence_id": "student_affairs_welfare-p1-c01",
        },
    ]

    def mock_search(query: str, top_k: int = 5):
        if "Auditorium" in query:
            return [
                EvidenceChunk(
                    evidence_id="osa_handbook_cbr-p24-c01",
                    document_id="osa",
                    title="Form",
                    source_url="https://example.com",
                    excerpt="Booking form",
                    page_start=24,
                    page_end=24,
                )
            ]
        return [
            EvidenceChunk(
                evidence_id="student_affairs_welfare-p1-c01",
                document_id="welfare",
                title="Welfare",
                source_url="https://example.com",
                excerpt="Office location",
                page_start=1,
                page_end=1,
            )
        ]

    metrics = evaluate_retrieval_metrics(samples, mock_search, top_k=3)
    assert metrics["hit_rate_at_k"] == 1.0
    assert metrics["mrr_at_k"] == 1.0
    assert metrics["total_queries"] == 2.0


def test_evaluate_retrieval_metrics_miss():
    samples = [{"user_input": "Unknown query", "evidence_id": "missing_id"}]

    def mock_search(query: str, top_k: int = 5):
        return []

    metrics = evaluate_retrieval_metrics(samples, mock_search, top_k=3)
    assert metrics["hit_rate_at_k"] == 0.0
    assert metrics["mrr_at_k"] == 0.0


def test_evaluate_with_ragas_mock():
    samples = [
        {
            "user_input": "Where is the office?",
            "reference": "Ground Floor Academic Block 1",
            "reference_contexts": ["The office is located on Ground Floor Academic Block 1."],
        }
    ]
    results = evaluate_with_ragas(samples, use_mock=True)
    assert "context_precision" in results
    assert "context_recall" in results
    assert results["context_recall"] >= 0.8
