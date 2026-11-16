
"""Run retrieval-only evaluation without calling the language model."""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.retrieval import retrieve


def main():
    questions_path = ROOT / "eval" / "questions.csv"
    output_path = ROOT / "eval" / "run_outputs.csv"

    with questions_path.open(encoding="utf-8", newline="") as f:
        questions = list(csv.DictReader(f))

    if not questions:
        print("No evaluation questions found.")
        return

    output = []

    for number, row in enumerate(questions, start=1):
        passages = retrieve(row["question"])

        retrieved = " | ".join(
            f'{p.get("source_title", "")} '
            f'{p.get("section_or_page", "")} '
            f'(score: {p.get("score", 0):.3f})'
            for p in passages
        )

        output.append({
            **row,
            "actual_answer": "Not evaluated in retrieval-only mode.",
            "retrieved_source_ids": retrieved,
            "groundedness_0_2": "",
            "relevance_0_2": "",
            "refusal_correct_0_1": "",
            "retrieval_hit_0_1": "",
            "reviewer_notes": (
                "Retrieval results require independent human relevance review."
            ),
        })

        print(f"Processed {number}/{len(questions)} questions.")

    fields = list(output[0].keys())

    with output_path.open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)

    print(f"\nCompleted retrieval for {len(output)} questions.")
    print(f"Results saved to: {output_path}")
    print("No Ollama answer-generation calls were made.")
    print("Retrieval hits are intentionally left blank pending review.")


if __name__ == "__main__":
    main()
