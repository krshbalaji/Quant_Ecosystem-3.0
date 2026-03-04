import csv
import json
from datetime import datetime
from pathlib import Path

from quant_ecosystem.core.config_loader import Config
from quant_ecosystem.reporting.analytics.institutional_report_engine import InstitutionalReportEngine


class EODReport:

    def __init__(self, output_dir="reporting/output"):
        self.config = Config()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.green = "\033[92m"
        self.red = "\033[91m"
        self.yellow = "\033[93m"
        self.reset = "\033[0m"
        self.institutional = InstitutionalReportEngine(output_dir=output_dir)

    def generate(self, state, intelligence_report=None, strategy_reports=None, adaptation_report=None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        realized_stats = self._compute_realized_stats(state.trade_history)
        summary = {
            "timestamp": timestamp,
            "mode": state.trading_mode,
            "equity": self._r2(state.equity),
            "peak_equity": self._r2(state.peak_equity),
            "drawdown_pct": self._r2(state.total_drawdown_pct),
            "cash_balance": self._r2(state.cash_balance),
            "realized_pnl": self._r2(state.realized_pnl),
            "unrealized_pnl": self._r2(state.unrealized_pnl),
            "fees_paid": self._r2(state.fees_paid),
            "turnover": self._r2(state.turnover),
            "trades_count": len(state.trade_history),
            "realized_stats": realized_stats,
            "target_compliance": self._target_compliance(realized_stats, state.total_drawdown_pct),
            "broker_truth": {
                "account_source": state.account_source,
                "last_reconciled_at": state.last_reconciled_at,
                "positions_count": state.broker_positions_count,
                "orders_count": state.broker_orders_count,
                "trades_count": state.broker_trades_count,
            },
            "intelligence": intelligence_report or {},
            "strategy_reports": strategy_reports or [],
            "adaptation": adaptation_report or {},
        }

        json_path = self.output_dir / f"eod_summary_{timestamp}.json"
        csv_path = self.output_dir / f"eod_trades_{timestamp}.csv"

        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)

        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            fieldnames = [
                "strategy_id",
                "strategy_stage",
                "shadow_mode",
                "symbol",
                "asset_class",
                "regime",
                "trade_type",
                "side",
                "qty",
                "status",
                "price",
                "intended_price",
                "slippage_bps",
                "confidence",
                "fee",
                "realized_pnl",
                "unrealized_pnl",
                "cycle_pnl",
                "equity",
                "cash_balance",
            ]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for trade in state.trade_history:
                writer.writerow(self._format_trade_row(trade, fieldnames))

        institutional_exports = self.institutional.build(timestamp, state.trade_history)
        summary["institutional_exports"] = {
            "analytics_json": institutional_exports["analytics_json"],
            "equity_curve_csv": institutional_exports["equity_curve_csv"],
            "report_pdf": institutional_exports["report_pdf"],
        }
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)

        self._print_console_summary(summary)

        report = {
            "summary_path": str(json_path),
            "trades_path": str(csv_path),
            "summary": summary,
        }
        print(f"EOD report generated: summary={json_path} trades={csv_path}")
        return report

    def _compute_realized_stats(self, trades):
        realized_closed = [
            float(item.get("realized_pnl", 0.0))
            for item in trades
            if bool(item.get("closed_trade", False)) and abs(float(item.get("realized_pnl", 0.0))) > 0.0
        ]
        if realized_closed:
            pnl_values = realized_closed
            sample = pnl_values[-100:] if len(pnl_values) >= 100 else pnl_values
            sample_equity = [
                item for item in trades
                if bool(item.get("closed_trade", False)) and abs(float(item.get("realized_pnl", 0.0))) > 0.0
            ][-len(sample):]
        else:
            pnl_values = [float(item.get("cycle_pnl", item.get("pnl_pct", 0.0))) for item in trades]
            sample = pnl_values[-100:] if len(pnl_values) >= 100 else pnl_values
            sample_equity = trades[-len(sample) :] if sample else []
        pnl_bps = []
        for item in sample_equity:
            pnl_abs = float(item.get("cycle_pnl", item.get("pnl_pct", 0.0)))
            equity = float(item.get("equity", 0.0))
            if equity > 0:
                pnl_bps.append((pnl_abs / equity) * 10000.0)

        if not sample:
            return {
                "win_rate_pct": 0.0,
                "expectancy_abs": 0.0,
                "expectancy_bps": 0.0,
                "profit_factor": 0.0,
                "sharpe": 0.0,
                "rolling_window": 0,
                "warnings": [],
            }

        wins = [value for value in sample if value > 0]
        losses = [value for value in sample if value < 0]
        win_rate = (len(wins) / len(sample)) * 100.0
        loss_rate = 100.0 - win_rate
        avg_win = (sum(wins) / len(wins)) if wins else 0.0
        avg_loss_abs = (abs(sum(losses)) / len(losses)) if losses else 0.0
        expectancy = ((win_rate / 100.0) * avg_win) - ((loss_rate / 100.0) * avg_loss_abs)
        expectancy_bps = (sum(pnl_bps) / len(pnl_bps)) if pnl_bps else 0.0
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit
        sharpe = self._sharpe(sample)

        warnings = []
        if len(sample) >= 20 and win_rate > 80:
            warnings.append("Win rate unusually high for sample size; verify assumptions.")
        if len(sample) >= 20 and expectancy_bps > 8.0:
            warnings.append("Expectancy looks optimistic; include fees/slippage validation.")
        if len(sample) >= 20 and profit_factor > 3.0:
            warnings.append("Profit factor unusually high; run out-of-sample validation.")

        return {
            "win_rate_pct": self._r2(win_rate),
            "expectancy_abs": self._r2(expectancy),
            "expectancy_bps": self._r2(expectancy_bps),
            "profit_factor": self._r2(profit_factor),
            "sharpe": self._r2(sharpe),
            "rolling_window": len(sample),
            "basis": "REALIZED_CLOSED" if realized_closed else "CYCLE_MTM",
            "warnings": warnings,
        }

    def _format_trade_row(self, trade, fields):
        row = {}
        for key in fields:
            value = trade.get(key, "")
            if isinstance(value, float):
                row[key] = self._r2(value)
            else:
                row[key] = value
        return row

    def _print_console_summary(self, summary):
        print("\nEOD Summary")
        print(f"Equity: {self._colored_signed(summary['equity'])}")
        print(f"Realized PnL: {self._colored_signed(summary['realized_pnl'])}")
        print(f"Unrealized PnL: {self._colored_signed(summary['unrealized_pnl'])}")
        print(f"Fees Paid: {self._colored_signed(-abs(summary['fees_paid']))}")
        print(f"Drawdown %: {self._colored_signed(-abs(summary['drawdown_pct']))}")
        print(f"Win Rate %: {self._plain(summary['realized_stats']['win_rate_pct'])}")
        print(f"Expectancy: {self._colored_signed(summary['realized_stats']['expectancy_abs'])}")
        print(f"Profit Factor: {self._plain(summary['realized_stats']['profit_factor'])}")
        print(f"Stats Basis: {summary['realized_stats'].get('basis', 'UNKNOWN')}")

        warnings = summary["realized_stats"].get("warnings", [])
        if warnings:
            print(f"{self.yellow}Warnings:{self.reset}")
            for message in warnings:
                print(f"{self.yellow}  ! {message}{self.reset}")

        compliance = summary.get("target_compliance", {})
        if compliance:
            print("Targets:")
            for key, value in compliance.items():
                if value is None:
                    marker = "[NA]"
                else:
                    marker = "[OK]" if value else "[MISS]"
                print(f"  {marker} {key}")

    def _colored_signed(self, value):
        if value > 0:
            return f"{self.green}[+] +{self._r2(value):.2f}{self.reset}"
        if value < 0:
            return f"{self.red}[-] {self._r2(value):.2f}{self.reset}"
        return f"{self.yellow}[=] 0.00{self.reset}"

    def _plain(self, value):
        return f"{self._r2(value):.2f}"

    def _r2(self, value):
        return round(float(value), 2)

    def _target_compliance(self, stats, drawdown_pct):
        if int(stats.get("rolling_window", 0)) < self.config.min_target_trades:
            return {
                "win_rate_45_60": None,
                "profit_factor_gt_1_5": None,
                "sharpe_gt_1_8": None,
                "max_dd_lt_15": float(drawdown_pct) < 15.0,
                "expectancy_positive": None,
            }
        return {
            "win_rate_45_60": 45.0 <= stats.get("win_rate_pct", 0.0) <= 60.0,
            "profit_factor_gt_1_5": stats.get("profit_factor", 0.0) > 1.5,
            "sharpe_gt_1_8": stats.get("sharpe", 0.0) > 1.8,
            "max_dd_lt_15": float(drawdown_pct) < 15.0,
            "expectancy_positive": stats.get("expectancy_abs", 0.0) > 0.0,
        }

    def _sharpe(self, values):
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        var = sum((x - mean) ** 2 for x in values) / len(values)
        std = var ** 0.5
        if std == 0:
            return 0.0
        return (mean / std) * (252 ** 0.5)
