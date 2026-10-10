#!/usr/bin/env python3
"""Script to download and pre-cache local AI models for CampusCue RAG Service.

Models are downloaded to the standard HuggingFace local cache (~/.cache/huggingface/hub)
and are strictly excluded from the Git repository.
"""

import argparse
import sys
import time


def download_dense_model(model_name: str = "BAAI/bge-base-en-v1.5") -> None:
    print(f"\n[1/3] Downloading Dense Embedding Model: {model_name} (768 dimensions)...")
    start = time.time()
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    dim = model.get_embedding_dimension() if hasattr(model, "get_embedding_dimension") else model.get_sentence_embedding_dimension()
    elapsed = time.time() - start
    print(f"  ✓ {model_name} loaded successfully in {elapsed:.2f}s (embedding dimension: {dim})")


def download_cross_encoder(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
    print(f"\n[2/3] Downloading Cross-Encoder Re-ranker: {model_name}...")
    start = time.time()
    from sentence_transformers import CrossEncoder

    _ = CrossEncoder(model_name)
    elapsed = time.time() - start
    print(f"  ✓ {model_name} loaded successfully in {elapsed:.2f}s")


def download_splade_model(model_name: str = "naver/splade-cocondenser-ensembledistil") -> None:
    print(f"\n[3/3] Downloading Neural Sparse (SPLADE) Model: {model_name}...")
    start = time.time()
    from transformers import AutoModelForMaskedLM, AutoTokenizer

    AutoTokenizer.from_pretrained(model_name)
    AutoModelForMaskedLM.from_pretrained(model_name)
    elapsed = time.time() - start
    print(f"  ✓ {model_name} loaded successfully in {elapsed:.2f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and cache local models for CampusCue RAG.")
    parser.add_argument(
        "--dense-model",
        default="BAAI/bge-base-en-v1.5",
        help="Dense embedding model identifier (default: BAAI/bge-base-en-v1.5, 768d)",
    )
    parser.add_argument(
        "--reranker-model",
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        help="Cross-encoder re-ranker identifier",
    )
    parser.add_argument(
        "--splade-model",
        default="naver/splade-cocondenser-ensembledistil",
        help="SPLADE neural sparse model identifier",
    )
    parser.add_argument(
        "--skip-splade",
        action="store_true",
        help="Skip downloading the SPLADE neural sparse model",
    )
    args = parser.parse_args()

    print("=" * 65)
    print(" CampusCue RAG Service: Local Model Download & Pre-Cache ")
    print("=" * 65)
    print("Note: Models are cached under ~/.cache/huggingface/hub/")
    print("      Model weights are strictly excluded from the Git repository.")

    try:
        download_dense_model(args.dense_model)
        download_cross_encoder(args.reranker_model)
        if not args.skip_splade:
            download_splade_model(args.splade_model)
        print("\n" + "=" * 65)
        print(" All local models are ready for offline execution!")
        print("=" * 65)
    except Exception as exc:  # noqa: BLE001
        print(f"\nError downloading models: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
