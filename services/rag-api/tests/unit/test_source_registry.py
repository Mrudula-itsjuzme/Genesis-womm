import pytest
from app.ingestion.source_registry import SourceRegistry, SourceEntry


def test_get_allowed_source():
    entry = SourceRegistry.get_by_id("osa_handbook_cbr")
    assert entry is not None
    assert entry.source_id == "osa_handbook_cbr"
    assert entry.format == "pdf"
    assert "student-affairs-handbook-cbr.pdf" in entry.url
    assert entry.access_level == "CAMPUS_PUBLIC"


def test_get_student_affairs_welfare():
    entry = SourceRegistry.get_by_id("student_affairs_welfare")
    assert entry is not None
    assert entry.source_id == "student_affairs_welfare"
    assert entry.format == "html"
    assert entry.url == "https://intranet.cb.amrita.edu/students-affairs-welfare"


def test_get_nonexistent_source():
    assert SourceRegistry.get_by_id("unknown_id") is None
    assert SourceRegistry.get_by_url("https://unknown.amrita.edu") is None


def test_is_allowed_url():
    assert SourceRegistry.is_allowed(
        "https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf"
    )
    assert not SourceRegistry.is_allowed("https://random-unauthorized-site.com/doc.pdf")


def test_validate_url_success():
    entry = SourceRegistry.validate_url(
        "https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf"
    )
    assert isinstance(entry, SourceEntry)
    assert entry.source_id == "osa_handbook_cbr"


def test_disallowed_source_raises():
    with pytest.raises(ValueError, match="Disallowed or unregistered source"):
        SourceRegistry.validate_url("https://malicious-site.com/exploit.pdf")
