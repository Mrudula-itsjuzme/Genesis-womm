import logging

import groq
from groq import Groq
from httpx import Timeout

from app.config import settings
from app.schemas.retrieval import EvidenceChunk

logger = logging.getLogger("campuscue.rag.generator")


class GroundedGenerator:
    """Generates cited answers strictly grounded in retrieved evidence using Groq."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        use_mock: bool = False,
    ):
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self.temperature = (
            temperature if temperature is not None else settings.groq_temperature
        )
        self.use_mock = use_mock or not bool(self.api_key)
        self._client: Groq | None = None

    def _get_client(self) -> Groq:
        if self._client is None:
            self._client = groq.Groq(
                api_key=self.api_key,
                timeout=Timeout(15.0, connect=5.0),
                max_retries=2,
            )
        return self._client

    def _build_user_prompt(self, query: str, candidates: list[EvidenceChunk]) -> str:
        context_blocks = []
        for c in candidates:
            context_blocks.append(
                f'<evidence id="{c.evidence_id}" title="{c.title}" page="{c.page_start}">\n{c.excerpt}\n</evidence>'
            )
        context_text = "\n\n".join(context_blocks)

        return (
            "Review the enclosed campus policy evidence inside the XML tags to answer the user question.\n\n"
            f"<evidence_corpus>\n{context_text}\n</evidence_corpus>\n\n"
            f"<user_question>\n{query}\n</user_question>\n\n"
            "Provide a concise, grounded answer based strictly on the evidence above. "
            "Cite relevant evidence IDs in brackets (e.g. [evidence_id]) where appropriate."
        )

    def _mock_generation(
        self, query: str, candidates: list[EvidenceChunk]
    ) -> tuple[str, str]:
        return (
            "Based on the policy excerpt, events require submission 14 days in advance.",
            "grounded",
        )

    def generate_answer(
        self,
        query: str,
        candidates: list[EvidenceChunk] | None = None,
        evidence_chunks: list[EvidenceChunk] | None = None,
    ) -> tuple[str, str]:
        chunks = candidates if candidates is not None else (evidence_chunks or [])
        if not chunks:
            return (
                "Insufficient evidence found in campus policy documents to answer this question.",
                "insufficient_evidence",
            )

        if self.use_mock:
            return self._mock_generation(query, chunks)

        system_prompt = (
            "You are CampusCue Assistant, an authoritative AI operations assistant for university clubs. "
            "Answer the question based STRICTLY and ONLY on the provided evidence excerpts. "
            "Do not invent, assume, or extrapolate policies, timelines, approvals, or facilities. "
            "If the provided evidence does not contain sufficient information to answer the question with certainty, "
            'respond with EXACTLY: "Insufficient evidence found in campus policy documents."'
        )

        user_prompt = self._build_user_prompt(query, chunks)

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.model,
                temperature=self.temperature,
            )
            if not response.choices:
                return (
                    "Insufficient evidence found in campus policy documents.",
                    "insufficient_evidence",
                )
            content = response.choices[0].message.content or ""
        except Exception as exc:
            logger.exception("Upstream Groq API invocation failed")
            raise RuntimeError(
                f"Upstream generation provider unavailable: {exc}"
            ) from exc

        if (
            "insufficient evidence" in content.lower()
            or "insufficient_evidence" in content.lower()
        ):
            return (
                "Insufficient evidence found in campus policy documents.",
                "insufficient_evidence",
            )

        return (content, "grounded")
