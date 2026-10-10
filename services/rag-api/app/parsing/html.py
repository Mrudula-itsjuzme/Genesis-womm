import re

import bs4

from app.parsing.pdf import ParsedPage


def clean_text(text: str) -> str:
    """Normalize whitespace, remove zero-width artifacts, and repair line wraps."""
    if not text:
        return ""
    # Replace non-breaking spaces and zero-width characters
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "")
    # Fix hyphenated words across line breaks (e.g. "approv-\nal" -> "approval")
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
    # Normalize multiple whitespace within lines
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ consecutive newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class HTMLParser:
    """Extracts clean, structured text and section breadcrumbs from HTML content."""

    def parse_html(self, html_content: str, default_title: str = "") -> list[ParsedPage]:
        if not html_content or not html_content.strip():
            return []

        soup = bs4.BeautifulSoup(html_content, "html.parser")

        # Decompose non-content elements
        for tag in soup(
            ["script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg"]
        ):
            tag.decompose()

        # Target main content area if available, fallback to body
        container = (
            soup.find("main")
            or soup.find("article")
            or soup.find(class_=re.compile(r"content|entry|post-body|main", re.IGNORECASE))
            or soup.body
            or soup
        )

        page_title = default_title
        if not page_title:
            title_tag = soup.find("title") or soup.find("h1")
            if title_tag:
                page_title = clean_text(title_tag.get_text())

        # Extract sections structured by headings
        pages: list[ParsedPage] = []
        current_heading = page_title
        current_lines: list[str] = []

        for element in container.find_all(["h1", "h2", "h3", "h4", "p", "li", "tr"]):
            text = clean_text(element.get_text(separator=" ", strip=True))
            if not text:
                continue

            if element.name in ["h1", "h2", "h3", "h4"]:
                # When encountering a new section heading, flush accumulated lines
                if current_lines:
                    combined_text = "\n".join(current_lines).strip()
                    if len(combined_text) > 40:
                        pages.append(
                            ParsedPage(
                                page_number=len(pages) + 1,
                                text=combined_text,
                                section_breadcrumb=current_heading,
                            )
                        )
                    current_lines = []
                current_heading = f"{page_title} > {text}" if page_title else text
            else:
                current_lines.append(text)

        # Flush final section
        if current_lines:
            combined_text = "\n".join(current_lines).strip()
            if combined_text:
                pages.append(
                    ParsedPage(
                        page_number=len(pages) + 1,
                        text=combined_text,
                        section_breadcrumb=current_heading,
                    )
                )

        if not pages:
            raw_text = clean_text(container.get_text(separator="\n", strip=True))
            if raw_text:
                pages.append(
                    ParsedPage(
                        page_number=1,
                        text=raw_text,
                        section_breadcrumb=page_title,
                    )
                )

        return pages
