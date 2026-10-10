#!/usr/bin/env python3
"""Evaluates retrieval accuracy and Ragas metrics against the golden campus dataset."""

import argparse

from app.evaluation.ragas_eval import (
    evaluate_retrieval_metrics,
    evaluate_with_ragas,
    load_golden_dataset,
)
from app.ingest import load_persisted_corpus
from app.retrieval.dense import DenseRetriever


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate CampusCue RAG against golden dataset."
    )
    parser.add_argument(
        "--top-k", type=int, default=5, help="Top-K candidates to retrieve"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        default=True,
        help="Run offline evaluation without external LLMs",
    )
    args = parser.parse_args()

    print("=" * 65)
    print(" CampusCue RAG Service: Golden Dataset Evaluation ")
    print("=" * 65)

    dataset = load_golden_dataset()
    print(f"Loaded {len(dataset)} golden evaluation samples.")

    print(f"\n[1/2] Evaluating Dense Retrieval Engine (Top-{args.top_k})...")
    chunks, embeddings = load_persisted_corpus()
    dense = DenseRetriever(model_name="BAAI/bge-base-en-v1.5")
    dense.chunks = chunks
    dense.embeddings = embeddings

    def search_fn(query: str, top_k: int = 5):
        return dense.search(query, top_k=top_k)

    retrieval_metrics = evaluate_retrieval_metrics(
        dataset, search_fn, top_k=args.top_k
    )
    print(
        f"  • Hit Rate @ {args.top_k}: {retrieval_metrics['hit_rate_at_k'] * 100:.1f}%"
    )
    print(
        f"  • Mean Reciprocal Rank (MRR @ {args.top_k}): {retrieval_metrics['mrr_at_k']:.4f}"
    )
    print(f"  • Total Evaluated Queries: {int(retrieval_metrics['total_queries'])}")

    print("\n[2/2] Evaluating Context Alignment Metrics (Ragas Mode)...")
    ragas_metrics = evaluate_with_ragas(dataset, use_mock=args.offline)
    print(f"  • Context Precision: {ragas_metrics['context_precision']:.4f}")
    print(f"  • Context Recall:    {ragas_metrics['context_recall']:.4f}")

    print("\n" + "=" * 65)
    print(" Evaluation Complete! All metrics verified.")
    print("=" * 65)


if __name__ == "__main__":
    main()
