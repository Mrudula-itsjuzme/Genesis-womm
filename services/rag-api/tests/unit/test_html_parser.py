from app.parsing.html import HTMLParser, clean_text


def test_clean_text_normalizes_whitespace_and_hyphens():
    raw = "This is a proced-\nure with \xa0 non-breaking \u200bspaces   and\n\n\n\nextra lines."
    cleaned = clean_text(raw)
    assert "procedure" in cleaned
    assert "\xa0" not in cleaned
    assert "\u200b" not in cleaned
    assert "\n\n\n" not in cleaned


def test_html_parser_strips_scripts_and_extracts_sections():
    html = """
    <html>
        <head><title>Student Welfare</title></head>
        <body>
            <nav><a href="/home">Home</a></nav>
            <main>
                <h1>Club Guidelines</h1>
                <p>All clubs must submit event proposals 10 days in advance.</p>
                <h2>Venue Booking</h2>
                <p>Auditorium booking requires faculty advisor endorsement.</p>
            </main>
            <footer>Contact us at info@example.com</footer>
            <script>console.log("tracker");</script>
        </body>
    </html>
    """
    parser = HTMLParser()
    pages = parser.parse_html(html)

    assert len(pages) >= 1
    full_text = " ".join(p.text for p in pages)
    assert "tracker" not in full_text
    assert "Home" not in full_text
    assert "10 days in advance" in full_text
    assert "faculty advisor endorsement" in full_text
    assert any("Venue Booking" in (p.section_breadcrumb or "") for p in pages)


def test_html_parser_empty_content():
    parser = HTMLParser()
    assert parser.parse_html("") == []
    assert parser.parse_html("   ") == []
