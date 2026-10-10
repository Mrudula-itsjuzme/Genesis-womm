from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_rag_pipeline_flow():
    # 1. Check health
    health_res = client.get("/health")
    assert health_res.status_code == 200

    # 2. Check search (no LLM required)
    search_res = client.post(
        "/v1/retrieval/search", json={"query": "venue approval", "top_k": 2}
    )
    assert search_res.status_code == 200
    candidates = search_res.json()["candidates"]
    assert len(candidates) > 0
    assert candidates[0]["evidence_id"].startswith("osa-2025")

    # 3. Check answer with citations
    answer_res = client.post(
        "/v1/knowledge/answer", json={"query": "venue approval deadline"}
    )
    assert answer_res.status_code == 200
    answer_data = answer_res.json()
    assert answer_data["status"] == "grounded"
    assert len(answer_data["citations"]) > 0
    assert answer_data["citations"][0]["page_start"] == 12
