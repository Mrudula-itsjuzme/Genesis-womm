import os
import requests
from bs4 import BeautifulSoup
from typing import List

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCES_FILE = os.path.join(BASE_DIR, "../../sources.txt")


def fetch_html(url: str) -> str:
    """Fetch and extract text from an HTML page."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"Error fetching HTML {url}: {e}")
        return ""


def fetch_pdf(url: str) -> str:
    """Fetch and extract text from a PDF."""
    print(f"Fetching PDF placeholder for: {url}")
    # In a real scenario, use PyPDF2 or pdfplumber here.
    return "PDF Content Placeholder"


def chunk_document(text: str, chunk_size: int = 500) -> List[str]:
    """Simulates splitting text into ~500 word chunks."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks


def parse_sources(file_path: str) -> List[str]:
    """Parses the sources.txt file and returns a list of URLs."""
    urls = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
    except FileNotFoundError:
        print(f"Sources file not found at {file_path}")
    return urls


def process_sources():
    urls = parse_sources(SOURCES_FILE)
    for url in urls:
        print(f"Processing {url}")
        if url.lower().endswith(".pdf"):
            text = fetch_pdf(url)
        else:
            text = fetch_html(url)
        
        chunks = chunk_document(text)
        print(f"Created {len(chunks)} chunks for {url}")


if __name__ == "__main__":
    process_sources()
