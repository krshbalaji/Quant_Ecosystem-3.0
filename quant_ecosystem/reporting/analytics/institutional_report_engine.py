import csv
import json
from pathlib import Path


class InstitutionalReportEngine:

    def __init__(self, output_dir="reporting/output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(self, timestamp, trades):
        equity_curve = self._equity_curve(trades)
        rolling_sharpe = self._rolling_sharpe(trades, window=30)
        rolling_drawdown = self._rolling_drawdown(equity_curve)
        histogram = self._trade_histogram(trades)
        regime_split = self._regime_split(trades)
        exposure_heatmap = self._exposure_heatmap(trades)

        bundle = {
            "equity_curve": equity_curve,
            "rolling_sharpe": rolling_sharpe,
            "rolling_drawdown": rolling_drawdown,
            "trade_distribution_histogram": histogram,
            "regime_performance_split": regime_split,
            "exposure_heatmap": exposure_heatmap,
        }

        json_path = self.output_dir / f"institutional_analytics_{timestamp}.json"
        csv_path = self.output_dir / f"equity_curve_{timestamp}.csv"
        pdf_path = self.output_dir / f"institutional_report_{timestamp}.pdf"

        json_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        self._write_equity_curve_csv(csv_path, equity_curve)
        self._write_pdf_placeholder(pdf_path, bundle)

        return {
            "analytics_json": str(json_path),
            "equity_curve_csv": str(csv_path),
            "report_pdf": str(pdf_path),
            "bundle": bundle,
        }

    def _equity_curve(self, trades):
        return [
            {
                "index": i + 1,
                "equity": round(float(item.get("equity", 0.0)), 4),
                "cycle_pnl": round(float(item.get("cycle_pnl", 0.0)), 4),
            }
            for i, item in enumerate(trades)
        ]

    def _rolling_sharpe(self, trades, window=30):
        values = [float(item.get("cycle_pnl", 0.0)) for item in trades]
        out = []
        for idx in range(len(values)):
            sample = values[max(0, idx - window + 1) : idx + 1]
            if len(sample) < 2:
                out.append({"index": idx + 1, "rolling_sharpe": 0.0})
                continue
            mean = sum(sample) / len(sample)
            var = sum((x - mean) ** 2 for x in sample) / len(sample)
            std = var ** 0.5
            sharpe = (mean / std) * (252 ** 0.5) if std else 0.0
            out.append({"index": idx + 1, "rolling_sharpe": round(sharpe, 4)})
        return out

    def _rolling_drawdown(self, equity_curve):
        peak = 0.0
        rows = []
        for row in equity_curve:
            eq = row["equity"]
            peak = max(peak, eq)
            dd = ((peak - eq) / peak * 100.0) if peak > 0 else 0.0
            rows.append({"index": row["index"], "drawdown_pct": round(dd, 4)})
        return rows

    def _trade_histogram(self, trades):
        bins = {"<-50": 0, "-50:-10": 0, "-10:0": 0, "0:10": 0, "10:50": 0, ">50": 0}
        for trade in trades:
            value = float(trade.get("cycle_pnl", 0.0))
            if value < -50:
                bins["<-50"] += 1
            elif value < -10:
                bins["-50:-10"] += 1
            elif value < 0:
                bins["-10:0"] += 1
            elif value < 10:
                bins["0:10"] += 1
            elif value < 50:
                bins["10:50"] += 1
            else:
                bins[">50"] += 1
        return bins

    def _regime_split(self, trades):
        split = {}
        for trade in trades:
            regime = str(trade.get("regime", "UNKNOWN"))
            split.setdefault(regime, {"trades": 0, "pnl": 0.0})
            split[regime]["trades"] += 1
            split[regime]["pnl"] += float(trade.get("cycle_pnl", 0.0))
        for key in split:
            split[key]["pnl"] = round(split[key]["pnl"], 4)
        return split

    def _exposure_heatmap(self, trades):
        heat = {}
        for trade in trades:
            regime = str(trade.get("regime", "UNKNOWN"))
            asset = str(trade.get("asset_class", "UNKNOWN"))
            heat.setdefault(regime, {})
            heat[regime][asset] = heat[regime].get(asset, 0) + abs(int(trade.get("qty", 0)))
        return heat

    def _write_equity_curve_csv(self, path, equity_curve):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["index", "equity", "cycle_pnl"])
            writer.writeheader()
            for row in equity_curve:
                writer.writerow(row)

    def _write_pdf_placeholder(self, path, bundle):
        content = [
            "Institutional EOD Report",
            "",
            "This is a lightweight PDF placeholder export.",
            "Detailed structured analytics are available in JSON and CSV exports.",
            "",
            f"Equity points: {len(bundle['equity_curve'])}",
            f"Regimes tracked: {', '.join(bundle['regime_performance_split'].keys())}",
        ]
        # Write minimal text bytes with .pdf extension for portable artifact generation.
        path.write_bytes(("\n".join(content) + "\n").encode("utf-8"))
