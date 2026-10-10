from typing import List, Tuple
from app.schemas.retrieval import EvidenceChunk
from app.config import settings


class GroundedGenerator:
    """Synthesizes grounded answers strictly from supplied evidence using Groq (or offline mock)."""

    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock or not settings.groq_api_key
        self._client = None

    def generate_answer(
        self, query: str, evidence_chunks: List[EvidenceChunk]
    ) -> Tuple[str, str]:
        if not evidence_chunks:
            return (
                "Insufficient evidence available in the approved campus policy documents to answer this question.",
                "insufficient_evidence",
            )

        context_text = "\n\n".join(
            [f"[{c.evidence_id}] {c.excerpt}" for c in evidence_chunks]
        )

        if self.use_mock:
            # Deterministic synthesis for test suite
            return (
                "Based on the policy excerpt, events require submission 14 days in advance.",
                "grounded",
            )

        # Real Groq API client
        if self._client is None:
            from groq import Groq

            self._client = Groq(api_key=settings.groq_api_key)
        client = self._client
        system_prompt = (
            "You are the CampusCue University Policy Assistant. You must answer questions ONLY using "
            "the provided evidence excerpts below. If the evidence does not clearly contain the answer, "
            "state 'INSUFFICIENT_EVIDENCE'. Never guess or extrapolate."
        )
        user_prompt = f"Evidence:\n{context_text}\n\nQuestion: {query}"

        try:
            response = client.chat.completions.create(
                model=settings.groq_model,
                temperature=settings.groq_temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            if not response.choices:
                return (
                    "Insufficient evidence found in campus policy documents.",
                    "insufficient_evidence",
                )
            content = response.choices[0].message.content or ""
        except Exception:
            return (
                "Insufficient evidence found in campus policy documents.",
                "insufficient_evidence",
            )

        if "INSUFFICIENT_EVIDENCE" in content:
            return (
                "Insufficient evidence found in campus policy documents.",
                "insufficient_evidence",
            )
        return content, "grounded"
