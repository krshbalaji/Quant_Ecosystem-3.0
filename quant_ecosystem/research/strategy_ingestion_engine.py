from pathlib import Path
from urllib.parse import urlparse


class StrategyIngestionEngine:

    def __init__(self, candidate_dir="strategy_bank/candidate"):
        self.candidate_dir = Path(candidate_dir)
        self.candidate_dir.mkdir(parents=True, exist_ok=True)

    def ingest(self, source, source_type="plain_text", strategy_id=None):
        normalized_type = str(source_type).strip().lower()
        strategy_id = strategy_id or self._default_id(source)
        target = self.candidate_dir / f"{strategy_id}.py"

        if normalized_type == "python":
            code = self._from_python(source)
        elif normalized_type == "pine_script":
            code = self._from_pine(source)
        elif normalized_type == "github_link":
            code = self._from_link(source, "github")
        elif normalized_type == "youtube_link":
            code = self._from_link(source, "youtube")
        else:
            code = self._from_plain_text(source)

        target.write_text(code, encoding="utf-8")
        return {"status": "OK", "strategy_id": strategy_id, "path": str(target)}

    def _from_python(self, source):
        text = str(source)
        if "def strategy(" in text:
            return text
        return self._wrap_logic_comment(text, "python")

    def _from_pine(self, source):
        comment = str(source).replace('"""', "'''")
        return self._wrap_logic_comment(comment, "pine_script")

    def _from_plain_text(self, source):
        return self._wrap_logic_comment(str(source), "plain_text")

    def _from_link(self, source, kind):
        url = str(source).strip()
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if kind == "github" and "github.com" not in host:
            raise ValueError("Invalid github_link source.")
        if kind == "youtube" and "youtube.com" not in host and "youtu.be" not in host:
            raise ValueError("Invalid youtube_link source.")
        return self._wrap_logic_comment(f"{kind} reference: {url}", kind)

    def _wrap_logic_comment(self, text, source_type):
        safe = text.replace('"""', "'''")
        return (
            f'"""Auto-ingested strategy from {source_type}.\n\n{safe}\n"""\n\n'
            "SUPPORTED_REGIMES = ['TREND', 'MEAN_REVERSION', 'HIGH_VOLATILITY', 'LOW_VOLATILITY', 'CRISIS']\n\n"
            "def strategy(data):\n"
            "    close = data.get('close', [])\n"
            "    if len(close) < 20:\n"
            "        return 'HOLD'\n"
            "    fast = sum(close[-5:]) / 5\n"
            "    slow = sum(close[-20:]) / 20\n"
            "    if fast > slow:\n"
            "        return 'BUY'\n"
            "    if fast < slow:\n"
            "        return 'SELL'\n"
            "    return 'HOLD'\n"
        )

    def _default_id(self, source):
        raw = str(source).strip().lower()
        chunks = [ch if ch.isalnum() else "_" for ch in raw[:40]]
        out = "".join(chunks).strip("_")
        return out or "candidate_strategy"
