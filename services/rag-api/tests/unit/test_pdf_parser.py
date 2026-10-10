import io
from unittest.mock import MagicMock
from pypdf import PdfWriter

from app.parsing.pdf import PDFParser, ParsedPage


def _create_mock_pdf_bytes(num_pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=72, height=72)
    stream = io.BytesIO()
    writer.write(stream)
    stream.seek(0)
    return stream.getvalue()


def test_pdf_parser_page_preservation():
    # Test with synthetic multi-page content using ParsedPage models
    pages = [
        ParsedPage(page_number=1, text="Chapter 1: Overview\nWelcome to Amrita Coimbatore."),
        ParsedPage(page_number=2, text="Chapter 2: Club Guidelines\nClubs must register annually."),
    ]
    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert "Overview" in pages[0].text
    assert pages[1].page_number == 2


def test_pdf_parser_rejects_empty_bytes():
    parser = PDFParser()
    result = parser.parse_bytes(b"")
    assert result == []


def test_pdf_parser_rejects_corrupted_bytes():
    parser = PDFParser()
    result = parser.parse_bytes(b"not a valid pdf payload")
    assert result == []


def test_pdf_parser_blank_pdf():
    parser = PDFParser()
    pdf_bytes = _create_mock_pdf_bytes(num_pages=2)
    result = parser.parse_bytes(pdf_bytes)

    assert len(result) == 2
    assert result[0].page_number == 1
    assert result[0].text == ""
    assert result[0].section_breadcrumb is None
    assert result[1].page_number == 2
    assert result[1].text == ""
    assert result[1].section_breadcrumb is None


def test_pdf_parser_breadcrumb_detection_and_persistence(monkeypatch):
    # Mock PdfReader to return pages with specific text content
    parser = PDFParser()

    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Chapter 1: Student Welfare\nRules and regulations"

    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "Continued details without heading\nParagraph two"

    mock_page3 = MagicMock()
    mock_page3.extract_text.return_value = "AUDITORIUM BOOKING POLICIES\nSubmit forms 7 days in advance"

    mock_reader = MagicMock()
    mock_reader.pages = [mock_page1, mock_page2, mock_page3]

    monkeypatch.setattr("app.parsing.pdf.PdfReader", lambda stream: mock_reader)

    result = parser.parse_bytes(b"dummy pdf content")
    assert len(result) == 3

    # Page 1: Chapter heading
    assert result[0].page_number == 1
    assert result[0].section_breadcrumb == "Chapter 1: Student Welfare"
    assert "Rules and regulations" in result[0].text

    # Page 2: Preserves previous heading
    assert result[1].page_number == 2
    assert result[1].section_breadcrumb == "Chapter 1: Student Welfare"
    assert "Continued details" in result[1].text

    # Page 3: New ALL CAPS heading
    assert result[2].page_number == 3
    assert result[2].section_breadcrumb == "AUDITORIUM BOOKING POLICIES"
    assert "Submit forms" in result[2].text


def test_pdf_parser_parse_file(tmp_path):
    parser = PDFParser()
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(_create_mock_pdf_bytes(num_pages=1))

    result = parser.parse_file(str(pdf_path))
    assert len(result) == 1
    assert result[0].page_number == 1
