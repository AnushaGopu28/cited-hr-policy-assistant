"""Evaluate questions using retrieval and the answer-generation pipeline.

Human-review scores are intentionally left blank.
"""

import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from app.retrieval import retrieve
from app.answer import answer_question, determination_safety_response
import requests

_original_post = requests.post
_ollama_call = {"attempted": False, "status": None, "error": False}

def tracked_post(*args, **kwargs):
    _ollama_call["attempted"] = True
    try:
        response = _original_post(*args, **kwargs)
        _ollama_call["status"] = response.status_code
        return response
    except Exception:
        _ollama_call["error"] = True
        raise

requests.post = tracked_post

MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")


def main():
    questions_path = ROOT / "eval" / "questions.csv"
    output_path = ROOT / "eval" / "run_outputs_ollama_fresh.csv"

    with questions_path.open(encoding="utf-8", newline="") as f:
        questions = list(csv.DictReader(f))

    if not questions:
        print("No evaluation questions found.")
        return

    output = []

    for number, row in enumerate(questions, start=1):
        question = row["question"]
        passages = retrieve(question)
        safety_response = determination_safety_response(question)

        _ollama_call.update(attempted=False, status=None, error=False)
        answer = answer_question(question, passages)

        if safety_response:
            response_path = "deterministic_safety_response"
        elif not passages:
            response_path = "no_passages_fallback"
        elif not _ollama_call["attempted"]:
            response_path = "pre_model_fallback"
        elif _ollama_call["error"] or _ollama_call["status"] != 200:
            response_path = "ollama_error"
        elif answer.strip() == "I can't find this in the approved documents, please ask HR":
            response_path = "ollama_fallback"
        else:
            response_path = "ollama_response"
        retrieved = " | ".join(
            f'{p.get("source_title", "")} - '
            f'{p.get("section_or_page", "")}'
            for p in passages
        )

        output.append({
            **row,
            "model": MODEL,
            "response_path": response_path,
            "actual_answer": answer,
            "retrieved_sources": retrieved,
            "groundedness_0_2": "",
            "relevance_0_2": "",
            "citation_correct_0_1": "",
            "refusal_correct_0_1": "",
            "reviewer_notes": "Pending independent human review.",
        })

        print(f"Processed {number}/{len(questions)}: {row['question_id']}")

    fields = list(output[0].keys())

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)

    print(f"\nCompleted {len(output)} questions.")
    print(f"Model configured: {MODEL}")
    print(f"Results saved to: {output_path}")
    print("Human-review scores remain blank; no scores were invented.")


if __name__ == "__main__":
    main()