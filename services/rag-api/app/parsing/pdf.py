import io
from typing import List, Optional
from pydantic import BaseModel
from pypdf import PdfReader


class ParsedPage(BaseModel):
    page_number: int
    text: str
    section_breadcrumb: Optional[str] = None


class PDFParser:
    """Extracts text page-by-page from PDFs preserving 1-indexed page boundaries."""

    def parse_bytes(self, pdf_bytes: bytes) -> List[ParsedPage]:
        if not pdf_bytes:
            return []

        stream = io.BytesIO(pdf_bytes)
        try:
            reader = PdfReader(stream)
            pages = reader.pages
            # Test reader length or access to ensure it's not a malformed payload
            _ = len(pages)
        except Exception:
            return []

        parsed_pages: List[ParsedPage] = []
        current_heading = ""

        for page_idx, page in enumerate(pages):
            page_num = page_idx + 1
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            cleaned = text.strip()

            lines = cleaned.splitlines()
            if lines and (lines[0].startswith("Chapter") or lines[0].isupper()):
                current_heading = lines[0].strip()

            parsed_pages.append(
                ParsedPage(
                    page_number=page_num,
                    text=cleaned,
                    section_breadcrumb=current_heading if current_heading else None,
                )
            )

        return parsed_pages

    def parse_file(self, file_path: str) -> List[ParsedPage]:
        with open(file_path, "rb") as f:
            return self.parse_bytes(f.read())
