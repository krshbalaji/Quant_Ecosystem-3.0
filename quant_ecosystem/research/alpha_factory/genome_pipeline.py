"""Genome-to-candidate conversion pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List


class GenomePipeline:
    """Converts genomes into executable candidate strategy payloads."""

    def convert(self, genomes: Iterable[Dict]) -> List[Dict]:
        out = []
        for genome in list(genomes or []):
            gid = str(genome.get("genome_id", "genome")).strip()
            signal = dict(genome.get("signal_gene", {}) or {})
            risk = dict(genome.get("risk_gene", {}) or {})
            exec_gene = dict(genome.get("execution_gene", {}) or {})
            candidate = {
                "strategy_id": f"genome_{gid}",
                "genome_id": gid,
                "strategy_type": str(signal.get("type", "systematic")).lower(),
                "timeframe": str(signal.get("timeframe", "5m")),
                "risk_pct": float(risk.get("risk_pct", 1.0) or 1.0),
                "slippage_bps_limit": float(exec_gene.get("slippage_bps_limit", 10.0) or 10.0),
                "genes": genome,
                "stage": "GENOME",
                "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            out.append(candidate)
        return out

