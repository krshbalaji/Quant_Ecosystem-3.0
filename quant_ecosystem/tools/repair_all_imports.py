import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MODULES = [
    "core",
    "control",
    "broker",
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

changed = []

for file in ROOT.rglob("*.py"):

    if "venv" in str(file):
        continue

    text = file.read_text(encoding="utf-8")
    new = text

    for m in MODULES:

        new = re.sub(
            rf"from {m}\.",
            f"from quant_ecosystem.{m}.",
            new
        )

        new = re.sub(
            rf"import {m}\.",
            f"import quant_ecosystem.{m}.",
            new
        )

        new = re.sub(
            rf"from {m} import",
            f"from quant_ecosystem.{m} import",
            new
        )

    if new != text:
        file.write_text(new, encoding="utf-8")
        changed.append(file)

print("\nUpdated:")
for f in changed:
    print("✔", f)

print("\nTotal:", len(changed))