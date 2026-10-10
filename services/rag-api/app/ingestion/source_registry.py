from typing import Dict, Optional
from pydantic import BaseModel


class SourceEntry(BaseModel):
    source_id: str
    title: str
    url: str
    format: str
    category: str
    treatment: str
    access_level: str = "CAMPUS_PUBLIC"


class SourceRegistry:
    _SOURCES: Dict[str, SourceEntry] = {
        "osa_handbook_cbr": SourceEntry(
            source_id="osa_handbook_cbr",
            title="OSA Student Affairs Handbook",
            url="https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf",
            format="pdf",
            category="policy",
            treatment="Structure-aware PDF parser preserving page numbers and headings",
        ),
        "student_affairs_welfare": SourceEntry(
            source_id="student_affairs_welfare",
            title="Student Affairs and Welfare",
            url="https://intranet.cb.amrita.edu/students-affairs-welfare",
            format="html",
            category="policy",
            treatment="Constrained HTML policy extractor",
        ),
    }

    @classmethod
    def get_by_id(cls, source_id: str) -> Optional[SourceEntry]:
        return cls._SOURCES.get(source_id)

    @classmethod
    def get_by_url(cls, url: str) -> Optional[SourceEntry]:
        for entry in cls._SOURCES.values():
            if entry.url == url:
                return entry
        return None

    @classmethod
    def is_allowed(cls, url: str) -> bool:
        return cls.get_by_url(url) is not None

    @classmethod
    def validate_url(cls, url: str) -> SourceEntry:
        entry = cls.get_by_url(url)
        if not entry:
            raise ValueError(f"Disallowed or unregistered source URL: {url}")
        return entry
