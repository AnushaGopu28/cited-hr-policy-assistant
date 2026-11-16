
"""General hybrid retrieval using semantic similarity and keyword overlap."""

import json
import os
import re
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
INDEX_DIR = ROOT / "index"

MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2"
)

TOP_K = int(os.getenv("TOP_K", "3"))
CANDIDATE_MULTIPLIER = 50
MIN_CANDIDATES = 200

_model = None

STOP_WORDS = {
    "who", "what", "when", "where", "why", "how",
    "is", "are", "was", "were", "the", "a", "an",
    "of", "for", "to", "in", "on", "at", "by",
    "and", "or", "can", "do", "does", "did",
    "be", "being", "been", "with", "from"
    "should", "my", "your", "our", "their", "during",
    "include", "when", "which", "this", "that"
}


def load():
    global _model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    idx = faiss.read_index(str(INDEX_DIR / "approved.faiss"))

    chunks = json.loads(
        (INDEX_DIR / "chunks.json").read_text(encoding="utf-8")
    )

    return idx, chunks


def tokenize(text):
    """Normalize text into searchable terms."""
    words = re.findall(r"[a-z0-9]+", text.lower())

    normalized = []

    for word in words:
        if word in STOP_WORDS:
            continue

        if word.startswith("complet"):
            word = "complet"

        normalized.append(word)

    return normalized


def keyword_score(query, text, section="", source_title=""):
    """Score keyword overlap separately for passage text and metadata."""
    query_terms = set(tokenize(query))

    if not query_terms:
        return 0.0

    body_terms = set(tokenize(text))
    section_terms = set(tokenize(section))
    source_terms = set(tokenize(source_title))

    body_score = len(query_terms & body_terms) / len(query_terms)
    section_score = len(query_terms & section_terms) / len(query_terms)
    source_score = len(query_terms & source_terms) / len(query_terms)

    return min(
        1.0,
        (0.40 * body_score)
        + (0.50 * section_score)
        + (0.10 * source_score)
    )

def retrieve(query, top_k=None):
    """Retrieve and rank passages using consistent hybrid scoring."""
    idx, chunks = load()

    if not chunks:
        return []

    k = top_k if top_k is not None else TOP_K
    k = max(1, min(k, len(chunks)))

    # Use the same candidate-pool rule for every question.
    candidate_k = min(
        len(chunks),
        max(k * CANDIDATE_MULTIPLIER, MIN_CANDIDATES)
    )

    query_embedding = _model.encode(
        [query],
        normalize_embeddings=True
    )

    semantic_scores, candidate_ids = idx.search(
        np.asarray(query_embedding, dtype="float32"),
        candidate_k
    )

    results = []

    for semantic_score, chunk_index in zip(
        semantic_scores[0],
        candidate_ids[0]
    ):
        if chunk_index < 0:
            continue

        item = dict(chunks[int(chunk_index)])

        semantic = float(semantic_score)
        lexical = keyword_score(
    query,
    item.get("text", ""),
    item.get("section_or_page", ""),
    item.get("source_title", "")
)

        # General hybrid ranking: semantic similarity + keyword overlap.
        combined = (0.50 * semantic) + (0.50 * lexical)

        item["semantic_score"] = semantic
        item["keyword_score"] = lexical
        item["score"] = combined

        results.append(item)

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    # Avoid returning the same source chunk more than once.
    final_results = []
    seen_chunk_ids = set()

    for item in results:
        chunk_id = item.get("chunk_id")

        if chunk_id and chunk_id in seen_chunk_ids:
            continue

        if chunk_id:
            seen_chunk_ids.add(chunk_id)

        final_results.append(item)

        if len(final_results) >= k:
            break

    return final_results
