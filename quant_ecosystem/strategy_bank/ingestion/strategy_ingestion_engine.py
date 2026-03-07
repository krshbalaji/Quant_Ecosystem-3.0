from pathlib import Path


class StrategyIngestionEngine:

    def __init__(self, output_dir="strategy_bank/validated", **kwargs):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def ingest(self, payload, source_type, strategy_id):
        normalized = source_type.strip().lower()
        if normalized == "python":
            return self._from_python(payload, strategy_id)
        if normalized == "pine":
            return self._from_pine(payload, strategy_id)
        if normalized in {"text", "plain"}:
            return self._from_text_logic(payload, strategy_id)
        raise ValueError("Unsupported source type. Use: python | pine | text")

    def _from_python(self, payload, strategy_id):
        body = payload.strip()
        if "def strategy(" not in body:
            raise ValueError("Python strategy must expose: def strategy(data)")
        file = self.output_dir / f"{strategy_id}.py"
        file.write_text(body + "\n", encoding="utf-8")
        return str(file)

    def _from_pine(self, payload, strategy_id):
        logic = "BUY" if "crossover" in payload.lower() else "SELL" if "crossunder" in payload.lower() else "HOLD"
        code = self._strategy_template(strategy_id, logic)
        file = self.output_dir / f"{strategy_id}.py"
        file.write_text(code, encoding="utf-8")
        return str(file)

    def _from_text_logic(self, payload, strategy_id):
        lower = payload.lower()
        logic = "BUY" if "buy" in lower else "SELL" if "sell" in lower else "HOLD"
        code = self._strategy_template(strategy_id, logic)
        file = self.output_dir / f"{strategy_id}.py"
        file.write_text(code, encoding="utf-8")
        return str(file)

    def _strategy_template(self, strategy_id, forced_side):
        return f'''SUPPORTED_REGIMES = ["TREND", "MEAN_REVERSION", "LOW_VOLATILITY"]

class Strategy:
    def generate_signal(self, data, regime, context):
        close = data.get("close", [])
        if len(close) < 30:
            return {{"side": "HOLD", "confidence": 0.0}}
        side = "{forced_side}"
        confidence = 0.62 if side != "HOLD" else 0.0
        return {{"side": side, "confidence": confidence}}

def strategy(data):
    close = data.get("close", [])
    if len(close) < 30:
        return "HOLD"
    return "{forced_side}"
'''
