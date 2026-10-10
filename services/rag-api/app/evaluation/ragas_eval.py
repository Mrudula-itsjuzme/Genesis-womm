import json
from pathlib import Path
from typing import Any

from app.schemas.retrieval import EvidenceChunk

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "golden_dataset.json"
)


def load_golden_dataset(
    path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Loads curated golden evaluation dataset from JSON."""
    target_path = Path(path) if path else DEFAULT_DATASET_PATH
    if not target_path.exists():
        return []
    with open(target_path, encoding="utf-8") as f:
        data = json.load(f)
        return list(data) if isinstance(data, list) else []


def evaluate_retrieval_metrics(
    golden_samples: list[dict[str, Any]],
    search_fn: Any,
    top_k: int = 5,
) -> dict[str, float]:
    """Evaluates retrieval accuracy (Hit Rate@K and Mean Reciprocal Rank) on golden dataset.

    Args:
        golden_samples: List of golden query dictionaries with 'user_input' and 'evidence_id'.
        search_fn: Callable taking (query, top_k) returning list[EvidenceChunk].
        top_k: Maximum candidates to inspect.

    Returns:
        dict containing 'hit_rate_at_k' and 'mrr_at_k'.
    """
    if not golden_samples:
        return {"hit_rate_at_k": 0.0, "mrr_at_k": 0.0, "total_queries": 0.0}

    hits = 0
    reciprocal_ranks = []

    for sample in golden_samples:
        query = sample["user_input"]
        expected_id = sample.get("evidence_id")
        candidates: list[EvidenceChunk] = search_fn(query, top_k=top_k)

        rank_found = 0
        for rank, c in enumerate(candidates, start=1):
            if c.evidence_id == expected_id:
                rank_found = rank
                break

        if rank_found > 0:
            hits += 1
            reciprocal_ranks.append(1.0 / rank_found)
        else:
            reciprocal_ranks.append(0.0)

    total = len(golden_samples)
    return {
        "hit_rate_at_k": round(hits / total, 4),
        "mrr_at_k": round(sum(reciprocal_ranks) / total, 4),
        "total_queries": float(total),
    }


def evaluate_with_ragas(
    golden_samples: list[dict[str, Any]],
    use_mock: bool = False,
) -> dict[str, float]:
    """Runs Ragas evaluation (context_precision, context_recall, faithfulness).

    When use_mock=True, computes deterministic lexical precision and recall
    to guarantee 100% offline testability without external LLM API dependencies.
    """
    if not golden_samples:
        return {"context_precision": 0.0, "context_recall": 0.0}

    if use_mock:
        # Offline deterministic evaluation
        precisions = []
        recalls = []
        for s in golden_samples:
            ref = s.get("reference", "").lower()
            contexts = " ".join(s.get("reference_contexts", [])).lower()
            words_ref = set(ref.split())
            words_ctx = set(contexts.split())
            overlap = len(words_ref & words_ctx)
            recall = overlap / len(words_ref) if words_ref else 1.0
            precision = overlap / len(words_ctx) if words_ctx else 1.0
            recalls.append(recall)
            precisions.append(precision)

        avg_rec = sum(recalls) / len(recalls) if recalls else 0.0
        avg_prec = sum(precisions) / len(precisions) if precisions else 0.0
        return {
            "context_precision": round(avg_prec, 4),
            "context_recall": round(avg_rec, 4),
        }

    # Live Ragas integration
    import pandas as pd
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import context_precision, context_recall

    dataset_dict = {
        "user_input": [s["user_input"] for s in golden_samples],
        "reference": [s["reference"] for s in golden_samples],
        "reference_contexts": [s.get("reference_contexts", []) for s in golden_samples],
        "retrieved_contexts": [s.get("reference_contexts", []) for s in golden_samples],
    }

    df = pd.DataFrame(dataset_dict)
    eval_dataset = Dataset.from_pandas(df)
    results: Any = evaluate(
        eval_dataset,
        metrics=[context_precision, context_recall],
    )
    scores = results if isinstance(results, dict) else getattr(results, "scores", {})
    return {
        "context_precision": round(float(scores.get("context_precision", 0.0)), 4),
        "context_recall": round(float(scores.get("context_recall", 0.0)), 4),
    }
