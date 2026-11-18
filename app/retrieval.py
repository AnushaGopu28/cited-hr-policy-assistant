
"""General hybrid retrieval using semantic similarity and keyword overlap."""

import json
import os
import re
from rank_bm25 import BM25Okapi
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
_bm25 = None
_bm25_signature = None

STOP_WORDS = {
    "i", "who", "what", "when", "where", "why", "how",
    "is", "are", "was", "were", "the", "a", "an",
    "of", "for", "to", "in", "on", "at", "by",
    "and", "or", "can", "do", "does", "did",
    "be", "being", "been", "with", "from",
    "should", "my", "your", "our", "their", "during", "assignment",
    "include", "which", "this", "that"
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


def normalize_word(word):
    """Apply lightweight, general word-form normalization."""
    if word.startswith("complet"):
        return "complet"

    if len(word) > 5 and word.endswith("ing"):
        word = word[:-3]
        if len(word) > 2 and word[-1] == word[-2]:
            word = word[:-1]
        return word

    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"

    if len(word) > 4 and word.endswith(
        ("ches", "shes", "xes", "zes", "sses", "oes")
    ):
        return word[:-2] if word.endswith(("ches", "shes", "xes", "zes", "sses", "oes")) else word[:-1]

    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]

    return word

SYNONYMS = {
    "paid": {"reimburse", "reimbursement"},
    "back": {"reimburse", "reimbursement"},
    "reimbursed": {"reimburse", "reimbursement"},
    "reimbursement": {"reimburse", "expense", "submission", "submit"},
    "reimburse": {"reimbursement", "expense", "submission", "submit"},
    "detail": {"information", "provide"},
    "cutoff": {"deadline"},
    "weekly": {"week"},
    "hour": {"time"},
    "timesheet": {"time"},
    "submit": {"submission"},
    "submitted": {"submit", "submission"},
    "submission": {"submit"},
    "customer": {"client", "work"},
    "document": {"file", "work"},
    "drive": {"storage", "repository"},
    "google": {"personal", "storage"},
    "save": {"store", "upload"},
    "cloud": {"storage", "repository"},
}

def tokenize(text):
    """Normalize text and expand common workplace synonyms."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    terms = set()

    for word in words:
        if word in STOP_WORDS:
            continue

        normalized = normalize_word(word)
        terms.add(normalized)
        terms.update(SYNONYMS.get(normalized, set()))

    return sorted(terms)
def bm25_tokenize(text):
    """Tokenize text for BM25 with general synonym expansion."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    terms = []

    for word in words:
        if word in STOP_WORDS:
            continue

        normalized = normalize_word(word)
        if normalized in STOP_WORDS:
            continue

        terms.append(normalized)
        terms.extend(sorted(SYNONYMS.get(normalized, set())))

    return terms
def keyword_score(query, text, section="", source_title="", idf=None):
    """Score keyword overlap using corpus-wide inverse document frequency."""
    query_terms = set(tokenize(query))

    if not query_terms:
        return 0.0

    body_terms = set(tokenize(text))
    section_terms = set(tokenize(section))
    source_terms = set(tokenize(source_title))

    if idf is None:
        idf = {}

    weights = {
        term: idf.get(term, 1.0)
        for term in query_terms
    }

    total_weight = sum(weights.values())

    if total_weight == 0:
        return 0.0

    body_score = sum(
        weights[term] for term in query_terms & body_terms
    ) / total_weight

    section_score = sum(
        weights[term] for term in query_terms & section_terms
    ) / total_weight

    source_score = sum(
        weights[term] for term in query_terms & source_terms
    ) / total_weight

    return min(
        1.0,
        (0.70 * body_score)
        + (0.20 * section_score)
        + (0.10 * source_score)
    )
def build_bm25(chunks):
    """Build and reuse a BM25 index for approved document chunks."""
    global _bm25, _bm25_signature

    signature = hash(tuple(
        (
            chunk.get("chunk_id"),
            chunk.get("text", ""),
            chunk.get("section_or_page", ""),
            chunk.get("source_title", "")
        )
        for chunk in chunks
    ))

    if _bm25 is None or _bm25_signature != signature:
        tokenized_chunks = [
            bm25_tokenize(
                chunk.get("text", "") + " "
                + chunk.get("section_or_page", "") + " "
                + chunk.get("source_title", "")
            )
            for chunk in chunks
        ]

        _bm25 = BM25Okapi(tokenized_chunks)
        _bm25_signature = signature

    return _bm25
def retrieve(query, top_k=None):
    """Retrieve passages using semantic search and BM25 rank fusion."""
    idx, chunks = load()

    if not chunks:
        return []

    k = top_k if top_k is not None else TOP_K
    k = max(1, min(k, len(chunks)))

    candidate_k = min(
        len(chunks),
        max(k * CANDIDATE_MULTIPLIER, MIN_CANDIDATES)
    )

    # Semantic search
    query_embedding = _model.encode(
        [query],
        normalize_embeddings=True
    )

    semantic_scores, semantic_ids = idx.search(
        np.asarray(query_embedding, dtype="float32"),
        candidate_k
    )

    semantic_rank = {
        int(chunk_id): rank
        for rank, chunk_id in enumerate(semantic_ids[0], start=1)
        if chunk_id >= 0
    }

    # BM25 keyword search across the full approved corpus
    bm25 = build_bm25(chunks)
    query_tokens = bm25_tokenize(query)

    bm25_scores = bm25.get_scores(query_tokens)

    bm25_order = np.argsort(bm25_scores)[::-1][:candidate_k]

    bm25_rank = {
        int(chunk_id): rank
        for rank, chunk_id in enumerate(bm25_order, start=1)
    }

    # Combine both rankings using Reciprocal Rank Fusion.
    candidate_ids = set(semantic_rank) | set(bm25_rank)
    results = []

    for chunk_id in candidate_ids:
        item = dict(chunks[chunk_id])

        semantic_position = semantic_rank.get(chunk_id)
        bm25_position = bm25_rank.get(chunk_id)

        fusion_score = 0.0

        if semantic_position is not None:
            fusion_score += 1.0 / (60 + semantic_position)

        if bm25_position is not None:
            fusion_score += 1.0 / (60 + bm25_position)

        item["semantic_rank"] = semantic_position
        item["bm25_rank"] = bm25_position
        item["bm25_score"] = float(bm25_scores[chunk_id])
        item["score"] = fusion_score

        results.append(item)

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return results[:k]
