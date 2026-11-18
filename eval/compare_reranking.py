
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "eval"

QUESTIONS_FILE = EVAL_DIR / "robustness_questions.csv"
HANDBOOK_FILE = ROOT / "corpus" / "consultant_handbook.md"
RRF_FILE = EVAL_DIR / "rrf_robustness_results.csv"
CE_FILE = EVAL_DIR / "crossencoder_robustness_results.csv"
OUTPUT_FILE = EVAL_DIR / "reranking_comparison_final.csv"

HANDBOOK = "Pine Harbor Analytics Consultant Handbook"


def load_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_heading_map(path):
    """Map each handbook subsection heading to its numbered parent section."""
    heading_map = {}
    current_section = None

    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()

            parent = re.match(r"^##\s+(\d+)\.", line)
            if parent:
                current_section = parent.group(1)
                continue

            subsection = re.match(r"^###\s+(.+)$", line)
            if subsection and current_section:
                heading = subsection.group(1).strip()
                heading_map[heading] = current_section

            # Appendices are not numbered policy sections.
            if re.match(r"^##\s+Appendix", line):
                current_section = None

    return heading_map


def expected_sections(hint):
    return set(re.findall(r"\d+", hint))


def index_results(rows):
    indexed = {}

    for row in rows:
        indexed.setdefault(row["question_id"], []).append(row)

    for qid in indexed:
        indexed[qid].sort(key=lambda r: int(r["rank"]))

    return indexed


questions = load_csv(QUESTIONS_FILE)
rrf = index_results(load_csv(RRF_FILE))
ce = index_results(load_csv(CE_FILE))
heading_map = build_heading_map(HANDBOOK_FILE)

output = []

for question in questions:
    qid = question["question_id"]
    expected = expected_sections(question["expected_source_hint"])

    for method, results in [("RRF", rrf), ("CrossEncoder", ce)]:
        ranked = results.get(qid, [])

        # Keep original global ranks. Only count approved handbook passages
        # whose subsection maps to an expected numbered policy section.
        def retrieved_sections(top_k):
            found = set()

            for row in ranked:
                if int(row["rank"]) > top_k:
                    continue

                if row["source_title"].strip() != HANDBOOK:
                    continue

                section_number = heading_map.get(
                    row["section_or_page"].strip()
                )

                if section_number:
                    found.add(section_number)

            return found

        sections3 = retrieved_sections(3)
        sections5 = retrieved_sections(5)
        sections10 = retrieved_sections(10)

        matched10 = expected.intersection(sections10)

        output.append({
            "question_id": qid,
            "method": method,
            "expected_sections": ";".join(sorted(expected)),
            "retrieved_sections_top3": ";".join(sorted(sections3)),
            "retrieved_sections_top5": ";".join(sorted(sections5)),
            "retrieved_sections_top10": ";".join(sorted(sections10)),
            "top3_any_section_hit": int(bool(expected & sections3)),
            "top5_any_section_hit": int(bool(expected & sections5)),
            "top10_any_section_hit": int(bool(matched10)),
            "top10_complete_section_hit": int(
                bool(expected) and expected.issubset(sections10)
            ),
            "top10_section_coverage": (
                round(len(matched10) / len(expected), 4)
                if expected else ""
            )
        })


with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(output[0].keys()))
    writer.writeheader()
    writer.writerows(output)


print("QUESTION | METHOD | TOP3 | TOP5 | TOP10 | COMPLETE | COVERAGE")
print("-" * 75)

for row in output:
    print(
        row["question_id"], "|",
        row["method"], "|",
        row["top3_any_section_hit"], "|",
        row["top5_any_section_hit"], "|",
        row["top10_any_section_hit"], "|",
        row["top10_complete_section_hit"], "|",
        row["top10_section_coverage"]
    )


print("\nSUMMARY")
print("-" * 75)

for method in ["RRF", "CrossEncoder"]:
    subset = [r for r in output if r["method"] == method]
    total = len(subset)

    print(f"\n{method} ({total} questions)")

    for metric in [
        "top3_any_section_hit",
        "top5_any_section_hit",
        "top10_any_section_hit",
        "top10_complete_section_hit",
        "top10_section_coverage"
    ]:
        average = sum(float(r[metric]) for r in subset) / total
        print(f"{metric}: {average * 100:.2f}%")


print("\nHandbook subsection headings mapped:", len(heading_map))
print("Questions evaluated:", len(questions))
print("Methods evaluated: RRF and CrossEncoder")
print("Saved:", OUTPUT_FILE)
