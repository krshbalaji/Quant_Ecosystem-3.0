"""
risk_engine.py — Quant Ecosystem 3.0
======================================

Production-grade risk engine.

Responsibilities
----------------
- Per-trade gate: ``check_order`` / ``allow_trade``
- Portfolio-level exposure reporting: ``portfolio_exposure``
- Symbol-level exposure reporting: ``symbol_exposure``
- Daily loss and drawdown protection
- Dynamic risk-budget adjustment
- Full integration with ExecutionRouter's RiskGatePipeline

Design notes
------------
- Zero module-level third-party imports.
- All dependencies optional / injectable via constructor.
- :class:`SystemState` and :class:`Config` are lazy-imported.
- Backward-compatible with every existing caller signature.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Tuple
from quant_ecosystem.instruments import instrument_resolver

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Null / stub helpers for graceful degradation
# ---------------------------------------------------------------------------

class _NullState:
    trading_halted     = False
    trading_enabled    = True
    total_drawdown_pct = 0.0
    daily_drawdown     = 0.0
    cooldown           = 0


class _NullConfig:
    max_daily_loss_pct         = 5.0
    max_position_pct           = 2.0
    hard_drawdown_limit_pct    = 20.0
    cooldown_after_loss        = 3
    max_portfolio_exposure_pct = 40.0
    max_symbol_exposure_pct    = 20.0
    max_daily_trades           = 18
    max_symbol_daily_loss_pct  = 1.25
    max_sector_exposure_pct    = 35.0
    max_strategy_exposure_pct  = 30.0
    max_asset_exposure_pct     = 50.0


# ---------------------------------------------------------------------------
# RiskEngine
# ---------------------------------------------------------------------------

class RiskEngine:
    """Central pre-trade and portfolio risk enforcement layer.

    Parameters
    ----------
    config:
        :class:`quant_ecosystem.core.config_loader.Config` or any object
        exposing the same attributes.  When ``None`` the engine
        lazy-imports :class:`Config`; if that also fails it uses
        :class:`_NullConfig` so the engine always boots.
    state:
        :class:`quant_ecosystem.core.system_state.SystemState` instance.
        When ``None`` the engine operates stateless (uses :class:`_NullState`).
    portfolio_engine:
        Object implementing ``net_exposure_notional(prices)`` and
        ``symbol_exposure_notional(symbol, prices)``.  Used by
        ``portfolio_exposure`` and ``symbol_exposure``; optional.
    equity_provider:
        Zero-argument callable returning current equity (float).
        Falls back to the state's equity attribute when absent.

    Interface contract (ExecutionRouter / RiskGatePipeline)
    --------------------------------------------------------
    ``allow_trade(state, portfolio_exposure_pct, symbol_exposure_pct, ...)``
        -> (bool, reason_str)   <- existing signature kept unchanged

    Additional interface (new, required by spec)
    -----------------------------------------------
    ``check_order(order)``          -> (bool, reason_str)
    ``portfolio_exposure()``        -> float  (percent of equity)
    ``symbol_exposure(symbol)``     -> float  (percent of equity)
    """

    def __init__(
        self,
        config=None,
        state=None,
        portfolio_engine=None,
        equity_provider=None,
        **kwargs
    ) -> None:
        if config is None:
            try:
                from quant_ecosystem.core.config_loader import Config  # noqa: lazy
                config = Config()
            except Exception as exc:
                logger.warning("RiskEngine: Config unavailable (%s) — using defaults", exc)
                config = _NullConfig()

        self.max_daily_dd              = float(getattr(config, "max_daily_loss_pct",         5.0))
        self.hard_drawdown_limit       = float(getattr(config, "hard_drawdown_limit_pct",   20.0))
        self.max_portfolio_risk        = float(getattr(config, "max_portfolio_exposure_pct", 40.0))
        self.max_symbol_risk           = float(getattr(config, "max_symbol_exposure_pct",   20.0))
        self.max_daily_trades          = max(1, int(getattr(config, "max_daily_trades",      18)))
        self.max_symbol_daily_loss_pct = float(getattr(config, "max_symbol_daily_loss_pct",  1.25))
        self.max_sector_exposure_pct   = float(getattr(config, "max_sector_exposure_pct",   35.0))
        self.max_strategy_exposure_pct = float(getattr(config, "max_strategy_exposure_pct", 30.0))
        self.max_asset_exposure_pct    = float(getattr(config, "max_asset_exposure_pct",    50.0))
        self.cooldown_after_loss       = int(getattr(config,   "cooldown_after_loss",          3))

        raw_max_pos              = float(getattr(config, "max_position_pct", 2.0))
        self.base_trade_risk     = raw_max_pos
        self.max_trade_risk      = raw_max_pos
        self.min_trade_risk      = max(0.25, raw_max_pos * 0.25)
        self.max_trade_risk_cap  = min(2.0, max(raw_max_pos, 2.0))
        # alias for RiskGatePipeline compatibility
        self.max_drawdown_pct    = self.hard_drawdown_limit

        self._state            = state
        self._portfolio_engine = portfolio_engine
        self._equity_provider  = equity_provider

        self._broker_loss_streak={}
        self._broker_locked_until={}
        self._post_unlock_half_risk = {}

        logger.info(
            "RiskEngine initialized (max_dd=%.1f%% hard=%.1f%% port=%.1f%% sym=%.1f%%)",
            self.max_daily_dd, self.hard_drawdown_limit,
            self.max_portfolio_risk, self.max_symbol_risk,
        )

    # ------------------------------------------------------------------
    # Dependency helpers
    # ------------------------------------------------------------------

    def _get_state(self):
        return self._state if self._state is not None else _NullState()

    def _get_equity(self) -> float:
        if self._equity_provider is not None:
            try:
                return float(self._equity_provider())
            except Exception:
                pass
        return float(getattr(self._get_state(), "equity", 100_000.0))

    def _resolve_instrument(self, symbol):
        """
        Pack25 resolver bridge.
        Fail-safe heuristic derivative detection fallback.
        """
        try:
            resolved = instrument_resolver.resolve(symbol)

            if resolved:
                return resolved
        except Exception:
            pass

        symbol_u = str(symbol).upper()

        if (
            "CE" in symbol_u
            or "PE" in symbol_u
            or "FUT" in symbol_u
        ):
            class _FallbackInstrument:
                asset_class = "OPTIONS"
                instrument_type = "OPTIONS"
                lot_size = 75
                multiplier = 1.0

            return _FallbackInstrument()

        return None

    def _instrument_multiplier(self, instrument):
        if not instrument:
            return 1.0

        multiplier = getattr(instrument, "multiplier", None)

        if multiplier is None:
            multiplier = getattr(
                instrument,
                "contract_multiplier",
                1.0,
            )

        try:
            return float(multiplier or 1.0)
        except Exception:
            return 1.0

    def _instrument_asset_class(self, instrument):
        if not instrument:
            return "EQUITY"

        asset_class = getattr(instrument, "asset_class", None)

        if not asset_class:
            asset_class = getattr(
                instrument,
                "instrument_type",
                "EQUITY",
            )

        if hasattr(asset_class, "value"):
            asset_class = asset_class.value

        return str(asset_class).upper()

    def _validate_contract_qty(
        self,
        qty,
        instrument,
    ):
        if not instrument:
            return True, "OK"

        lot_size = int(
            getattr(instrument, "lot_size", 1) or 1
        )

        expiry = getattr(instrument, "expiry", None)
        strike = getattr(instrument, "strike", None)
        option_type = getattr(instrument, "option_type", None)

        asset = str(
            getattr(instrument, "asset_class", "")
        ).upper()

        instrument_type = str(
            getattr(instrument, "instrument_type", "")
        ).upper()

        is_derivative = (
            lot_size > 1
            or expiry is not None
            or strike is not None
            or option_type is not None
            or asset in {
                "OPTION",
                "OPTIONS",
                "FUTURE",
                "FUTURES",
                "DERIVATIVE",
                "DERIVATIVES",
            }
            or instrument_type in {
                "OPTION",
                "OPTIONS",
                "FUTURE",
                "FUTURES",
                "DERIVATIVE",
                "DERIVATIVES",
            }
        )

        if not is_derivative:
            return True, "OK"

        qty_int = int(qty)

        if qty_int % lot_size != 0:
            return False, "INVALID_DERIVATIVE_QTY"

        return True, "OK"

    def _effective_notional(
        self,
        qty,
        price,
        instrument,
    ):
        multiplier = self._instrument_multiplier(instrument)

        return (
            float(qty)
            * float(price)
            * multiplier
        )
    # ------------------------------------------------------------------
    # NEW: check_order(order)
    # ------------------------------------------------------------------

    def check_order(self, order: Dict[str, Any]) -> Tuple[bool, str]:
        """Gate a proposed order dict through all active risk rules.

        Parameters
        ----------
        order:
            Must contain ``symbol``, ``side``, ``qty``, ``price``.
            Optional: ``daily_trade_count``, ``symbol_daily_loss_pct``,
            ``sector_exposure_pct``, ``strategy_exposure_pct``,
            ``asset_exposure_pct``, ``exposure_reducing``,
            ``active_strategy_count``.

        Returns
        -------
        (allowed: bool, reason: str)
        """
        if not isinstance(order, dict):
            return False, "INVALID_ORDER"

        state = self._get_state()

        if getattr(state, "trading_halted", False):
            return False, "TRADING_HALTED"
        if not getattr(state, "trading_enabled", True):
            return False, "TRADING_DISABLED"

        total_dd = float(getattr(state, "total_drawdown_pct", 0.0))
        if total_dd >= self.hard_drawdown_limit:
            if hasattr(state, "trading_halted"):
                state.trading_halted = True
            return False, "HARD_DD_LIMIT"

        daily_dd = float(getattr(state, "daily_drawdown", 0.0))
        if daily_dd >= self.max_daily_dd:
            if hasattr(state, "trading_halted"):
                state.trading_halted = True
            return False, "MAX_DAILY_LOSS"

        if total_dd > self.max_daily_dd:
            if hasattr(state, "trading_halted"):
                state.trading_halted = True
            return False, "MAX_DD_HALT"

        if int(getattr(state, "cooldown", 0)) > 0:
            return False, "COOLDOWN"

        daily_count = int(order.get("daily_trade_count", 0))
        if daily_count >= self.max_daily_trades:
            return False, "MAX_DAILY_TRADES"

        sym_daily_loss = float(order.get("symbol_daily_loss_pct", 0.0))
        if sym_daily_loss >= self.max_symbol_daily_loss_pct:
            return False, "MAX_SYMBOL_DAILY_LOSS"

        exposure_reducing   = bool(order.get("exposure_reducing", False))
        active_strategy_count = int(order.get("active_strategy_count", 1))

        if not exposure_reducing:
            sector_exp   = float(order.get("sector_exposure_pct",   0.0))
            strategy_exp = float(order.get("strategy_exposure_pct", 0.0))
            asset_exp    = float(order.get("asset_exposure_pct",    0.0))

            if sector_exp >= self.max_sector_exposure_pct:
                return False, "MAX_SECTOR_EXPOSURE"
            if active_strategy_count > 1 and strategy_exp >= self.max_strategy_exposure_pct:
                return False, "MAX_STRATEGY_EXPOSURE"
            if asset_exp >= self.max_asset_exposure_pct:
                return False, "MAX_ASSET_EXPOSURE"

            symbol = str(order.get("symbol", ""))
            price  = float(order.get("price", 0.0))
            
            instrument = self._resolve_instrument(symbol)

            port_pct = self._compute_portfolio_exposure({symbol: price} if (symbol and price) else {})
            if port_pct >= self.max_portfolio_risk:
                return False, "MAX_PORTFOLIO_EXPOSURE"
            sym_pct = self._compute_symbol_exposure(symbol, price)
            if sym_pct >= self.max_symbol_risk:
                return False, "MAX_SYMBOL_EXPOSURE"

        qty = float(order.get("qty", 0))
        price = float(order.get("price", 0.0))
        symbol = str(order.get("symbol", ""))

        if qty <= 0 or price <= 0:
            return False, "INVALID_QTY_OR_PRICE"

        instrument = self._resolve_instrument(symbol)

        valid_qty, qty_reason = self._validate_contract_qty(
            qty,
            instrument,
        )

        if not valid_qty:
            return False, qty_reason

        effective_notional = self._effective_notional(
            qty,
            price,
            instrument,
        )

        equity = self._get_equity()

        if equity > 0:
            proposed_pct = (
                effective_notional / equity
            ) * 100.0

            if proposed_pct > self.max_symbol_risk:
                return False, "PROPOSED_SYMBOL_RISK_BREACH"

        return True, "OK"

    # ------------------------------------------------------------------
    # NEW: portfolio_exposure()
    # ------------------------------------------------------------------

    def portfolio_exposure(self, prices: Optional[Dict[str, float]] = None) -> float:
        """Current portfolio exposure as percent of equity (0-100)."""
        return self._compute_portfolio_exposure(prices or {})

    # ------------------------------------------------------------------
    # NEW: symbol_exposure(symbol)
    # ------------------------------------------------------------------

    def symbol_exposure(
        self,
        symbol: str,
        prices: Optional[Dict[str, float]] = None,
    ) -> float:
        """Exposure for *symbol* as percent of equity (0-100)."""
        price = (prices or {}).get(symbol, 0.0)
        return self._compute_symbol_exposure(symbol, price)

    # ------------------------------------------------------------------
    # EXISTING: allow_trade() — full original signature preserved
    # ------------------------------------------------------------------

    def allow_trade(
        self,
        state=None,
        portfolio_exposure_pct: float = 0.0,
        symbol_exposure_pct: float = 0.0,
        daily_trade_count: int = 0,
        symbol_daily_loss_pct: float = 0.0,
        sector_exposure_pct: float = 0.0,
        strategy_exposure_pct: float = 0.0,
        asset_exposure_pct: float = 0.0,
        exposure_reducing: bool = False,
        active_strategy_count: int = 1,
    ) -> Tuple[bool, str]:
        """Evaluate all risk gates for a proposed trade (original signature).

        Returns (allowed: bool, reason: str).
        """
        if state is None:
            state = self._get_state()

        if getattr(state, "trading_halted", False):
            return False, "TRADING_HALTED"

        if float(getattr(state, "total_drawdown_pct", 0.0)) >= self.hard_drawdown_limit:
            state.trading_halted = True
            return False, "HARD_DD_LIMIT"

        if float(getattr(state, "daily_drawdown", 0.0)) >= self.max_daily_dd:
            state.trading_halted = True
            if hasattr(state, "trading_enabled"):
                state.trading_enabled = False
            return False, "MAX_DAILY_LOSS"

        if float(getattr(state, "total_drawdown_pct", 0.0)) > self.max_daily_dd:
            state.trading_halted = True
            return False, "MAX_DD_HALT"

        if int(getattr(state, "cooldown", 0)) > 0:
            return False, "COOLDOWN"

        if int(daily_trade_count) >= self.max_daily_trades:
            return False, "MAX_DAILY_TRADES"

        if float(symbol_daily_loss_pct) >= self.max_symbol_daily_loss_pct:
            return False, "MAX_SYMBOL_DAILY_LOSS"

        if (not exposure_reducing) and float(sector_exposure_pct) >= self.max_sector_exposure_pct:
            return False, "MAX_SECTOR_EXPOSURE"

        if (
            (not exposure_reducing)
            and int(active_strategy_count) > 1
            and float(strategy_exposure_pct) >= self.max_strategy_exposure_pct
        ):
            return False, "MAX_STRATEGY_EXPOSURE"

        if (not exposure_reducing) and float(asset_exposure_pct) >= self.max_asset_exposure_pct:
            return False, "MAX_ASSET_EXPOSURE"

        if (not exposure_reducing) and float(portfolio_exposure_pct) >= self.max_portfolio_risk:
            return False, "MAX_PORTFOLIO_EXPOSURE"

        if (not exposure_reducing) and float(symbol_exposure_pct) >= self.max_symbol_risk:
            return False, "MAX_SYMBOL_EXPOSURE"

        return True, "OK"

    # Backward-compatible alias
    def check_trade(self, *args, **kwargs) -> Tuple[bool, str]:
        return self.allow_trade(*args, **kwargs)

    # ------------------------------------------------------------------
    # Position sizing helpers
    # ------------------------------------------------------------------

    def trade_risk(self, equity: float) -> float:
        """Return the monetary risk budget for a single trade."""
        return equity * (self.max_trade_risk / 100.0)

    def set_trade_risk_pct(self, value: float) -> float:
        """Clamp and store a new per-trade risk percentage; return new value."""
        self.max_trade_risk = max(self.min_trade_risk, min(float(value), self.max_trade_risk_cap))
        return self.max_trade_risk

    def calculate_position_size(
        self,
        equity: float,
        price: float,
        volatility: Optional[float] = None,
        symbol: Optional[str] = None,
    ) -> int:
        if price <= 0:
            return 0

        instrument = None

        if symbol:
            instrument = self._resolve_instrument(symbol)

        multiplier = self._instrument_multiplier(instrument)

        if volatility and volatility > 0:
            risk_budget = self.trade_risk(equity)

            raw_qty = int(
                risk_budget
                / (float(volatility) * multiplier)
            )
        else:
            risk_budget = self.trade_risk(equity)

            raw_qty = int(
                risk_budget
                / (float(price) * multiplier)
            )

        if instrument:
            asset = self._instrument_asset_class(instrument)

            if asset in {
                "OPTIONS",
                "OPTION",
                "FUTURES",
                "FUTURE",
            }:
                lot_size = int(
                    getattr(instrument, "lot_size", 1) or 1
                )

                if raw_qty <= 0:
                    return 0

                raw_qty = max(
                    lot_size,
                    (raw_qty // lot_size) * lot_size
                )

        return max(raw_qty, 0)
        
    def update_risk(self, performance: Optional[Dict] = None) -> Dict:
        """Placeholder for dynamic risk adjustment; returns current limits."""
        return {
            "max_trade_risk":     self.max_trade_risk,
            "max_portfolio_risk": self.max_portfolio_risk,
            "max_symbol_risk":    self.max_symbol_risk,
        }

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Return a snapshot of all active risk limits and live state."""
        state = self._get_state()
        return {
            "max_daily_dd_pct":        self.max_daily_dd,
            "hard_drawdown_limit_pct": self.hard_drawdown_limit,
            "max_portfolio_risk_pct":  self.max_portfolio_risk,
            "max_symbol_risk_pct":     self.max_symbol_risk,
            "max_daily_trades":        self.max_daily_trades,
            "max_trade_risk_pct":      self.max_trade_risk,
            "current_drawdown_pct":    float(getattr(state, "total_drawdown_pct", 0.0)),
            "current_daily_dd_pct":    float(getattr(state, "daily_drawdown",     0.0)),
            "trading_halted":          bool(getattr(state,  "trading_halted",    False)),
            "cooldown":                int(getattr(state,   "cooldown",             0)),
        }

    # ------------------------------------------------------------------
    # Dependency injection
    # ------------------------------------------------------------------

    def set_state(self, state) -> None:
        self._state = state

    def set_portfolio_engine(self, portfolio_engine) -> None:
        self._portfolio_engine = portfolio_engine

    def set_equity_provider(self, provider: "Callable[[], float]") -> None:
        self._equity_provider = provider

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_portfolio_exposure(self, prices: Dict[str, float]) -> float:
        equity = self._get_equity()
        if equity <= 0 or self._portfolio_engine is None:
            return 0.0
        try:
            notional = self._portfolio_engine.net_exposure_notional(prices)
            return min(float(notional) / equity * 100.0, 100.0)
        except Exception as exc:
            logger.debug("RiskEngine._compute_portfolio_exposure: %s", exc)
            return 0.0

    def _compute_symbol_exposure(self, symbol: str, price: float) -> float:
        equity = self._get_equity()
        if equity <= 0 or self._portfolio_engine is None or not symbol:
            return 0.0
        try:
            prices   = {symbol: price} if price else {}
            notional = self._portfolio_engine.symbol_exposure_notional(symbol, prices)
            return min(float(notional) / equity * 100.0, 100.0)
        except Exception as exc:
            logger.debug("RiskEngine._compute_symbol_exposure(%s): %s", symbol, exc)
            return 0.0

    def __repr__(self) -> str:
        state = self._get_state()
        return (
            f"RiskEngine("
            f"halted={getattr(state,'trading_halted',False)}, "
            f"dd={getattr(state,'total_drawdown_pct',0.0):.2f}%, "
            f"trade_risk={self.max_trade_risk:.2f}%)"
        )

    def broker_locked(self, broker):
        import time
        if broker not in self._broker_locked_until:
            return False

        if time.time() > self._broker_locked_until[broker]:
            self._broker_loss_streak[broker] = 0
            self._post_unlock_half_risk[broker] = True
            return False

        return True


    def record_broker_loss(self, broker):
        import time

        self._broker_loss_streak[broker] = \
            self._broker_loss_streak.get(broker,0)+1

        if self._broker_loss_streak[broker] >= 3:
            self._broker_locked_until[broker] = \
                time.time() + (30*60)


    def risk_multiplier(self, broker):

        if self._post_unlock_half_risk.get(broker,False):
            self._post_unlock_half_risk[broker]=False
            return 0.5

        return 1.0