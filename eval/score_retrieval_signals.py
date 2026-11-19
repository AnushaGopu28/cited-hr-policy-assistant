
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"

QUESTIONS = EVAL / "robustness_questions.csv"
RESULTS = EVAL / "retrieval_signals_comparison.csv"
OUTPUT = EVAL / "retrieval_signals_scorecard.csv"

SECTION_MAP = {
    "1": {
        "Before starting", "Day 1", "Days 1ΓÇô2", "Days 2ΓÇô3",
        "End of week", "First-week checklist",
        "Helpful question to HR", "Identity and payroll forms"
    },
    "2": {
        "Recording time", "Every workweek",
        "Submission deadline", "Corrections and records",
        "Pay schedule", "Payroll questions"
    },
    "3": {
        "Unexpected absence", "Requesting planned time away",
        "Family or medical leave questions", "Coverage and handoff"
    },
    "4": {
        "Data handling", "Company equipment", "Device security",
        "Software and access", "Meetings and availability",
        "Remote-work approval", "Ergonomics and safety",
        "Urgent security incident"
    },
    "5": {
        "Before buying", "Approval before spending",
        "Submitting an expense", "Review and payment",
        "Receipts and records", "Days 3ΓÇô5"
    },
    "6": {
        "Urgent security incident", "Escalation order",
        "Device security"
    }
}


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def expected_sections(hint):
    expected = set()
    for number in re.findall(r"\d+", hint):
        expected.update(SECTION_MAP.get(number, set()))
    return expected


def main():
    questions = read_csv(QUESTIONS)
    results = read_csv(RESULTS)

    scorecard = []

    for question in questions:
        qid = question["question_id"]
        expected = expected_sections(question["expected_source_hint"])

        for method in ("Semantic", "BM25", "Current_RRF"):
            ranked = sorted(
                [
                    row for row in results
                    if row["question_id"] == qid
                    and row["method"] == method
                ],
                key=lambda row: int(row["rank"])
            )

            sections = [
                row["section_or_page"].strip()
                for row in ranked
            ]

            record = {
                "question_id": qid,
                "category": question["category"],
                "method": method
            }

            for k in (3, 5, 10):
                matched = expected.intersection(sections[:k])
                record[f"top{k}_hit"] = int(bool(matched))
                record[f"top{k}_matched_sections"] = " ; ".join(
                    sorted(matched)
                )

            scorecard.append(record)

    with open(OUTPUT, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=scorecard[0].keys()
        )
        writer.writeheader()
        writer.writerows(scorecard)

    print("QUESTION | SEMANTIC TOP3 | BM25 TOP3 | RRF TOP3")

    for question in questions:
        qid = question["question_id"]
        values = {}

        for method in ("Semantic", "BM25", "Current_RRF"):
            row = next(
                x for x in scorecard
                if x["question_id"] == qid
                and x["method"] == method
            )
            values[method] = row["top3_hit"]

        print(
            qid, "|",
            values["Semantic"], "|",
            values["BM25"], "|",
            values["Current_RRF"]
        )

    print("\nSUMMARY")

    for metric in ("top3_hit", "top5_hit", "top10_hit"):
        print("\n" + metric)

        for method in ("Semantic", "BM25", "Current_RRF"):
            values = [
                row[metric]
                for row in scorecard
                if row["method"] == method
            ]
            percentage = sum(values) / len(values) * 100
            print(f"{method}: {percentage:.2f}%")

    print("\nSaved:", OUTPUT)


if __name__ == "__main__":
    main()
