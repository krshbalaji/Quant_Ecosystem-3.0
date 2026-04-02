"""Stable execution router for Quant Ecosystem."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from quant_ecosystem.operating.risk.dynamic_risk_scaler import get_dynamic_risk_scaler
from quant_ecosystem.operating.execution.signal_diversity_engine import get_signal_diversity_engine

logger = logging.getLogger(__name__)


_ASSET_BROKER_MAP: Dict[str, str] = {
    "EQUITY": "fyers",
    "FUTURES": "fyers",
    "OPTIONS": "fyers",
    "FOREX": "fyers",
    "CRYPTO": "coinswitch",
    "COMMODITY": "fyers",
}

_ASSET_BROKER_ALT: Dict[str, str] = {
    "EQUITY": "groww",
    "FUTURES": "groww",
    "OPTIONS": "groww",
    "CRYPTO": "coinswitch",
}

_RISK_PRESET_MAP = {"25%": 0.25, "50%": 0.50, "100%": 1.0}


def _skip(reason: str) -> Dict:
    return {"status": "SKIP", "reason": reason}


class _PaperBroker:
    account_source = "PAPER"

    def __init__(self) -> None:
        self.connected = True
        self._seq = 0

    def connect(self) -> None:
        self.connected = True

    def is_connected(self) -> bool:
        return True

    def place_order(self, symbol: str, side: str, qty: int, price: float, fee: float = 0.0, meta: Optional[Dict] = None, **kwargs) -> Dict:
        self._seq += 1
        return {
            "id": f"PAPER-{self._seq:06d}",
            "order_id": f"PAPER-{self._seq:06d}",
            "symbol": symbol,
            "side": side,
            "qty": int(qty),
            "price": float(price),
            "fee": float(fee or 0.0),
            "status": "FILLED",
            "realized_pnl": 0.0,
            "account_source": self.account_source,
            "meta": meta or {},
        }

    def get_positions(self) -> List:
        return []

    def cancel_order(self, order_id: str) -> Dict:
        return {"cancelled": order_id}


class _GenericBrokerAdapter:
    def __init__(self, broker: Any, source: str = "BROKER") -> None:
        self._broker = broker
        self.account_source = str(getattr(broker, "account_source", source)).upper()

    def connect(self) -> None:
        if hasattr(self._broker, "connect"):
            self._broker.connect()

    def is_connected(self) -> bool:
        if hasattr(self._broker, "is_connected"):
            try:
                return bool(self._broker.is_connected())
            except Exception:
                return False
        return bool(getattr(self._broker, "connected", False))

    def place_order(self, symbol: str, side: str, qty: int, price: float, fee: float = 0.0, meta: Optional[Dict] = None, **kwargs) -> Dict:
        raw = self._broker.place_order(symbol=symbol, side=side, qty=qty, price=price, fee=fee, meta=meta or {})
        if isinstance(raw, dict):
            raw.setdefault("order_id", raw.get("id", ""))
            raw.setdefault("account_source", self.account_source)
        return raw or {}

    def get_positions(self) -> List:
        if hasattr(self._broker, "get_positions"):
            return self._broker.get_positions()
        return []

    def cancel_order(self, order_id: str) -> Dict:
        if hasattr(self._broker, "cancel_order"):
            return self._broker.cancel_order(order_id)
        return {"cancelled": order_id}


class MultiBrokerRouter:
    def __init__(self, mode: str = "PAPER") -> None:
        self.mode = str(mode).upper()
        self.account_source = self.mode
        self._paper = _PaperBroker()
        self._brokers: Dict[str, Any] = {}

    def register(self, name: str, broker: Any) -> None:
        key = str(name).lower().strip()
        self._brokers[key] = broker
        logger.info("Broker registered | name=%s source=%s", key, getattr(broker, "account_source", "UNKNOWN"))

    def has_connected_broker(self) -> bool:
        if self.mode != "LIVE":
            return True
        return any(
            bool(getattr(broker, "is_connected", lambda: False)())
            for broker in self._brokers.values()
        )

    def _resolve_candidates(self, asset_class: str) -> List[Any]:
        names: List[str] = []
        preferred = _ASSET_BROKER_MAP.get(asset_class.upper())
        alt = _ASSET_BROKER_ALT.get(asset_class.upper())
        if preferred:
            names.append(preferred)
        if alt and alt not in names:
            names.append(alt)
        for name in self._brokers.keys():
            if name not in names:
                names.append(name)
        return [self._brokers[name] for name in names if name in self._brokers]

    def _select(self, asset_class: str) -> Any:
        for broker in self._resolve_candidates(asset_class):
            if bool(getattr(broker, "is_connected", lambda: False)()):
                self.account_source = getattr(broker, "account_source", "PAPER")
                return broker
        if self.mode != "LIVE":
            self.account_source = "PAPER"
            return self._paper
        raise RuntimeError(f"No connected live broker available for asset class {asset_class}")

    def place_order(self, symbol: str, side: str, qty: int, price: float, fee: float = 0.0, asset_class: str = "EQUITY", meta: Optional[Dict] = None) -> Dict:
        broker = self._select(asset_class)
        return broker.place_order(symbol=symbol, side=side, qty=qty, price=price, fee=fee, meta=meta or {})

    def place_order_with_failover(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: float,
        fee: float = 0.0,
        asset_class: str = "EQUITY",
        meta: Optional[Dict] = None,
    ) -> Dict:
        failures: List[str] = []
        for broker in self._resolve_candidates(asset_class):
            if self.mode == "LIVE" and not bool(getattr(broker, "is_connected", lambda: False)()):
                continue
            try:
                self.account_source = getattr(broker, "account_source", self.account_source)
                result = broker.place_order(symbol=symbol, side=side, qty=qty, price=price, fee=fee, meta=meta or {})
                if isinstance(result, dict):
                    result.setdefault("account_source", self.account_source)
                return result
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{self.account_source}:{exc}")
                logger.warning("Broker execution failed | source=%s error=%s", self.account_source, exc)
        if self.mode != "LIVE":
            return self._paper.place_order(symbol=symbol, side=side, qty=qty, price=price, fee=fee, meta=meta or {})
        raise RuntimeError("; ".join(failures) if failures else "No broker execution path available")


class ExecutionRouter:
    """Production-stable execution coordinator with multi-broker routing."""

    def __init__(
        self,
        broker: Any = None,
        risk_engine: Any = None,
        state: Any = None,
        runtime_state: Any = None,
        market_data: Any = None,
        strategy_engine: Any = None,
        portfolio_engine: Any = None,
        reconciler: Any = None,
        symbols: Optional[List[str]] = None,
        portfolio_governor: Any = None,
        **kwargs: Any,
    ) -> None:
        self.broker = broker
        self.risk_engine = risk_engine
        self.state = state
        self.runtime_state = runtime_state
        self.market_data = market_data
        self.strategy_engine = strategy_engine
        self.portfolio_engine = portfolio_engine
        self.reconciler = reconciler
        self.symbols = list(symbols or [])
        self.portfolio_governor = portfolio_governor
        self.config = kwargs.get("config")
        self.data_layer = kwargs.get("data_layer")
        self.telegram = None
        self.mode = str(getattr(state, "trading_mode", "PAPER")).upper() if state else "PAPER"
        self._multi_broker = MultiBrokerRouter(mode=self.mode)
        self._order_queue: List[Dict] = []
        self._cycle_no = 0
        self._execution_loop_started = False
        self.trade_journal_path = Path("storage") / "trade_journal.json"
        self.performance_log_path = Path("storage") / "performance_log.json"
        self.max_order_retries = int(getattr(self.config, "execution_retry_attempts", 2) if self.config else 2)
        self.retry_delay_ms = int(getattr(self.config, "execution_retry_delay_ms", 250) if self.config else 250)

        if self.state is not None:
            if not hasattr(self.state, "trade_history"):
                self.state.trade_history = []
            self.state.trading_enabled = bool(getattr(self.state, "trading_enabled", True))
            self.state.trading_halted = bool(getattr(self.state, "trading_halted", False))
            self.state.auto_mode = bool(getattr(self.state, "auto_mode", True))
            self.state.strategy_profile = str(getattr(self.state, "strategy_profile", "BETA"))
            self.state.risk_preset = str(getattr(self.state, "risk_preset", "100%"))
            self.state.active_symbols = list(getattr(self.state, "active_symbols", self.symbols))
            self.state.last_strategy_id = getattr(self.state, "last_strategy_id", "")
            self.state.last_signal = getattr(self.state, "last_signal", {})
            self.state.signal_count = int(getattr(self.state, "signal_count", 0) or 0)
            self.state.trades_executed = int(getattr(self.state, "trades_executed", 0) or 0)
            self.state.skipped_signals = int(getattr(self.state, "skipped_signals", 0) or 0)
            self.state.last_trade_explanation = str(getattr(self.state, "last_trade_explanation", ""))

        raw_broker = getattr(broker, "broker", broker)
        if raw_broker is not None:
            self.register_broker("fyers", raw_broker)

    def register_broker(self, name: str, broker: Any) -> None:
        source = str(name).upper()
        self._multi_broker.register(str(name).lower().strip(), _GenericBrokerAdapter(broker, source=source))

    def start_execution_loop(self) -> str:
        if self._execution_loop_started:
            logger.info("Execution loop already running | mode=%s", self.mode)
            return "Execution loop already started."
        self._execution_loop_started = True
        logger.info("🔥 Execution loop started")
        return "Execution loop started."

    async def execute(self, signal: Optional[Dict] = None, market_bias: str = "NEUTRAL", regime: str = "RANGE") -> Dict:
        await asyncio.sleep(0)
        return self.run_cycle(signal=signal, market_bias=market_bias, regime=regime)

    def run_cycle(self, signal: Optional[Dict] = None, market_bias: str = "NEUTRAL", regime: str = "RANGE") -> Dict:
        # HARD STOP CHECK
        if getattr(self, "runtime_state", None) and not self.runtime_state.is_running():
            print(f"[DEBUG] CYCLE ABORTED: runtime_state.is_running={self.runtime_state.is_running()}")
            return {"status": "STOPPED"}
        if getattr(self, "state", None) and hasattr(self.state, "run_state") and not getattr(self.state, "run_state", True):
            return {"status": "STOPPED"}
        self._cycle_no += 1
        print(f"[DEBUG] SYSTEM RUNNING: {getattr(self, 'runtime_state', None).is_running() if getattr(self, 'runtime_state', None) else 'unknown'}")
        if not self.state:
            return _skip("NO_STATE")
        if getattr(self.state, "trading_halted", False):
            return _skip("TRADING_HALTED")
        if not getattr(self.state, "trading_enabled", True):
            return _skip("TRADING_DISABLED")
        if not getattr(self.state, "auto_mode", True) and signal is None:
            return _skip("AUTO_DISABLED")

        candidate = signal or self._select_signal(regime=regime, market_bias=market_bias)
        if candidate:
            logger.info(
                "[cycle] cycle=%s symbol=%s regime=%s strategy=%s confidence=%s",
                self._cycle_no,
                candidate.get("symbol", "N/A"),
                regime,
                candidate.get("strategy", "N/A"),
                candidate.get("confidence", 0.0),
            )

        if not candidate:
            self.state.skipped_signals = int(getattr(self.state, "skipped_signals", 0) or 0) + 1
            return _skip("NO_SIGNAL")

        strategy_id = str(candidate.get("strategy_id") or candidate.get("strategy") or "").strip()
        confidence = float(candidate.get("confidence", 0.0) or 0.0)

        if self.portfolio_engine:
            total_exposure = self.portfolio_engine.get_total_exposure()
            if total_exposure > 0.2 * float(self.portfolio_engine.capital or 100000.0):
                logger.warning("[risk] total exposure %s exceeds 20%% capital -> skipping trade", total_exposure)
                return _skip("EXPOSURE_LIMIT")

        if not candidate.get("symbol"):
            self.state.skipped_signals = int(getattr(self.state, "skipped_signals", 0) or 0) + 1
            return _skip("INVALID_SIGNAL")

        # Check signal diversity constraints
        symbol = str(candidate.get("symbol")).upper()
        strategy_type = str(candidate.get("strategy_type", candidate.get("strategy", "UNKNOWN"))).upper()
        diversity_engine = get_signal_diversity_engine()
        should_execute, diversity_reason = diversity_engine.should_execute_signal(
            symbol, strategy_type, self._cycle_no
        )
        if not should_execute:
            self.state.skipped_signals = int(getattr(self.state, "skipped_signals", 0) or 0) + 1
            logger.warning("Trade skipped due to safety constraint: %s for symbol %s", diversity_reason, symbol)
            return _skip(f"DIVERSITY_GATE: {diversity_reason}")

        self.state.active_symbols = list(self.symbols or [])
        self.state.last_signal = dict(candidate)
        self.state.last_strategy_id = str(candidate.get("strategy_id", candidate.get("strategy", "")))
        self.state.signal_count = int(getattr(self.state, "signal_count", 0) or 0) + 1

        asset_class = self._asset_class(candidate["symbol"])
        symbol = str(candidate.get("symbol", "")).upper()

        price = candidate.get("price")
        if not price and self.market_data and hasattr(self.market_data, "get_price_sync"):
            try:
                price = self.market_data.get_price_sync(symbol)
            except Exception as e:
                logger.warning("Failed to get price_sync for %s: %s", symbol, e)
                price = None

        try:
            price = float(price)
        except Exception:
            price = 0.0
            
            self.state.skipped_signals = int(getattr(self.state, "skipped_signals", 0) or 0) + 1
            return _skip("NO_PRICE")

        qty = int(candidate.get("qty") or self._allocate_quantity(candidate, price))

        if self.portfolio_engine and strategy_id:
            symbol = str(candidate.get("symbol", "")).upper()
            strategy_allocations = self.portfolio_engine.allocations.get(strategy_id, {})
            allocated_capital = float(strategy_allocations.get(symbol, 0.0) or 0.0)
            position_size = allocated_capital * confidence
            if position_size > 0 and price > 0:
                qty_by_alloc = int(position_size / price)
                if qty_by_alloc <= 0:
                    self.state.skipped_signals = int(getattr(self.state, "skipped_signals", 0) or 0) + 1
                    return _skip("ALLOC_SIZE_ZERO")
                qty = min(qty, qty_by_alloc) if qty > 0 else qty_by_alloc

        if qty <= 0:
            self.state.skipped_signals = int(getattr(self.state, "skipped_signals", 0) or 0) + 1
            return _skip("SIZE_ZERO")

        # Define side before using it in risk check
        side = str(candidate.get("side", "BUY")).upper()
        if side not in ["BUY", "SELL"]:
            self.state.skipped_signals = int(getattr(self.state, "skipped_signals", 0) or 0) + 1
            return _skip("INVALID_SIGNAL_NO_SIDE")

        # Check risk engine constraints
        if self.risk_engine:
            order = {
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "price": price,
                "daily_trade_count": len(getattr(self.state, "trade_history", []) or []),
            }
            allowed, risk_reason = self.risk_engine.check_order(order)
            if not allowed:
                logger.warning("Trade blocked by risk engine: %s for symbol %s", risk_reason, symbol)
                return _skip(f"RISK_GATE: {risk_reason}")

        fee = float(candidate.get("fee", 0.0) or 0.0)
        execution_signal = dict(candidate)
        execution_signal.update(
            {
                "side": side,
                "qty": qty,
                "price": price,
                "fee": fee,
                "asset_class": asset_class,
                "regime": regime,
            }
        )
        if self.mode == "PAPER":
            return self._simulate_trade(execution_signal)
        return self._live_execute(execution_signal)

    def _select_signal(self, regime: str, market_bias: str) -> Optional[Dict]:
        active_symbols = list(self.symbols or []) or list(getattr(self.state, "active_symbols", []) or [])
        if not active_symbols and self.config is not None:
            active_symbols = list(getattr(self.config, "trade_symbols", []) or [])
        market_payload = {
            "regime": regime,
            "market_bias": market_bias,
            "symbols": active_symbols,
        }
        if active_symbols:
            symbol = active_symbols[0]
            market_payload["symbol"] = symbol
            market_payload["price"] = self._market_price(symbol)
            
        min_confidence = float(getattr(self.config, "min_signal_confidence", 0.45) if self.config else 0.45)

        candidate_signals = []
        if self.strategy_engine and hasattr(self.strategy_engine, "run"):
            try:
                signals = self.strategy_engine.run(market_payload) or []
                for row in signals:
                    enriched = self._enrich_signal(dict(row), regime=regime)
                    if enriched and float(enriched.get("confidence", 0.0)) >= min_confidence:
                        candidate_signals.append(enriched)
                if candidate_signals:
                    candidate_signals.sort(
                        key=lambda item: (
                            0 if str(item.get("strategy_id", "")).startswith("fallback_") else 1,
                            float(item.get("confidence", 0.0) or 0.0),
                        ),
                        reverse=True,
                    )
                    return candidate_signals[0]
            except Exception as exc:
                logger.warning("Strategy engine run failed | error=%s", exc)

        strategies = getattr(self.strategy_engine, "strategies", {}) or {}
        active_ids = list(getattr(self.strategy_engine, "active_ids", []) or [])
        ordered_ids = active_ids or list(strategies.keys())
        for strategy_id in ordered_ids:
            strategy = strategies.get(strategy_id)
            if strategy is None or not hasattr(strategy, "generate_signal"):
                continue
            try:
                signal = strategy.generate_signal(market_payload)
                if signal:
                    signal.setdefault("strategy_id", strategy_id)
                    signal.setdefault("strategy", strategy_id)
                    enriched = self._enrich_signal(signal, regime=regime)
                    if enriched and float(enriched.get("confidence", 0.0)) >= min_confidence:
                        return enriched
            except Exception as exc:
                logger.warning("Strategy signal generation failed | strategy=%s error=%s", strategy_id, exc)

        # only fallback when no valid high-confidence live strategy signal is present.
        return self._fallback_signal(market_payload)

    def _enrich_signal(self, signal: Dict, regime: str) -> Optional[Dict]:
        signal.setdefault("strategy_id", signal.get("strategy", "LIVE_ENGINE"))
        signal.setdefault("strategy", signal.get("strategy_id", "LIVE_ENGINE"))
        signal.setdefault("participation", 0.5)
        signal.setdefault("regime", regime)

        base_confidence = self._score_signal(signal=signal, regime=regime)
        trend_factor = self._trend_confirmation(signal.get("symbol", ""), signal.get("side", "BUY"))
        participation_factor = self._participation_score(signal)
        regime_factor = self._regime_alignment(signal, regime)

        combined = (
            base_confidence * 0.5
            + trend_factor * 0.25
            + participation_factor * 0.15
            + regime_factor * 0.10
        )

        signal["confidence"] = round(max(0.0, min(combined, 1.0)), 4)

        threshold = float(getattr(self.config, "min_signal_confidence", 0.45) if self.config else 0.45)
        if float(signal["confidence"]) < threshold:
            return None

        return signal

    def _fallback_signal(self, market_payload: Dict) -> Optional[Dict]:
        symbols = list(market_payload.get("symbols", []) or [])
        if not symbols:
            return None
        symbol = str(market_payload.get("symbol") or symbols[0]).strip()
        if not symbol:
            return None
        regime = str(market_payload.get("regime", "RANGE")).upper()
        side = "BUY"
        strategy_id = "fallback_range"
        participation = 0.6
        if regime in {"TREND", "TRENDING_BULL", "TRENDING_BEAR"}:
            strategy_id = "fallback_trend"
            participation = 0.75
        elif regime in {"HIGH_VOLATILITY", "VOLATILE", "CRISIS"}:
            strategy_id = "fallback_volatility"
            side = "SELL"
            participation = 0.55
        return {
            "symbol": symbol,
            "side": side,
            "strategy": strategy_id,
            "strategy_id": strategy_id,
            "participation": participation,
            "price": market_payload.get("price") or self._market_price(symbol),
            "trade_type": "FALLBACK",
            "regime": regime,
        }

    def _score_signal(self, signal: Dict, regime: str) -> float:
        regime_key = str(regime or signal.get("regime", "RANGE")).upper()
        trend_strength = 0.85 if regime_key in {"TREND", "TRENDING_BULL", "TRENDING_BEAR"} else 0.45
        volume_participation = max(0.1, min(float(signal.get("participation", 0.5) or 0.5), 1.0))
        signal_regime = str(signal.get("regime", regime_key)).upper()
        regime_alignment = 1.0 if signal_regime == regime_key else 0.5
        confidence = (trend_strength * 0.4) + (volume_participation * 0.3) + (regime_alignment * 0.3)
        if str(signal.get("strategy_id", "")).startswith("fallback_"):
            confidence = max(confidence, 0.45)
        return max(0.0, min(confidence, 1.0))

    def _ema(self, data: List[float], period: int) -> float:
        if not data or period <= 0:
            return 0.0
        if len(data) < period:
            return float(data[-1]) if data else 0.0
        k = 2.0 / (period + 1)
        ema = float(data[0])
        for price in data[1:]:
            ema = (price * k) + (ema * (1.0 - k))
        return float(ema)

    def _trend_confirmation(self, symbol: str, side: str) -> float:
        if not symbol or not self.market_data or not hasattr(self.market_data, "get_close_series"):
            return 0.5
        closes = list(self.market_data.get_close_series(symbol, lookback=26) or [])
        if len(closes) < 26:
            return 0.5
        ema12 = self._ema(closes[-26:], 12)
        ema26 = self._ema(closes[-26:], 26)
        side = str(side or "BUY").upper()
        if side == "BUY":
            return 1.0 if ema12 > ema26 else 0.35
        if side == "SELL":
            return 1.0 if ema12 < ema26 else 0.35
        return 0.5

    def _participation_score(self, signal: Dict) -> float:
        participation = max(0.1, min(float(signal.get("participation", 0.5) or 0.5), 2.0))
        if not self.market_data or not signal.get("symbol"):
            return min(1.0, max(0.1, participation))
        symbol = str(signal.get("symbol"))
        current_volume = float(getattr(self.market_data, "get_volume", lambda x: 0.0)(symbol) or 0.0)
        avg_volume = float(getattr(self.market_data, "get_average_volume", lambda x, lookback=20: 0.0)(symbol) or 0.0)
        if avg_volume > 0:
            ratio = min(2.0, max(0.0, current_volume / max(avg_volume, 1.0)))
            return min(1.0, max(0.1, ratio))
        return min(1.0, max(0.1, participation))

    def _regime_alignment(self, signal: Dict, regime: str) -> float:
        signal_regime = str(signal.get("regime", "")).upper()
        regime_key = str(regime or "").upper()
        if not regime_key or not signal_regime:
            return 0.5
        if signal_regime == regime_key:
            return 1.0
        if regime_key in {"TREND", "TRENDING_BULL", "TRENDING_BEAR"} and signal_regime in {"TREND", "TRENDING_BULL", "TRENDING_BEAR"}:
            return 0.8
        return 0.45

    def _allocate_quantity(self, signal: Dict, price: float) -> int:
        equity = float(getattr(self.state, "equity", 100000.0) or 100000.0)
        base_risk = 0.02   # 2% capital
        base_confidence = float(signal.get("confidence", 1.0) or 1.0)
        participation = max(0.1, min(float(signal.get("participation", 1.0) or 1.0), 2.0))
        regime = str(signal.get("regime", "RANGE")).upper()

        # Intelligence from global intelligence engine
        intelligence = signal.get("intelligence", {})
        confidence = float(intelligence.get("confidence", base_confidence) or base_confidence)
        volatility = float(intelligence.get("volatility", 0) or 0)

        # Execution filter: skip if confidence below threshold
        if confidence < 0.4:
            self.state.skipped_signals = int(getattr(self.state, "skipped_signals", 0) or 0) + 1
            logger.info("[CAPITAL ENGINE] SKIP TRADE: confidence=%.3f < 0.4", confidence)
            return 0

        # Dynamic position sizing
        adjusted_risk = base_risk * min(confidence, 2.0)

        if volatility > 0:
            position_size = adjusted_risk / volatility
        else:
            position_size = adjusted_risk / 0.01  # default volatility floor

        # Max risk cap: 5% of capital
        position_size = min(position_size, 0.05)

        # Regime-based adjustment
        if regime == "HIGH_VOLATILITY":
            position_size *= 0.5
        elif regime == "TREND":
            position_size *= 1.2

        # Performance weight
        performance_weight = self._performance_weight(signal.get("strategy_id", signal.get("strategy", "")))

        # Dynamic risk scaling based on drawdown
        dynamic_scaler = get_dynamic_risk_scaler()
        risk_scale_factor = dynamic_scaler.get_risk_scale_factor()

        # Calculate final position
        gross = equity * position_size * participation * performance_weight * risk_scale_factor
        qty = int(gross / max(price, 1.0))

        # Capital tracking if portfolio engine available
        available_capital = equity
        if self.portfolio_engine and hasattr(self.portfolio_engine, "get_available_capital"):
            try:
                available_capital = float(self.portfolio_engine.get_available_capital() or equity)
            except Exception:
                pass

        capital_used = gross
        print(f"\n[CAPITAL ENGINE]")
        print(f"confidence={confidence:.3f}")
        print(f"volatility={volatility:.5f}")
        print(f"position_size={position_size:.5f}")
        print(f"capital_used={capital_used:.2f}")

        return max(qty, 1)

    def _regime_multiplier(self, regime: str) -> float:
        key = str(regime or "RANGE").upper()
        if key in {"TREND", "TRENDING_BULL", "TRENDING_BEAR"}:
            return 1.5
        if key in {"RANGE", "MEAN_REVERSION"}:
            return 0.5
        if key in {"LOW_VOL", "LOW_VOLATILITY"}:
            return 0.3
        return 1.0

    def _performance_weight(self, strategy_id: str) -> float:
        if not strategy_id:
            return 1.0
        metrics = self._load_performance_log().get(str(strategy_id), {})
        avg_pnl = float(metrics.get("avg_pnl", 0.0) or 0.0)
        win_rate = float(metrics.get("win_rate", 50.0) or 50.0)
        weight = 1.0
        if avg_pnl > 0:
            weight += min(avg_pnl / 100.0, 0.35)
        if win_rate > 50.0:
            weight += min((win_rate - 50.0) / 100.0, 0.25)
        if avg_pnl < 0:
            weight -= min(abs(avg_pnl) / 100.0, 0.35)
        return max(0.5, min(weight, 1.6))

    def _simulate_trade(self, signal: Dict) -> Dict:
        trade = {
            "time": datetime.now().isoformat(),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "strategy": signal.get("strategy", signal.get("strategy_id", "MANUAL")),
            "strategy_id": signal.get("strategy_id", signal.get("strategy", "MANUAL")),
            "symbol": signal["symbol"],
            "side": signal.get("side", "BUY"),
            "qty": int(signal.get("qty", 1) or 1),
            "price": float(signal.get("price", 0.0) or 0.0),
            "entry": float(signal.get("price", 0.0) or 0.0),
            "exit": float(signal.get("price", 0.0) or 0.0),
            "pnl": 0.0,
            "cycle_pnl": 0.0,
            "realized_pnl": 0.0,
            "regime": signal.get("regime", "RANGE"),
            "confidence": float(signal.get("confidence", 1.0) or 1.0),
            "participation": float(signal.get("participation", 1.0) or 1.0),
            "trade_type": signal.get("trade_type", self._trade_type(signal)),
            "broker": "PAPER",
        }
        logger.info("💰 Simulated trades executing | symbol=%s side=%s qty=%s", trade["symbol"], trade["side"], trade["qty"])
        return self._finalize_trade(trade)

    def _live_execute(self, signal: Dict) -> Dict:
        order = self._execute_live_order(signal)
        fill_qty = int(order.get("filled_qty", order.get("qty", signal.get("qty", 0))) or 0)
        requested_qty = int(signal.get("qty", fill_qty) or fill_qty)
        fill_status = str(order.get("status", "FILLED")).upper()
        partial_fill = fill_status.startswith("PARTIAL") or (0 < fill_qty < requested_qty)
        intended_price = float(signal.get("price", 0.0) or 0.0)
        executed_price = float(order.get("price", intended_price) or intended_price)
        slippage_bps = self._compute_slippage_bps(intended_price=intended_price, executed_price=executed_price)
        trade = {
            "time": datetime.now().isoformat(),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "strategy": signal.get("strategy", signal.get("strategy_id", "MANUAL")),
            "strategy_id": signal.get("strategy_id", "MANUAL"),
            "symbol": order.get("symbol", signal.get("symbol")),
            "side": order.get("side", signal.get("side", "BUY")),
            "qty": fill_qty or requested_qty,
            "requested_qty": requested_qty,
            "price": executed_price,
            "entry": executed_price,
            "exit": executed_price,
            "pnl": float(order.get("realized_pnl", 0.0) or 0.0),
            "cycle_pnl": float(order.get("realized_pnl", 0.0) or 0.0),
            "realized_pnl": float(order.get("realized_pnl", 0.0) or 0.0),
            "regime": signal.get("regime", "RANGE"),
            "confidence": float(signal.get("confidence", 1.0) or 1.0),
            "participation": float(signal.get("participation", 1.0) or 1.0),
            "trade_type": signal.get("trade_type", self._trade_type(signal)),
            "broker": order.get("account_source", self._multi_broker.account_source),
            "order_id": order.get("order_id", order.get("id", "")),
            "fill_status": fill_status,
            "partial_fill": partial_fill,
            "slippage_bps": slippage_bps,
        }
        return self._finalize_trade(trade)

    def _execute_live_order(self, signal: Dict) -> Dict:
        last_error = None
        for attempt in range(1, self.max_order_retries + 2):
            try:
                started = time.perf_counter()
                order = self._multi_broker.place_order_with_failover(
                    symbol=signal["symbol"],
                    side=signal["side"],
                    qty=int(signal["qty"]),
                    price=float(signal["price"]),
                    fee=float(signal.get("fee", 0.0) or 0.0),
                    asset_class=signal.get("asset_class", "EQUITY"),
                    meta={
                        "strategy_id": signal.get("strategy_id", "MANUAL"),
                        "regime": signal.get("regime", "RANGE"),
                        "confidence": signal.get("confidence", 1.0),
                        "participation": signal.get("participation", 1.0),
                    },
                )
                latency_ms = (time.perf_counter() - started) * 1000.0
                if self.state is not None:
                    self.state.last_execution_latency_ms = round(latency_ms, 3)
                return order
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("Live order attempt failed | attempt=%s error=%s", attempt, exc)
                if attempt < (self.max_order_retries + 1):
                    time.sleep(self.retry_delay_ms / 1000.0)
        raise RuntimeError(f"Order execution failed after retries: {last_error}")

    def _finalize_trade(self, trade: Dict) -> Dict:

        self.state.trade_history.append(trade)
        realized_pnl = float(trade.get("realized_pnl", trade.get("pnl", 0.0)) or 0.0)
        self.state.realized_pnl = float(getattr(self.state, "realized_pnl", 0.0) or 0.0) + realized_pnl
        self.state.trades_executed = int(getattr(self.state, "trades_executed", 0) or 0) + 1
        equity = float(getattr(self.state, "equity", 100000.0) or 100000.0) + realized_pnl
        self.state.equity = equity
        peak = float(getattr(self.state, "peak_equity", equity) or equity)
        self.state.peak_equity = max(peak, equity)
        if self.state.peak_equity > 0:
            self.state.total_drawdown_pct = ((self.state.peak_equity - equity) / self.state.peak_equity) * 100.0
        trade["equity"] = equity

        strategy_id = str(trade.get("strategy_id", "")).strip()
        symbol = str(trade.get("symbol", "")).strip()
        if self.portfolio_engine and strategy_id and symbol:
            self.portfolio_engine.record_performance(strategy_id, symbol, float(trade.get("pnl", 0.0) or 0.0))

        trade["explanation"] = self._explain_trade(trade)
        self.state.last_trade_explanation = trade["explanation"]
        self.state.last_execution = {
            "symbol": trade["symbol"],
            "side": trade["side"],
            "broker": trade["broker"],
            "slippage_bps": float(trade.get("slippage_bps", 0.0) or 0.0),
            "partial_fill": bool(trade.get("partial_fill", False)),
            "fill_status": trade.get("fill_status", "FILLED"),
        }
        self._log_trade(trade)
        self._update_performance_log(trade)
        self._send_trade_alert(trade)
        
        # Record signal execution in diversity engine for cooldown and throttle tracking
        symbol = str(trade.get("symbol", "")).upper()
        strategy_type = str(trade.get("strategy_type", trade.get("strategy", "UNKNOWN"))).upper()
        strategy_id = str(trade.get("strategy_id", "UNKNOWN"))
        confidence = float(trade.get("confidence", 0.5) or 0.5)
        diversity_engine = get_signal_diversity_engine()
        diversity_engine.record_executed_signal(symbol, strategy_type, self._cycle_no, confidence)
        logger.info(
            "SignalDiversityEngine: Recorded %s/%s execution (symbol=%s, confidence=%.2f)",
            strategy_type,
            strategy_id,
            symbol,
            confidence,
        )

        result = {
            "status": "TRADE",
            "order_id": trade.get("order_id", ""),
            "symbol": trade["symbol"],
            "side": trade["side"],
            "qty": trade["qty"],
            "price": trade["price"],
            "pnl": float(trade.get("cycle_pnl", trade.get("pnl", 0.0)) or 0.0),
            "equity": equity,
            "strategy_id": trade["strategy_id"],
            "trade_type": trade["trade_type"],
            "regime": trade.get("regime", "RANGE"),
            "confidence": trade["confidence"],
            "broker": trade["broker"],
            "slippage_bps": float(trade.get("slippage_bps", 0.0) or 0.0),
            "partial_fill": bool(trade.get("partial_fill", False)),
        }
        logger.info(
            "Order executed | symbol=%s side=%s qty=%s price=%s broker=%s",
            result["symbol"],
            result["side"],
            result["qty"],
            result["price"],
            result["broker"],
        )
        return result

    def _explain_trade(self, trade: Dict) -> str:
        try:
            from quant_ecosystem.operating.intelligence.trade_explainer import explain_trade
            return explain_trade(
                trade,
                regime=str(trade.get("regime", "RANGE")),
                market_bias=str(getattr(self.state, "market_bias", "NEUTRAL")),
            )
        except Exception:
            return f"Trade because {trade.get('strategy_id', 'strategy')} aligned with {trade.get('regime', 'RANGE')}."

    def _log_trade(self, trade: Dict) -> None:
        self.trade_journal_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.trade_journal_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
                if not isinstance(data, list):
                    data = []
        except Exception:
            data = []
        data.append(trade)
        with self.trade_journal_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

    def _send_trade_alert(self, trade: Dict) -> None:
        if not self.telegram:
            return
        try:
            if hasattr(self.telegram, "send_trade_alert"):
                self.telegram.send_trade_alert(trade)
            elif hasattr(self.telegram, "notify_trade"):
                self.telegram.notify_trade(
                    {
                        "status": "TRADE",
                        "strategy_id": trade.get("strategy_id", trade.get("strategy", "MANUAL")),
                        "symbol": trade.get("symbol", "UNKNOWN"),
                        "side": trade.get("side", "BUY"),
                        "qty": trade.get("qty", 0),
                        "trade_type": trade.get("trade_type", "INTRADAY"),
                        "regime": trade.get("regime", "NA"),
                        "price": trade.get("price", trade.get("entry", 0.0)),
                        "confidence": trade.get("confidence", 1.0),
                        "pnl": trade.get("pnl", 0.0),
                        "equity": trade.get("equity", 0.0),
                    }
                )
        except Exception as exc:
            logger.warning("Trade alert dispatch failed | error=%s", exc)

    def _load_performance_log(self) -> Dict[str, Dict]:
        try:
            with self.performance_log_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
                return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _update_performance_log(self, trade: Dict) -> None:
        self.performance_log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._load_performance_log()
        key = str(trade.get("strategy_id", trade.get("strategy", "UNKNOWN")))
        bucket = dict(payload.get(key, {}))
        trades = int(bucket.get("trades", 0) or 0) + 1
        pnl = float(trade.get("pnl", 0.0) or 0.0)
        total_pnl = float(bucket.get("total_pnl", 0.0) or 0.0) + pnl
        wins = int(bucket.get("wins", 0) or 0) + (1 if pnl > 0 else 0)
        losses = int(bucket.get("losses", 0) or 0) + (1 if pnl < 0 else 0)
        avg_win = ((float(bucket.get("avg_win", 0.0) or 0.0) * max(wins - 1, 0)) + max(pnl, 0.0)) / max(wins, 1)
        avg_loss = ((float(bucket.get("avg_loss", 0.0) or 0.0) * max(losses - 1, 0)) + min(pnl, 0.0)) / max(losses, 1)
        payload[key] = {
            "strategy_id": key,
            "trades": trades,
            "wins": wins,
            "losses": losses,
            "win_rate": round((wins / max(trades, 1)) * 100.0, 2),
            "avg_pnl": round(total_pnl / max(trades, 1), 4),
            "avg_win": round(avg_win, 4),
            "avg_loss": round(avg_loss, 4),
            "total_pnl": round(total_pnl, 4),
            "last_trade_at": trade.get("time", datetime.now().isoformat()),
        }
        with self.performance_log_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def _market_price(self, symbol: str) -> float:
        if self.market_data:
            try:
                price = self.market_data.get_price_sync(symbol)
                if price:
                    return float(price)
            except Exception:
                pass
        return 0.0

    def _asset_class(self, symbol: str) -> str:
        sym = str(symbol or "").upper()
        if sym.startswith("CRYPTO:"):
            return "CRYPTO"
        if sym.startswith("FX:"):
            return "FOREX"
        if "CE" in sym or "PE" in sym:
            return "OPTIONS"
        if "FUT" in sym:
            return "FUTURES"
        return "EQUITY"

    def _compute_slippage_bps(self, intended_price: float, executed_price: float) -> float:
        if intended_price <= 0:
            return 0.0
        return round(((executed_price - intended_price) / intended_price) * 10000.0, 4)

    def _trade_type(self, signal: Optional[Dict] = None) -> str:
        return str((signal or {}).get("trade_type", "INTRADAY")).upper()

    def _portfolio_exposure_pct(self) -> float:
        cash = float(getattr(self.state, "cash_balance", 0.0) or 0.0)
        equity = float(getattr(self.state, "equity", 1.0) or 1.0)
        if cash <= 0:
            return 0.0
        exposure = max(equity - cash, 0.0)
        return round((exposure / max(equity, 1.0)) * 100.0, 2)

    def start_trading(self) -> str:
        self.state.trading_enabled = True
        self.state.trading_halted = False
        return "Trading started."

    def stop_trading(self) -> str:
        self.state.trading_enabled = False
        return "Trading stopped."

    def kill_switch(self) -> str:
        self.state.trading_enabled = False
        self.state.trading_halted = True
        return "Kill switch activated. Trading halted."

    def set_auto_mode(self, enabled: bool) -> str:
        self.state.auto_mode = bool(enabled)
        return f"Auto mode set to {self.state.auto_mode}."

    def set_mode(self, mode: str) -> str:
        self.mode = str(mode).upper()
        self._multi_broker.mode = self.mode
        self.state.trading_mode = self.mode
        return f"Mode set to {self.mode}"

    def set_trading_mode(self, mode: str) -> str:
        return self.set_mode(mode)

    def set_risk_preset(self, preset: str) -> str:
        normalized = str(preset).upper()
        factor = _RISK_PRESET_MAP.get(normalized)
        if factor is None:
            return "Invalid risk preset. Use 25%, 50%, or 100%."
        if self.risk_engine and hasattr(self.risk_engine, "set_trade_risk_pct"):
            base = float(getattr(self.risk_engine, "base_trade_risk", 1.0) or 1.0)
            value = self.risk_engine.set_trade_risk_pct(base * factor)
            self.state.risk_preset = normalized
            return f"Risk preset {normalized} applied. Trade risk={round(float(value), 2)}%."
        self.state.risk_preset = normalized
        return f"Risk preset {normalized} applied."

    def set_strategy_profile(self, profile: str) -> str:
        normalized = str(profile).upper()
        self.state.strategy_profile = normalized
        return f"Strategy profile set to {normalized}."

    def submit_order(self, symbol: str, side: str, qty: int, price: float, fee: float = 0.0, meta: Optional[Dict] = None) -> Dict:
        return self.run_cycle(signal={"symbol": symbol, "side": side, "qty": qty, "price": price, "fee": fee, "strategy_id": "MANUAL", "trade_type": "MANUAL", "confidence": 1.0, "participation": 1.0}, regime="MANUAL")

    def update_positions(self) -> Dict:
        if hasattr(self.broker, "get_account_snapshot"):
            return self.broker.get_account_snapshot(getattr(self.state, "latest_prices", {}))
        return {}

    def get_status_report(self) -> str:
        return (
            f"enabled={getattr(self.state, 'trading_enabled', False)} "
            f"halted={getattr(self.state, 'trading_halted', False)} "
            f"mode={getattr(self.state, 'trading_mode', self.mode)} "
            f"auto={getattr(self.state, 'auto_mode', False)} "
            f"profile={getattr(self.state, 'strategy_profile', 'BETA')} "
            f"risk_preset={getattr(self.state, 'risk_preset', '100%')} "
            f"source={self._multi_broker.account_source} "
            f"equity={round(float(getattr(self.state, 'equity', 0.0) or 0.0), 2)} "
            f"cash={round(float(getattr(self.state, 'cash_balance', 0.0) or 0.0), 2)} "
            f"realized={round(float(getattr(self.state, 'realized_pnl', 0.0) or 0.0), 2)} "
            f"drawdown={round(float(getattr(self.state, 'total_drawdown_pct', 0.0) or 0.0), 2)}% "
            f"exposure={self._portfolio_exposure_pct()}% "
            f"trades={len(getattr(self.state, 'trade_history', []) or [])}"
        )

    def get_positions_report(self) -> str:
        positions = []
        if hasattr(self.broker, "get_positions"):
            try:
                positions = self.broker.get_positions()
            except Exception:
                positions = []
        if not positions:
            return "Open positions: 0"
        return f"Open positions: {len(positions)} | {positions}"

    def get_strategy_report(self) -> str:
        if self.strategy_engine and hasattr(self.strategy_engine, "_get_live_strategies"):
            try:
                strategies = self.strategy_engine._get_live_strategies() or {}
                return f"Active strategies: {list(strategies.keys()) if strategies else 'none'}"
            except Exception:
                return "Active strategies: unavailable"
        active = list(getattr(self.strategy_engine, "active_ids", []) or [])
        return f"Active strategies: {active if active else 'none'}"

    def get_dashboard_report(self) -> str:
        trades = list(getattr(self.state, "trade_history", []) or [])
        symbol = self.symbols[0] if self.symbols else "-"
        price = self.market_data.get_price_sync(symbol)
        if trades:
            wins = [row for row in trades if float(row.get("cycle_pnl", 0.0)) > 0]
            profit_abs = sum(float(row.get("cycle_pnl", 0.0) or 0.0) for row in trades)
            win_rate = (len(wins) / len(trades)) * 100.0
            last = trades[-1]
            last_line = f"Last: {last.get('trade_type', 'NA')} {last.get('side', '')} {last.get('symbol', '')} pnl={round(float(last.get('cycle_pnl', 0.0) or 0.0), 2)}"
        else:
            profit_abs = 0.0
            win_rate = 0.0
            last_line = "Last: NA"
        return (
            "Institutional Control Terminal\n\n"
            f"Symbol: {symbol}\n"
            f"Price: {round(price, 2)}\n"
            f"Mode: {getattr(self.state, 'trading_mode', self.mode)}\n"
            f"TradeType: {self._trade_type()}\n"
            f"Winrate: {round(win_rate, 2)}% | Profit: {round(profit_abs, 2)}\n"
            f"Equity: {round(float(getattr(self.state, 'equity', 0.0) or 0.0), 2)}\n"
            f"Queue: {len(self._order_queue)} pending\n"
            f"Why: {getattr(self.state, 'last_trade_explanation', 'Awaiting signal')}\n"
            f"{last_line}"
        )
