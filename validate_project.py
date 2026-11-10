"""Static project validation; does not claim that the model/app/evaluation has been run."""
import csv
from pathlib import Path
ROOT=Path(__file__).resolve().parent
q=list(csv.DictReader((ROOT/"eval/questions.csv").open(encoding="utf-8")))
s=list(csv.DictReader((ROOT/"eval/security_tests.csv").open(encoding="utf-8")))
src=list(csv.DictReader((ROOT/"sources.csv").open(encoding="utf-8")))
assert len(q)>=25, f"Expected >=25 questions, got {len(q)}"
assert sum(x["category"]=="answerable" for x in q)>=15
assert sum(x["category"]=="unanswerable" for x in q)>=5
assert sum(x["category"]=="determination" for x in q)>=5
assert len(src)>=5, f"Expected >=5 sources, got {len(src)}"
assert len([x for x in s if x["test_type"]=="direct_jailbreak"])>=3
assert any(x["test_type"]=="indirect_prompt_injection" for x in s)
assert (ROOT/"corpus/consultant_handbook.pdf").exists()
assert (ROOT/"app/app.py").exists()
print("PASS: static structure checks only.")
print(f"Questions: {len(q)}; sources: {len(src)}; security cases: {len(s)}")
print("NOTE: This does not validate live URLs, model quality, citations, or security outcomes.")
