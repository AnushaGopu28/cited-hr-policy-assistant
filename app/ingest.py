"""Ingest approved government PDFs and public web sources into FAISS."""

import csv
import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
INDEX_DIR = ROOT / "index"

MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2"
)

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

# Official government sources mapped to locally available PDFs.
LOCAL_PDF_MAP = {
    "Recordkeeping and Reporting": "fact_sheet_21.pdf",
    "Handy Reference Guide to the Fair Labor Standards Act":
        "recordkeeping.pdf",
    "Family and Medical Leave Act Employee Guide":
        "fmla_employee_guide.pdf",
    "Family and Medical Leave Act": "fmla_fact_sheet_28.pdf",

    "Form I-9, Employment Eligibility Verification (PDF)":
        "form_i9.pdf",
    "Instructions for Form I-9 (PDF)":
        "form_i9_instructions.pdf",
}


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def read_pdf(path):
    reader = PdfReader(str(path))
    return [
        (page.extract_text() or "", f"page {i + 1}")
        for i, page in enumerate(reader.pages)
    ]


def read_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml"
    }

    response = requests.get(url, timeout=30, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else url
    text = soup.get_text(" ", strip=True)

    return title, text




def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    text = clean(text)

    if size <= 0:
        raise ValueError("CHUNK_SIZE must be greater than zero")

    if overlap < 0 or overlap >= size:
        raise ValueError(
            "CHUNK_OVERLAP must be non-negative and smaller than CHUNK_SIZE"
        )

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + size, len(text))

        if end < len(text):
            # Prefer a sentence boundary.
            boundary = text.rfind(
                ". ", start + int(size * 0.65), end
            )

            if boundary != -1:
                end = boundary + 1
            else:
                # Otherwise, split at the last complete word.
                boundary = text.rfind(" ", start, end)

                if boundary > start:
                    end = boundary

        piece = text[start:end].strip()

        if piece:
            chunks.append(piece)

        if end >= len(text):
            break

        # Calculate the next starting position.
        next_start = max(start + 1, end - overlap)

        # Move forward to the next word boundary if necessary.
        if next_start > 0 and text[next_start - 1] != " ":
            next_space = text.find(" ", next_start, end)

            if next_space != -1:
                next_start = next_space + 1

        if next_start <= start:
            raise ValueError("Chunking failed to make forward progress")

        start = next_start

    return chunks



def add_pdf_records(records, path, source_title, source_url):
    pages = read_pdf(path)

    for page_text, page_label in pages:
        for n, chunk in enumerate(chunk_text(page_text)):
            records.append({
                "text": chunk,
                "source_title": source_title,
                "source_url": source_url,
                "section_or_page": page_label,
                "chunk_id": (
                    f"{source_title}-{page_label}-{n}"
                ),
                "source_type": "local government PDF",
                "local_file": path.name
            })

    return len(pages)
def add_markdown_records(records, path, source_title, source_url):
    text = path.read_text(encoding="utf-8-sig")

    current_section = source_title
    section_number = 0
    section_lines = []
    total_chunks = 0

    def save_section():
        nonlocal total_chunks

        content = "\n".join(section_lines).strip()

        if not content:
            return

        for n, chunk in enumerate(chunk_text(content)):
            records.append({
                "text": chunk,
                "source_title": source_title,
                "source_url": source_url,
                "section_or_page": current_section,
                "chunk_id": f"handbook-{section_number}-{n}",
                "source_type": "local approved Markdown",
                "local_file": path.name
            })

            total_chunks += 1

    for line in text.splitlines():
        if line.startswith("#"):
            save_section()

            section_number += 1
            current_section = line.lstrip("#").strip()
            section_lines = []
        else:
            section_lines.append(line)

    save_section()

    return total_chunks


def main():
    INDEX_DIR.mkdir(exist_ok=True)

    records = []
    failed_sources = []
    successful_sources = set()

    with (ROOT / "sources.csv").open(
        encoding="utf-8-sig"
    ) as f:
        source_rows = list(csv.DictReader(f))

    print("Processing approved sources...\n")
    handbook_path = CORPUS / "consultant_handbook.md"

    if not handbook_path.exists():
        raise FileNotFoundError(
            f"Approved handbook not found: {handbook_path}"
        )

    handbook_chunks = add_markdown_records(
        records,
        handbook_path,
        "Pine Harbor Analytics Consultant Handbook",
        "local://consultant_handbook.md"
    )

    successful_sources.add(
        "Pine Harbor Analytics Consultant Handbook"
    )

    print(
        f"SUCCESS: Local Markdown handbook "
        f"({handbook_chunks} chunks)"
    )
    for row in source_rows:
        title = row["title"]
        url = row["url"]

        try:
            if title in LOCAL_PDF_MAP:
                pdf_path = CORPUS / LOCAL_PDF_MAP[title]

                if not pdf_path.exists():
                    raise FileNotFoundError(
                        f"Local PDF not found: {pdf_path}"
                    )

                page_count = add_pdf_records(
                    records, pdf_path, title, url
                )

                successful_sources.add(title)

                print(
                    f"SUCCESS: Local PDF: {title} "
                    f"({page_count} pages)"
                )

            else:
                web_title, text = read_html(url)

                if len(text.strip()) < 200:
                    raise ValueError(
                        "Insufficient page text"
                    )

                for n, chunk in enumerate(chunk_text(text)):
                    records.append({
                        "text": chunk,
                        "source_title": title,
                        "source_url": url,
                        "section_or_page": f"web chunk {n + 1}",
                        "chunk_id": f"web-{len(records)}-{n}",
                        "source_type": "government website",
                        "local_file": None
                    })

                successful_sources.add(title)
                print(f"SUCCESS: Website: {title}")

        except Exception as e:
            failed_sources.append({
                "title": title,
                "url": url,
                "reason": str(e)
            })

            print(f"FAILED: {title} - {e}")

    if not records:
        raise RuntimeError("No documents were indexed.")

    print("\nGenerating embeddings...")

    model = SentenceTransformer(MODEL_NAME)

    vectors = model.encode(
        [r["text"] for r in records],
        normalize_embeddings=True,
        show_progress_bar=True
    )

    vectors = np.asarray(vectors, dtype="float32")

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    faiss.write_index(
        index,
        str(INDEX_DIR / "approved.faiss")
    )

    (INDEX_DIR / "chunks.json").write_text(
        json.dumps(records, indent=2),
        encoding="utf-8"
    )

    report = {
        "indexed_chunks": len(records),
        "successful_sources": sorted(successful_sources),
        "failed_sources": failed_sources,
        "embedding_model": MODEL_NAME
    }

    (INDEX_DIR / "ingestion_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print("\n========== INGESTION REPORT ==========")
    print("Indexed chunks:", len(records))
    print("Successful sources:", len(successful_sources))
    print("Failed sources:", len(failed_sources))

    for source in failed_sources:
        print("\nUNVERIFIED:", source["title"])
        print("URL:", source["url"])
        print("Reason:", source["reason"])

    print("\nFAISS index and chunks.json created successfully.")


if __name__ == "__main__":
    main()