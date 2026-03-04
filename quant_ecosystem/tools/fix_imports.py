import os
import re
from pathlib import Path

PROJECT_ROOT = Path(".")
PACKAGE = "quant_ecosystem"

FOLDERS = [
    "core",
    "execution",
    "intelligence",
    "market",
    "portfolio",
    "reporting",
    "research",
    "risk",
    "strategy_bank",
    "strategy_lab",
    "utils",
]

pattern_from = re.compile(r'^from\s+(core|execution|intelligence|market|portfolio|reporting|research|risk|strategy_bank|strategy_lab|utils)\.')
pattern_import = re.compile(r'^import\s+(core|execution|intelligence|market|portfolio|reporting|research|risk|strategy_bank|strategy_lab|utils)\.')

changed_files = []

for path in PROJECT_ROOT.rglob("*.py"):

    if ".venv" in str(path):
        continue

    text = path.read_text(encoding="utf-8")

    new_text = text

    new_text = pattern_from.sub(
        lambda m: f"from {PACKAGE}.{m.group(1)}.", new_text
    )

    new_text = pattern_import.sub(
        lambda m: f"import {PACKAGE}.{m.group(1)}", new_text
    )

    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        changed_files.append(str(path))

print("\nUpdated files:")
for f in changed_files:
    print("✔", f)

print(f"\nTotal updated: {len(changed_files)}")