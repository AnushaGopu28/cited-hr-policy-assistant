"""Run all questions through the RAG app and evaluate retrieval hits."""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.retrieval import retrieve
from app.answer import answer_question


def retrieval_hit(row, passages):
    category = row["category"].strip().lower()
    hint = row["expected_source_hint"].strip().lower()

    handbook_passages = [
        p for p in passages
        if "pine harbor analytics consultant handbook"
        in p.get("source_title", "").lower()
    ]

    if category == "answerable":
        source_titles = " ".join(
        p.get("source_title", "").lower() for p in passages
        )

        unanswerable_sources = {
            "Q16": ["form w-4", "topic no. 753"],
            "Q19": ["publication 463"],
        }

        expected_sources = unanswerable_sources.get(
            row["question_id"], []
        )

        if any(source in source_titles for source in expected_sources):
            return 1
        match = re.search(r"handbook sections? ([0-9]+)", hint)
        if not match:
            return 0

        expected_section = int(match.group(1))

        section_titles = {
            1: {
                "before the first day", "day 1", "days 1–2",
                "days 2–3", "days 3–5", "end of week",
                "access troubleshooting", "identity and payroll forms",
                "project readiness", "first-week checklist",
                "what is not specified",
            },
            2: {
                "time-entry system", "recording time",
                "submission deadline", "manager approval",
                "payroll questions", "pay schedule",
                "corrections and records", "tax forms",
                "w-2 questions", "important boundary",
            },
            3: {
                "requesting planned time away", "company holidays",
                "unexpected absence", "leave documentation",
                "coverage and handoff", "family or medical leave questions",
                "military, jury, and other leave",
                "no automated eligibility decisions",
                "not specified in source", "helpful question to hr",
            },
            4: {
                "company equipment", "device security",
                "remote-work environment", "data handling",
                "remote-work approval", "software and access",
                "meetings and availability", "ergonomics and safety",
                "return of equipment",
            },
            5: {
                "approval before spending", "submitting an expense",
                "receipts and records", "travel expenses",
                "non-reimbursable examples", "review and payment",
                "tax questions", "expense privacy", "disputed expense",
                "public reference boundary",
            },
            6: {
                "fictional contacts", "escalation order",
                "urgent security incident", "what the assistant can do",
                "when information is missing",
            },
        }

        expected_titles = section_titles.get(expected_section, set())

        return int(any(
            p.get("section_or_page", "").strip().lower() in expected_titles
            for p in handbook_passages
        ))

    if category == "unanswerable":
        source_titles = " ".join(
        p.get("source_title", "").lower() for p in passages
        )

        unanswerable_sources = {
            "Q16": ["form w-4", "topic no. 753"],
            "Q19": ["publication 463"],
        }

        expected_sources = unanswerable_sources.get(
            row["question_id"], []
        )

        if any(source in source_titles for source in expected_sources):
            return 1

        relevant_terms = {
            "Q16": {"payroll questions", "pay schedule", "not specified in source"},
            "Q17": {"pay schedule", "payroll questions"},
            "Q18": {"remote-work approval", "not specified in source"},
            "Q19": {"travel expenses", "non-reimbursable examples", "review and payment"},
            "Q20": {"fictional contacts", "first-week checklist", "day 1"},
        }

        expected = relevant_terms.get(row["question_id"], set())

        return int(any(
            p.get("section_or_page", "").strip().lower() in expected
            for p in handbook_passages
        ))
    if category == "determination":
        source_titles = " ".join(
        p.get("source_title", "").lower() for p in passages
        )

        determination_sources = {
            "Q21": ["family and medical leave act"],
            "Q22": ["form i-9"],
            "Q23": ["instructions for form i-9", "publication 463"],
            "Q24": ["publication 463"],
        }

        expected_sources = determination_sources.get(
            row["question_id"], []
        )

        if any(source in source_titles for source in expected_sources):
            return 1
        relevant_terms = {
            "Q21": {"family or medical leave questions", "no automated eligibility decisions"},
            "Q22": {"identity and payroll forms", "approved documents"},
            "Q23": {"determination request", "what the assistant can do"},
            "Q24": {"tax questions", "public reference boundary"},
            "Q25": {"company holidays", "not specified in source"},
        }

        expected = relevant_terms.get(row["question_id"], set())

        return int(any(
            p.get("section_or_page", "").strip().lower() in expected
            for p in handbook_passages
        ))

    return 0


def main():
    questions = list(
        csv.DictReader((ROOT / "eval" / "questions.csv").open(encoding="utf-8"))
    )

    out = []

    for row in questions:
        passages = retrieve(row["question"])
        response = answer_question(row["question"], passages)

        retrieved = " | ".join(
            p.get("source_title", "") + " " + p.get("section_or_page", "")
            for p in passages
        )

        hit = retrieval_hit(row, passages)

        out.append({
            **row,
            "actual_answer": response,
            "retrieved_source_ids": retrieved,
            "groundedness_0_2": "",
            "relevance_0_2": "",
            "refusal_correct_0_1": "",
            "retrieval_hit_0_1": hit,
            "reviewer_notes": "Human review required; scores intentionally not auto-invented.",
        })

    fields = list(out[0].keys())

    with (ROOT / "eval" / "run_outputs.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out)

    total_hits = sum(row["retrieval_hit_0_1"] for row in out)

    print(f"Completed {len(out)} questions.")
    print(f"Retrieval hits: {total_hits}/{len(out)}")
    print("Groundedness, relevance, and refusal scores remain blank for human review.")


if __name__ == "__main__":
    main()