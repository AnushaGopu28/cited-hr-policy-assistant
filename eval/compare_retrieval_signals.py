
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.retrieval import retrieve

EVAL = ROOT / "eval"
QUESTIONS = EVAL / "robustness_questions.csv"
OUTPUT = EVAL / "retrieval_signals_comparison.csv"


def main():
    with open(QUESTIONS, encoding="utf-8-sig", newline="") as f:
        questions = list(csv.DictReader(f))

    rows = []

    for question in questions:
        qid = question["question_id"]
        query = question["question"]

        passages = retrieve(query, top_k=667)

        semantic = sorted(
            passages,
            key=lambda p: (
                p["semantic_rank"]
                if p.get("semantic_rank") is not None
                else 999999
            )
        )

        bm25 = sorted(
            passages,
            key=lambda p: (
                p["bm25_rank"]
                if p.get("bm25_rank") is not None
                else 999999
            )
        )

        rrf = sorted(
            passages,
            key=lambda p: p["score"],
            reverse=True
        )

        for method, ranked in [
            ("Semantic", semantic),
            ("BM25", bm25),
            ("Current_RRF", rrf)
        ]:
            for rank, item in enumerate(ranked[:10], start=1):
                rows.append({
                    "question_id": qid,
                    "question": query,
                    "method": method,
                    "rank": rank,
                    "chunk_id": item.get("chunk_id", ""),
                    "section_or_page": item.get("section_or_page", ""),
                    "source_title": item.get("source_title", ""),
                    "text": item.get("text", "")
                })

    with open(OUTPUT, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print("Questions evaluated:", len(questions))
    print("Methods: Semantic, BM25, Current RRF")
    print("Total saved rows:", len(rows))
    print("Rows per method:", len(questions) * 10)
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
