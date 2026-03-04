import re
import uuid
from pathlib import Path

class StrategyConverter:

    def __init__(self):

        self.raw_path = Path("strategy_bank/raw")
        self.validated_path = Path("strategy_bank/validated")

    # -------------------------------------------------

    def ingest(self, strategy_text):

        strategy_id = str(uuid.uuid4())[:8]

        file = self.raw_path / f"{strategy_id}.txt"

        with open(file, "w", encoding="utf-8") as f:
            f.write(strategy_text)

        print(f"Strategy stored → {file}")

        parsed = self.parse(strategy_text)

        return self.generate_strategy(parsed, strategy_id)

    # -------------------------------------------------

    def parse(self, text):

        rules = {}

        # Detect SMA
        sma = re.findall(r"SMA\((\d+)\)", text)
        if sma:
            rules["sma"] = list(map(int, sma))

        # Detect RSI
        rsi = re.findall(r"RSI\((\d+)\)", text)
        if rsi:
            rules["rsi"] = int(rsi[0])

        # Detect BUY condition
        if "cross" in text.lower():
            rules["logic"] = "crossover"

        return rules

    # -------------------------------------------------

    def generate_strategy(self, rules, strategy_id):

        code = f"""
def strategy(data):

    close = data["close"]

"""

        if "sma" in rules:

            sma1 = rules["sma"][0]
            sma2 = rules["sma"][-1]

            code += f"""

    if len(close) < {sma2}:
        return "HOLD"

    sma_fast = sum(close[-{sma1}:]) / {sma1}
    sma_slow = sum(close[-{sma2}:]) / {sma2}

    if sma_fast > sma_slow:
        return "BUY"

    if sma_fast < sma_slow:
        return "SELL"

"""

        code += """

    return "HOLD"
"""

        file = self.validated_path / f"{strategy_id}.py"

        with open(file, "w", encoding="utf-8") as f:
            f.write(code)

        print("Strategy compiled →", file)

        return file
