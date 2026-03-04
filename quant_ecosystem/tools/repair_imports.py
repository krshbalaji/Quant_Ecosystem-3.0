import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MODULES = [
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
    "utils"
]

pattern = re.compile(r'^from (' + "|".join(MODULES) + r')\.')

changed = []

for file in ROOT.rglob("*.py"):

    if "venv" in str(file):
        continue

    text = file.read_text(encoding="utf-8")

    new = pattern.sub(r'from quant_ecosystem.\1.', text)

    if new != text:
        file.write_text(new, encoding="utf-8")
        changed.append(file)

print("\nUpdated imports in:")
for f in changed:
    print("✔", f)

print(f"\nTotal files updated: {len(changed)}")