from dataclasses import dataclass
from typing import Any, Dict, Callable, List, Optional


@dataclass
class GateResult:
    allowed: bool
    reason: str
    gate: str


class RiskGatePipeline:

    def __init__(
        self,
        gates: Optional[List[Callable]] = None,
    ):
        if gates is not None:
            self._gates = list(gates)
        else:
            self._gates = [
                self._gate_trading_halted,
                self._gate_drawdown,
                self._gate_daily_loss,
                self._gate_portfolio_exposure,
                self._gate_symbol_exposure,
                self._gate_strategy_cooldown,
                self._gate_position_limits,
            ]

    def add_gate(
        self,
        name,
        fn,
    ):
        self._gates.append(fn)

    def check(
        self,
        state: Any,
        signal: Dict,
        context: Dict,
    ) -> GateResult:
        for fn in self._gates:
            result = fn(
                state,
                signal,
                context,
            )

            if not result.allowed:
                return result

        return GateResult(
            allowed=True,
            reason="OK",
            gate="none",
        )

    @staticmethod
    def _gate_trading_halted(state, signal, ctx):
        if getattr(state, "trading_halted", False):
            return GateResult(False, "TRADING_HALTED", "trading_halted")

        if not getattr(state, "trading_enabled", True):
            return GateResult(False, "TRADING_DISABLED", "trading_halted")

        return GateResult(True, "OK", "trading_halted")

    @staticmethod
    def _gate_drawdown(state, signal, ctx):
        risk = ctx.get("risk_engine")

        if risk is None:
            return GateResult(True, "OK", "drawdown_guard")

        if getattr(risk, "max_drawdown_breached", lambda: False)():
            return GateResult(False, "MAX_DRAWDOWN_BREACH", "drawdown_guard")

        return GateResult(True, "OK", "drawdown_guard")

    @staticmethod
    def _gate_daily_loss(state, signal, ctx):
        risk = ctx.get("risk_engine")

        if risk is None:
            return GateResult(True, "OK", "daily_loss_guard")

        checker = getattr(risk, "symbol_daily_loss_breached", None)

        if checker and checker(signal["symbol"]):
            return GateResult(False, "SYMBOL_DAILY_LOSS_LIMIT", "daily_loss_guard")

        return GateResult(True, "OK", "daily_loss_guard")

    @staticmethod
    def _gate_portfolio_exposure(state, signal, ctx):
        portfolio = ctx.get("portfolio_engine")

        if portfolio is None:
            return GateResult(True, "OK", "portfolio_exposure")

        checker = getattr(portfolio, "max_portfolio_exposure_breached", None)

        if checker and checker():
            return GateResult(False, "MAX_PORTFOLIO_EXPOSURE", "portfolio_exposure")

        return GateResult(True, "OK", "portfolio_exposure")

    @staticmethod
    def _gate_symbol_exposure(state, signal, ctx):
        portfolio = ctx.get("portfolio_engine")

        if portfolio is None:
            return GateResult(True, "OK", "symbol_exposure")

        checker = getattr(portfolio, "max_symbol_exposure_breached", None)

        if checker and checker(signal["symbol"]):
            return GateResult(False, "MAX_SYMBOL_EXPOSURE", "symbol_exposure")

        return GateResult(True, "OK", "symbol_exposure")

    @staticmethod
    def _gate_strategy_cooldown(state, signal, ctx):
        cooldown = ctx.get("strategy_cooldown", {})

        if signal.get("strategy_id") in cooldown:
            return GateResult(False, "STRATEGY_COOLDOWN", "strategy_cooldown")

        return GateResult(True, "OK", "strategy_cooldown")

    @staticmethod
    def _gate_position_limits(state, signal, ctx):
        portfolio = ctx.get("portfolio_engine")

        if portfolio is None:
            return GateResult(True, "OK", "position_limits")

        getter = getattr(portfolio, "open_positions_count", None)

        if getter and getter() >= ctx.get("max_open_positions", 20):
            return GateResult(False, "MAX_OPEN_POSITIONS", "position_limits")

        return GateResult(True, "OK", "position_limits")