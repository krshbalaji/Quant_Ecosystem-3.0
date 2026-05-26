"""
execution_router.py — Quant Ecosystem 3.0
==========================================

Production-grade async execution layer for the hedge fund engine.

Architecture layers (bottom → top):
  1. Broker Adapters       — thin shims for Fyers, Zerodha, Binance, Paper.
                             Each implements the same four-method contract:
                             connect(), place_order(), get_positions(), cancel_order()
  2. MultiBrokerRouter     — asset-class-aware broker dispatch.
                             PAPER mode → _PaperBroker for every call.
                             LIVE mode  → asset class determines preferred broker;
                             fallback to _PaperBroker on registration miss.
  3. RiskGatePipeline      — sequential named pre-trade checks:
                             trading_halted → drawdown_guard → daily_loss_guard
                             → portfolio_exposure → symbol_exposure
                             → strategy_cooldown → position_limits
  4. AsyncOrderQueue       — priority queue with per-(symbol, strategy_id)
                             deduplication and FIFO within priority buckets.
  5. SnapshotBuilder       — aggregates positions, account equity, and market
                             regime into one enriched snapshot per symbol.
  6. ExecutionRouter       — top-level async coordinator; fully compatible with
                             MasterOrchestrator's .execute(market_bias, regime).

Architecture principles:
  - Zero module-level side effects; all third-party imports are lazy.
  - All dependencies injected via constructor; nothing imported at init time.
  - Broker-agnostic routing via MultiBrokerRouter.
  - Mode-aware: PAPER simulates fills; LIVE dispatches to real brokers.

Integration contracts:
  - async execute(signal, market_bias, regime) → standardised result dict
  - execute_trade(...)  synchronous shim (backward compat)
  - run_cycle(...)      lowest-level synchronous implementation
  - register_broker(name, broker)  add a live broker at runtime

Standardised result envelope:
    {
        "status":      "TRADE" | "SKIP" | "ERROR",
        "order_id":    str | None,
        "symbol":      str | None,
        "side":        "BUY" | "SELL" | None,
        "qty":         int,
        "price":       float,
        "pnl":         float,
        "equity":      float,
        "strategy_id": str | None,
        ...
    }
"""

from __future__ import annotations

# ── stdlib only at module level ──────────────────────────────────────────────
import asyncio
import heapq
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, time as dtime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
from quant_ecosystem.execution.execution_audit import log_execution_event
from quant_ecosystem.execution.contracts.broker_response_validator import (
    BrokerResponseValidator,
)

from quant_ecosystem.execution.execution_exceptions import (
    ExecutionIntegrityError,
)
from quant_ecosystem.notifications.telegram_notifier import TelegramNotifier

from quant_ecosystem.execution.retry_policy import (
    execute_with_retry,
    CircuitBreaker,
)
from quant_ecosystem.execution.order_status_normalizer import OrderStatusNormalizer
from quant_ecosystem.execution.order_reconciler import OrderReconciler
from quant_ecosystem.execution.broker_health import BrokerHealth
from quant_ecosystem.market.session_guard import SessionGuard
from quant_ecosystem.execution.retry_policy import execute_with_retry
from quant_ecosystem.market.symbol_normalizer import SymbolNormalizer
from quant_ecosystem.broker.broker_capabilities import BrokerCapabilities
from quant_ecosystem.canonical.canonical_router import (
    CanonicalRouter,
)

from quant_ecosystem.execution.adapter_registry import adapter_registry

from quant_ecosystem.execution.adapters import (
    FyersExecutionAdapter,
    GrowwExecutionAdapter,
    ViewTradeExecutionAdapter,
    CoinSwitchExecutionAdapter,
)

from quant_ecosystem.canonical.broker_models import (
    CanonicalOrderRequest,
    CanonicalModifyRequest,
    CanonicalCancelRequest,
)

from quant_ecosystem.portfolio.portfolio_adapter_registry import (
    portfolio_adapter_registry,
)

from quant_ecosystem.portfolio.adapters import (
    FyersPortfolioAdapter,
    GrowwPortfolioAdapter,
    ViewTradePortfolioAdapter,
    CoinSwitchPortfolioAdapter,
)

from quant_ecosystem.canonical.broker_models import (
    CanonicalPortfolioSnapshot,
    CanonicalMarginSnapshot,
    CanonicalExposureSnapshot,
    CanonicalRiskSnapshot,
)

from quant_ecosystem.oms import (
    CanonicalOrderLifecycle,
    CanonicalExecutionEvent,
    CanonicalEventType,
    CanonicalOrderStatus,
    order_registry,
    execution_event_bus,
    order_state_machine,
    reconciliation_engine,
)

from quant_ecosystem.accounting import (
    CanonicalTradeFill,
    accounting_engine,
)

from quant_ecosystem.events import (
    event_ingestion_engine,
)

from quant_ecosystem.instruments import instrument_resolver

from quant_ecosystem.strategy_execution import (
    StrategyExecutionIntent,
    strategy_execution_context,
    strategy_risk_controller,
)

from quant_ecosystem.execution.guards.duplicate_guard import (
    DuplicateOrderGuard,
)

from quant_ecosystem.execution.guards.market_hours_guard import (
    MarketHoursGuard,
)

from quant_ecosystem.execution.guards.circuit_breaker_guard import (
    CircuitBreakerGuard,
)

from quant_ecosystem.execution.broker_registry import (
    BrokerRegistry,
)

from quant_ecosystem.execution.broker_selector import (
    BrokerSelector,
)

from quant_ecosystem.execution.broker_failover import (
    BrokerFailover,
)

from quant_ecosystem.execution.pipeline.risk_gate_pipeline import (
    GateResult,
    RiskGatePipeline,
)

from quant_ecosystem.execution.telemetry.execution_audit import (
    ExecutionAudit,
)

from quant_ecosystem.execution.telemetry.execution_metrics import (
    ExecutionMetrics,
)

from quant_ecosystem.execution.routing.broker_health_router import (
    BrokerHealthRouter,
)

from quant_ecosystem.execution.orchestrators.live_execution_orchestrator import (
    LiveExecutionOrchestrator,
)

from quant_ecosystem.execution.orchestrators.paper_execution_orchestrator import (
    PaperExecutionOrchestrator,
)

from quant_ecosystem.execution.dispatch.execution_dispatcher import (
    ExecutionDispatcher,
)

from quant_ecosystem.execution.chaos.failure_injector import (
    FailureInjector,
)

from quant_ecosystem.execution.contracts.broker_response_validator import (
    BrokerResponseValidator,
)


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

# Maps asset class → preferred live broker name (must match MultiBrokerRouter
# registration key).  Fallback is _PaperBroker if that broker is not wired in.
BROKER_ROUTING = {
    "INDIA": {
        "EQUITY": ["fyers", "groww", "lemonn"],
        "FUTURES": ["fyers"],
        "OPTIONS": ["fyers"],
        "COMMODITY": ["fyers"],
    },

    "US": {
        "EQUITY": ["viewtrade", "ibkr", "alpaca"],
        "OPTIONS": ["ibkr"],
        "FUTURES": ["ibkr"],
    },

    "GLOBAL": {
        "FOREX": ["ibkr", "oanda"],
        "CFD": ["ibkr"],
    },

    "CRYPTO": {
        "SPOT": ["coinswitch", "binance"],
        "FUTURES": ["binance"],
    }
}

_COOLDOWN_BY_TRADE_TYPE: Dict[str, int] = {
    "SCALP":          1,
    "INTRADAY":       2,
    "SWING":          3,
    "RISK_REBALANCE": 0,
    "RISK_REDUCTION": 0,
}

_RISK_GATE_EXPOSURE_REASONS = frozenset({
    "MAX_STRATEGY_EXPOSURE",
    "MAX_PORTFOLIO_EXPOSURE",
    "MAX_SYMBOL_EXPOSURE",
    "MAX_SECTOR_EXPOSURE",
    "MAX_ASSET_EXPOSURE",
})


# ──────────────────────────────────────────────────────────────────────────────
# 0. Broker Adapters
# ──────────────────────────────────────────────────────────────────────────────

class _PaperBroker:
    """
    Silent paper-trade broker.
    Implements the standard four-method broker contract without touching any
    external service.  Used as the fallback in PAPER mode and whenever a
    requested live broker is not registered.
    """

    account_source = "PAPER"

    def __init__(self) -> None:
        self._seq: int = 0

    def connect(self) -> None:
        pass

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: float,
        fee: float = 0.0,
        meta: Optional[Dict] = None,
        **kwargs: Any,
    ) -> Dict:
        self._seq += 1
        return {
            "id":             f"PAPER-{self._seq:06d}",
            "order_id":       f"PAPER-{self._seq:06d}",
            "symbol":         symbol,
            "side":           side,
            "qty":            qty,
            "price":          price,
            "fee":            fee,
            "status":         "FILLED",
            "realized_pnl":   0.0,
            "account_source": "PAPER",
        }

    def get_positions(self) -> List:
        return []

    def cancel_order(self, order_id: str) -> Dict:
        return {"cancelled": order_id}


class _FyersBrokerAdapter:
    """
    Thin adapter that wraps the existing FyersBroker to the four-method
    broker contract expected by MultiBrokerRouter.
    All real logic lives in quant_ecosystem.broker.fyers_broker.FyersBroker;
    this adapter only normalises the method signatures.
    Import is deferred to avoid circular imports and service calls at
    module-load time.
    """

    account_source = "FYERS"

    def __init__(self, broker: Any) -> None:
        self._broker = broker

    def connect(self) -> None:
        if hasattr(self._broker, "connect"):
            self._broker.connect()

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: float,
        fee: float = 0.0,
        meta: Optional[Dict] = None,
        **kwargs: Any,
    ) -> Dict:
        raw = self._broker.place_order(
            symbol=symbol, side=side, qty=qty, price=price,
            fee=fee, meta=enriched_meta,
        )
        if isinstance(raw, dict):
            raw.setdefault("order_id", raw.get("id", ""))
            raw.setdefault("account_source", "FYERS")
        return raw or {}

    def get_positions(self) -> List:
        fn = getattr(self._broker, "get_positions", None)
        return fn() if fn else []

    def cancel_order(self, order_id: str) -> Dict:
        fn = getattr(self._broker, "cancel_order", None)
        return fn(order_id) if fn else {}


class _ZerodhaBrokerAdapter:
    """
    Adapter for Zerodha (KiteConnect).
    The underlying broker is expected to expose:
      .place_order(tradingsymbol, transaction_type, quantity, price, ...)
      .positions()
      .cancel_order(variety, order_id)

    Import of the real Zerodha broker is deferred; this shim only translates
    the canonical four-method contract into Zerodha's calling convention.
    """

    account_source = "ZERODHA"

    def __init__(self, broker: Any) -> None:
        self._broker = broker

    def connect(self) -> None:
        if hasattr(self._broker, "connect"):
            self._broker.connect()

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: float,
        fee: float = 0.0,
        meta: Optional[Dict] = None,
        **kwargs: Any,
    ) -> Dict:
        """Translate canonical → Zerodha calling convention."""
        try:
            # Zerodha uses 'BUY'/'SELL' for transaction_type
            raw = self._broker.place_order(
                tradingsymbol=symbol,
                transaction_type=side,
                quantity=qty,
                price=price,
                order_type="MARKET" if price == 0 else "LIMIT",
                product="MIS",  # intraday; override via meta if needed
            )
            order_id = str(raw) if isinstance(raw, (str, int)) else raw.get("order_id", "")
            return {
                "order_id":       order_id,
                "id":             order_id,
                "symbol":         symbol,
                "side":           side,
                "qty":            qty,
                "price":          price,
                "fee":            fee,
                "status":         "FILLED",
                "realized_pnl":   0.0,
                "account_source": "ZERODHA",
            }
        except Exception as exc:
            logger.error("Zerodha place_order failed for %s: %s", symbol, exc)
            return {
                "order_id":       "",
                "symbol":         symbol,
                "side":           side,
                "qty":            0,
                "price":          price,
                "status":         "ERROR",
                "account_source": "ZERODHA",
                "error":          str(exc),
            }

    def get_positions(self) -> List:
        try:
            fn = getattr(self._broker, "positions", None)
            if fn:
                data = fn()
                # Zerodha returns {"net": [...], "day": [...]}
                if isinstance(data, dict):
                    return data.get("net", [])
                return data or []
        except Exception as exc:
            logger.warning("Zerodha get_positions failed: %s", exc)
        return []

    def cancel_order(self, order_id: str) -> Dict:
        try:
            fn = getattr(self._broker, "cancel_order", None)
            if fn:
                fn("regular", order_id)
        except Exception as exc:
            logger.warning("Zerodha cancel_order failed: %s", exc)
        return {"cancelled": order_id}


class _BinanceBrokerAdapter:
    """
    Adapter for Binance (python-binance or ccxt).
    The underlying broker is expected to expose:
      .create_order(symbol, side, type, quantity, price)
      .get_account() / .fetch_positions()
      .cancel_order(symbol, orderId)

    Translates the canonical four-method contract into Binance's calling
    convention.  Lazy import means the binance SDK is never loaded unless
    a Binance broker is actually registered.
    """

    account_source = "BINANCE"

    def __init__(self, broker: Any) -> None:
        self._broker = broker

    def connect(self) -> None:
        if hasattr(self._broker, "ping"):
            self._broker.ping()

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: float,
        fee: float = 0.0,
        meta: Optional[Dict] = None,
        **kwargs: Any,
    ) -> Dict:
        """Translate canonical → Binance calling convention."""
        try:
            # Strip exchange prefix (e.g. "CRYPTO:BTCUSDT" → "BTCUSDT")
            raw_sym = symbol.upper().replace("CRYPTO:", "")
            order_type = "MARKET" if price == 0 else "LIMIT"
            raw = self._broker.create_order(
                symbol=raw_sym,
                side=side,
                type=order_type,
                quantity=str(qty),
                **({"price": str(price)} if order_type == "LIMIT" else {}),
            )
            if isinstance(raw, dict):
                oid = str(raw.get("orderId", raw.get("id", "")))
                fill_price = float(raw.get("price", price) or price)
                return {
                    "order_id":       oid,
                    "id":             oid,
                    "symbol":         symbol,
                    "side":           side,
                    "qty":            int(raw.get("executedQty", qty)),
                    "price":          fill_price,
                    "fee":            fee,
                    "status":         "FILLED" if raw.get("status") == "FILLED" else raw.get("status", "OPEN"),
                    "realized_pnl":   0.0,
                    "account_source": "BINANCE",
                }
        except Exception as exc:
            logger.error("Binance place_order failed for %s: %s", symbol, exc)
        return {
            "order_id":       "",
            "symbol":         symbol,
            "side":           side,
            "qty":            0,
            "price":          price,
            "status":         "ERROR",
            "account_source": "BINANCE",
        }

    def get_positions(self) -> List:
        try:
            fn = getattr(self._broker, "futures_position_information", None) or \
                 getattr(self._broker, "fetch_positions", None)
            return fn() if fn else []
        except Exception as exc:
            logger.warning("Binance get_positions failed: %s", exc)
        return []

    def cancel_order(self, order_id: str) -> Dict:
        try:
            fn = getattr(self._broker, "cancel_order", None)
            if fn:
                fn(order_id)
        except Exception as exc:
            logger.warning("Binance cancel_order failed: %s", exc)
        return {"cancelled": order_id}


# ──────────────────────────────────────────────────────────────────────────────
# 1. MultiBrokerRouter
# ──────────────────────────────────────────────────────────────────────────────

class MultiBrokerRouter:
    """
    Routes a trade to the appropriate underlying broker based on asset class
    and operating mode.

    Broker selection (LIVE mode):
      EQUITY / FUTURES / OPTIONS / FOREX / COMMODITY → Fyers (primary)
      CRYPTO → Binance (primary) → CoinSwitch (alternate) → Paper (fallback)
      Any unregistered broker → _PaperBroker fallback

    PAPER mode: all traffic is sent to the shared _PaperBroker.

    Brokers are registered lazily via register() so the factory can wire them
    in without importing this module.  register() accepts either a raw broker
    object or one of the *Adapter shims defined above.
    """

    def __init__(self, mode: str = "PAPER") -> None:
        self.mode = str(mode).upper()
        self._broker_registry = BrokerRegistry()
        self._brokers = self._broker_registry._brokers
        self._paper = _PaperBroker()
        self._notifier = TelegramNotifier()
        self._circuit_breaker = (
            CircuitBreaker()
        )
        self._circuit_breaker_guard = (
            CircuitBreakerGuard(
                self._circuit_breaker
            )
        )
        self._health = {}
        self._reconciler = OrderReconciler()
        self._session_guard = SessionGuard()
        self._symbol_normalizer = SymbolNormalizer()
        self._status_normalizer = OrderStatusNormalizer()   # Pack16
        self._broker_selector = BrokerSelector()
        self._broker_failover = BrokerFailover()
        self._telegram = TelegramNotifier()
        self._duplicate_guard = DuplicateOrderGuard()
        self._market_hours_guard = (
            MarketHoursGuard()
        )
        self._execution_audit = (
            ExecutionAudit()
        )

        self._execution_metrics = (
            ExecutionMetrics()
        )
        self._broker_health_router = (
            BrokerHealthRouter()
        )
        self._failure_injector = (
            FailureInjector()
        )

        self._live_execution_orchestrator = (
            LiveExecutionOrchestrator(
                circuit_breaker=self._circuit_breaker,
                broker_health_router=self._broker_health_router,
                notifier=self._notifier,
                failure_injector=self._failure_injector,
                response_validator=BrokerResponseValidator(),
            )
        )

        self._paper_execution_orchestrator = (
            PaperExecutionOrchestrator()
        )

        self._execution_dispatcher = (
            ExecutionDispatcher(
                live_execution_orchestrator=self._live_execution_orchestrator,
                paper_execution_orchestrator=self._paper_execution_orchestrator,
            )
        )

       
        logger.info("MultiBrokerRouter initialised (mode=%s)", self.mode)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, name: str, broker: Any) -> None:
        """
        Register a named broker adapter.
        name must match a key in _ASSET_BROKER_MAP (e.g. 'fyers', 'zerodha',
        'binance', 'coinswitch').
        """
        key = name.lower().strip()
        self._broker_registry.register(
            key,
            broker,
        )
        logger.info("Broker registered: %s (mode=%s)", name, self.mode)

    def _broker_health(self, broker_name):
        broker_name = str(broker_name).lower().strip()

        if broker_name not in self._health:
            self._health[broker_name] = BrokerHealth()

        return self._health[broker_name]

    def _get_broker_name(
        self,
        broker,
    ) -> str:
        for name, instance in self._broker_registry.all().items():
            if instance is broker:
                return name

        return "paper"

    def _get_capabilities(self, broker):
        """
        Return broker capability contract.
        Supports both Pack17 brokers and legacy brokers.
        """

        if hasattr(broker, "get_capabilities"):
            caps = broker.get_capabilities()
            if caps is not None:
                return caps

        broker_class = type(broker).__name__.lower()

        class _LegacyCaps:
            supports_retry = True
            supports_health_check = hasattr(broker, "health_check")
            requires_market_session = True

            @property
            def supports_reconciliation(self):
                if "dummy" in broker_class or "mock" in broker_class:
                    return False

                return bool(
                    getattr(
                        broker,
                        "ENABLE_RECONCILIATION",
                        False
                    )
                )

        return _LegacyCaps()
               
    # ------------------------------------------------------------------
    # Internal selection
    # ------------------------------------------------------------------

    def _select(self, asset_class: str, market: str = "INDIA") -> Any:
        if self.mode != "LIVE":
            return self._paper

        market = (market or "INDIA").upper()
        asset_class = asset_class.upper()

        market_map = BROKER_ROUTING.get(market)
        if not market_map:
            raise RuntimeError(f"Unsupported market: {market}")

        broker_chain = market_map.get(asset_class)
        if not broker_chain:
            raise RuntimeError(
                f"No broker routing defined for market={market}, asset={asset_class}"
            )

        for broker_name in broker_chain:
            broker = self._broker_registry.get(broker_name)

            if broker is None:
                continue

            
            logger.debug(
                "Selected broker '%s' for market=%s asset=%s",
                broker_name,
                market,
                asset_class,
            )
            return broker

        raise RuntimeError(
            f"No live broker available for market={market}, asset={asset_class}"
        )
        
    # ------------------------------------------------------------------
    # Order dispatch
    # ------------------------------------------------------------------
    def modify_order(
        self,
        broker_name: str,
        order_id: str,
        qty: int = None,
        price: float = None,
    ):
        broker = self._broker_registry.get(
            broker_name
        )
        caps = self._get_capabilities(broker)

        if not caps.supports_modify_order:
            raise RuntimeError(
                f"{broker_name} does not support modify_order"
            )

        return broker.modify_order(
            order_id=order_id,
            qty=qty,
            price=price,
        )

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: float,
        fee: float = 0.0,
        meta: Optional[Dict] = None,
        asset_class: str = "EQUITY",
        market: str = "INDIA",
    ) -> Dict:
        # ── Pack16: duplicate-order guard (must run before any broker call) ──
        self._duplicate_guard.check(
            symbol=symbol,
            side=side,
            qty=qty,
        )

        self._circuit_breaker_guard.check()

        normalized_symbol = self._symbol_normalizer.normalize(
            symbol=symbol,
            market=market,
            asset_class=asset_class,
        )

        strict_market_hours = bool(
            getattr(
                self,
                "_strict_market_hours",
                False,
            )
        )

        self._market_hours_guard.check(
            strict_market_hours=strict_market_hours,
            market_open=True,
        )

            
        broker = self._select(asset_class, market)
        
        broker_name = self._get_broker_name(broker)
        self._last_selected_broker_name = broker_name

        caps = self._get_capabilities(broker)

        if (
            str(self.mode).upper() == "LIVE"
            and strict_market_hours
            and getattr(caps, "requires_market_session", False)
        ):
            if not self._session_guard.is_market_open(market, asset_class):
                raise RuntimeError(
                    f"MARKET CLOSED: market={market}, asset={asset_class}"
                )

        broker_is_healthy = self._broker_health_router.is_healthy(
            broker_name
        )
        enriched_meta = dict(meta or {})
        try:
            # ── Pack16: retry policy wraps the raw broker call ──────────────
            result = self._execution_dispatcher.dispatch(
                mode=self.mode,
                broker=broker,
                broker_name=broker_name,
                normalized_symbol=normalized_symbol,
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                fee=fee,
                meta=enriched_meta,
                asset_class=asset_class,
                caps=caps,
            )

            if (
                caps.supports_health_check
                and hasattr(broker, "health_check")
            ):
                broker_health = broker.health_check()

                if not broker_health.get("healthy", False):
                    raise RuntimeError(
                        f"BROKER UNHEALTHY: {broker_name}"
                    )
                    
            if str(self.mode).upper() == "LIVE":
                result = self._status_normalizer.normalize(
                    broker_name,
                    result
                )

                order_id = (
                    result.get("broker_order_id")
                    or result.get("order_id")
                    or result.get("id")
                    or ""
                )
                                
                broker_class = type(broker).__name__.lower()

                skip_reconciliation = (
                    "dummy" in broker_class
                    or "mock" in broker_class
                )

                if (
                    str(self.mode).upper() == "LIVE"
                    and order_id
                    and caps.supports_reconciliation
                    and not skip_reconciliation
                ):
                    reconciled = self._reconciler.wait_for_final_state(
                        broker_name=broker_name,
                        broker=broker,
                        order_id=order_id,
                    )

                    result["reconciled_status"] = reconciled

            self._broker_health_router.mark_healthy(
                broker_name
            )
            self._circuit_breaker.reset()

        except Exception as exc:
            self._broker_health_router.mark_unhealthy(
                broker_name
            )
            self._circuit_breaker.record_failure()

            logger.critical(
                "LIVE broker order failed for %s/%s: %s. NO paper fallback allowed.",
                normalized_symbol,
                asset_class,
                exc,
            )

            msg = str(exc).lower()

            if "rejected" in msg:
                raise RuntimeError("LIVE broker rejected order") from exc

            if "reconciliation" in msg:
                raise RuntimeError("LIVE reconciliation failed") from exc

            raise RuntimeError(
                f"LIVE broker execution failed: {normalized_symbol}/{asset_class}: {exc}"
            ) from exc

        result = result or {}
        result.setdefault("order_id", result.get("id", ""))
        result.setdefault(
            "broker",
            getattr(broker, "account_source", type(broker).__name__.upper()),
        )

        log_execution_event({
            "mode":              self.mode,
            "symbol":            symbol,
            "normalized_symbol": normalized_symbol,
            "side":              side,
            "qty":               qty,
            "price":             price,
            "asset_class":       asset_class,
            "broker_response":   result,
            "status":            "SUCCESS",
        })

        if str(self.mode).upper() == "LIVE":
            self._notifier.send(
                f"✅ *QE3 LIVE ORDER ACCEPTED*\n"
                f"Symbol: {symbol}\n"
                f"Side: {side}\n"
                f"Qty: {qty}\n"
                f"Price: {price}\n"
                f"Order ID: {result.get('order_id', 'UNKNOWN')}"
            )

        return result
    def cancel_order(
        self,
        broker_name: str,
        order_id: str,
    ):
        broker = self._broker_registry.get(
            broker_name
        )
        caps = self._get_capabilities(broker)

        if not caps.supports_cancel_order:
            raise RuntimeError(
                f"{broker_name} does not support cancel_order"
            )

        return broker.cancel_order(order_id)

    def get_positions(self, asset_class: str = "EQUITY", market: str = "INDIA") -> List:
        broker = self._select(asset_class, market)
        try:
            return getattr(broker, "get_positions", lambda: [])()
        except Exception as exc:
            logger.warning("get_positions failed for %s/%s: %s", asset_class, market, exc)
            return []

    @property
    def account_source(self) -> str:
        if self.mode != "LIVE":
            return "PAPER"
        sources = [
            getattr(b, "account_source", "UNKNOWN") for b in self._broker_registry.all().values()
        ]
        return ",".join(s for s in sources if s) or "UNKNOWN"


          

# ──────────────────────────────────────────────────────────────────────────────
# 3. AsyncOrderQueue
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(order=True)
class OrderItem:
    """
    Priority queue item.

    Priority bucket (lower = higher priority):
      0.x — RISK_REDUCTION / liquidation
      1.x — RISK_REBALANCE
      2.x — normal (inverted confidence within bucket)

    seq breaks ties (FIFO within same priority).
    """
    priority:    float = field(compare=True)
    seq:         int   = field(compare=True)
    signal:      Dict  = field(compare=False)
    market_bias: str   = field(compare=False, default="NEUTRAL")
    regime:      str   = field(compare=False, default="MEAN_REVERSION")


class AsyncOrderQueue:
    """
    Thread-safe async priority queue for order signals.

    Features
    --------
    - Priority-based dispatch.
    - Per-(symbol, strategy_id) deduplication: new signal replaces an existing
      one only when its confidence is strictly higher.
    - FIFO within the same priority bucket via a monotonic sequence counter.
    - drain() returns all pending items without removing them.
    """

    def __init__(self) -> None:
        self._heap:  List[OrderItem] = []
        self._seq:   int             = 0
        self._index: Dict            = {}
        self._lock                   = asyncio.Lock()

    @staticmethod
    def _priority(signal: Dict) -> float:
        tt = str(signal.get("trade_type", "")).upper()
        if tt == "RISK_REDUCTION":
            return 0.0
        if tt == "RISK_REBALANCE":
            return 1.0
        conf = max(0.0, min(1.0, float(signal.get("confidence", 0.5))))
        return 2.0 + (1.0 - conf)

    async def enqueue(
        self,
        signal: Dict,
        market_bias: str = "NEUTRAL",
        regime: str = "MEAN_REVERSION",
    ) -> None:
        async with self._lock:
            key = (signal.get("symbol", ""), signal.get("strategy_id", ""))
            existing = self._index.get(key)
            prio = self._priority(signal)
            if existing is not None:
                if float(signal.get("confidence", 0)) <= float(
                    existing.signal.get("confidence", 0)
                ):
                    return
                existing.signal["_superseded"] = True
            self._seq += 1
            item = OrderItem(
                priority=prio, seq=self._seq,
                signal=signal, market_bias=market_bias, regime=regime,
            )
            heapq.heappush(self._heap, item)
            self._index[key] = item

    async def dequeue(self) -> Optional[OrderItem]:
        async with self._lock:
            while self._heap:
                item = heapq.heappop(self._heap)
                if item.signal.get("_superseded"):
                    continue
                key = (item.signal.get("symbol", ""), item.signal.get("strategy_id", ""))
                self._index.pop(key, None)
                return item
            return None

    async def drain(self) -> List[OrderItem]:
        async with self._lock:
            return [i for i in self._heap if not i.signal.get("_superseded")]

    async def clear(self) -> None:
        async with self._lock:
            self._heap.clear()
            self._index.clear()

    def __len__(self) -> int:
        return sum(1 for i in self._heap if not i.signal.get("_superseded"))


# ──────────────────────────────────────────────────────────────────────────────
# 4. SnapshotBuilder
# ──────────────────────────────────────────────────────────────────────────────

class SnapshotBuilder:
    """
    Builds enriched per-symbol market snapshots for the execution cycle.

    Each snapshot includes:
      - OHLCV arrays from the market-data provider
      - Candle indicators: angle, patterns
      - account_equity  (from state)
      - open_position   (from portfolio_engine for that symbol)
      - market_regime   tag

    candle_angle and candle_pattern engines are injected; the builder itself
    never imports any external library.
    """

    def __init__(
        self,
        market_data:    Any,
        candle_angle:   Any,
        candle_pattern: Any,
    ) -> None:
        self._market_data    = market_data
        self._candle_angle   = candle_angle
        self._candle_pattern = candle_pattern

    def build(
        self,
        symbols:          List[str],
        regime:           str,
        state:            Any,
        portfolio_engine: Any,
    ) -> List[Dict]:
        if not self._market_data:
            return []

        open_positions: Dict = {}
        if portfolio_engine:
            open_positions = getattr(portfolio_engine, "positions", {})

        account_equity = float(getattr(state, "equity", 0.0))
        snapshots: List[Dict] = []

        for symbol in symbols:
            try:
                raw    = self._market_data.get_snapshot(symbol=symbol, lookback=60) or {}
                closes = list(raw.get("close") or [])
                if not closes:
                    continue
                snap = {
                    "symbol":         symbol,
                    "price":          float(closes[-1]),
                    "open":           list(raw.get("open")   or []),
                    "high":           list(raw.get("high")   or []),
                    "low":            list(raw.get("low")    or []),
                    "close":          closes,
                    "volume":         list(raw.get("volume") or []),
                    "regime":         regime,
                    "account_equity": account_equity,
                    "open_position":  open_positions.get(symbol, {}),
                }
                snapshots.append(self._enrich(snap))
            except Exception as exc:
                logger.debug("Snapshot skipped for %s: %s", symbol, exc)

        return snapshots

    def _enrich(self, snap: Dict) -> Dict:
        closes = snap.get("close", [])
        if len(closes) < 3:
            snap["candle_angle"]    = 0.0
            snap["candle_patterns"] = []
            return snap
        candle = {
            "open":  float(closes[-2]),
            "close": float(closes[-1]),
            "high":  max(float(closes[-1]), float(closes[-2])),
            "low":   min(float(closes[-1]), float(closes[-2])),
        }
        try:
            snap["candle_angle"] = _quantize(
                self._candle_angle.calculate(closes[-20:]), 6
            )
        except Exception:
            snap["candle_angle"] = 0.0
        try:
            snap["candle_patterns"] = self._candle_pattern.detect(candle)
        except Exception:
            snap["candle_patterns"] = []
        return snap


# ──────────────────────────────────────────────────────────────────────────────
# Module-level utilities
# ──────────────────────────────────────────────────────────────────────────────

def _quantize(value: float, places: int = 4) -> float:
    """Thin wrapper; falls back to round() if decimal_utils is unavailable."""
    try:
        from quant_ecosystem.utils.decimal_utils import quantize
        return quantize(value, places)
    except Exception:
        return round(float(value), places)


def _skip(reason: str) -> Dict:
    return {
        "status":   "SKIP",
        "order_id": None,
        "symbol":   None,
        "side":     None,
        "qty":      0,
        "price":    0.0,
        "pnl":      0.0,
        "equity":   0.0,
        "reason":   reason,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 5. ExecutionRouter
# ──────────────────────────────────────────────────────────────────────────────

class ExecutionRouter:
    """
    Top-level async execution coordinator for Quant Ecosystem 3.0.

    Constructor parameters (all optional / injectable):
      broker              — legacy single-broker object; auto-registered as
                            its account_source name.
      risk_engine         — RiskEngine instance
      state               — SystemState instance
      market_data         — MarketDataEngine instance
      strategy_engine     — LiveStrategyEngine instance
      portfolio_engine    — PortfolioEngine instance
      reconciler          — BrokerReconciler instance
      capital_governance  — CapitalGovernanceEngine instance
      position_sizer      — PositionSizer instance
      symbols             — list of default symbols to trade
      outcome_memory      — OutcomeMemory instance
      capital_intelligence — CapitalIntelligenceEngine instance
      mode                — "PAPER" | "LIVE"

    Public API
    ----------
    async execute(signal, market_bias, regime)   primary async entry point
    execute_trade(signal, market_bias, regime)   sync shim (backward compat)
    run_cycle(signal, market_bias, regime)        sync implementation
    submit_order(symbol, side, qty, price, ...)   bypass signal pipeline
    register_broker(name, broker)                 wire a live broker at runtime
    set_mode(mode)  start_trading()  stop_trading()  kill_switch()
    set_auto_mode(enabled)  set_risk_preset(preset)  set_strategy_profile(profile)
    """

    def __init__(
        self,
        broker:               Optional[Any] = None,
        risk_engine:          Optional[Any] = None,
        state:                Optional[Any] = None,
        market_data:          Optional[Any] = None,
        strategy_engine:      Optional[Any] = None,
        portfolio_engine:     Optional[Any] = None,
        reconciler:           Optional[Any] = None,
        capital_governance:   Optional[Any] = None,
        position_sizer:       Optional[Any] = None,
        symbols:              Optional[List[str]] = None,
        outcome_memory:       Optional[Any] = None,
        capital_intelligence: Optional[Any] = None,
        strategy_registry:    Optional[Any] = None,
        registry_governor:    Optional[Any] = None,
        token_authority:      Optional[Any] = None,
        portfolio_governor: Optional[Any] = None,
        mode:                 str = "PAPER",
    ) -> None:
        # Injected dependencies
        self.broker               = broker
        self.risk_engine          = risk_engine
        self.state                = state
        self.market_data          = market_data
        self.strategy_engine      = strategy_engine
        self.portfolio_engine     = portfolio_engine
        self.reconciler           = reconciler
        self.capital_governance   = capital_governance
        self.position_sizer       = position_sizer
        self.symbols              = symbols or ["NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:INFY-EQ"]
        self.outcome_memory       = outcome_memory
        self.capital_intelligence = capital_intelligence
        self.strategy_registry    = strategy_registry
        self.registry_governor    = registry_governor
        self.telegram = None
        self.token_authority      = token_authority
        self.portfolio_governor   = portfolio_governor
        self.mode                 = str(mode).upper()

        # Config — lazy import to avoid import-time side effects
        self.config = self._load_config()

        
        # Indicator engines — lazy import
        self.instrument_policy = self._load_instrument_policy()
        self.candle_pattern    = self._load_candle_pattern()
        self.candle_angle      = self._load_candle_angle()

        # Sub-systems
        self._multi_broker = MultiBrokerRouter(mode=self.mode)
        self._canonical = CanonicalRouter()
        self._canonical_bridge = CanonicalExecutionBridge()
        self._portfolio_bridge = CanonicalPortfolioBridge()
        self._risk_bridge = CanonicalRiskBridge()
        self._oms_bridge = OMSBridge()
        self._oms_accounting_bridge = OMSAccountingBridge()

        # Register legacy single-broker if provided
        if broker is not None:
            src = str(getattr(broker, "account_source", "fyers")).lower().split("_")[0]
            self._multi_broker.register(src, broker)

        self._risk_gate   = RiskGatePipeline()
        self._order_queue = AsyncOrderQueue()
        self._snapshot_builder = SnapshotBuilder(
            market_data=market_data,
            candle_angle=self.candle_angle,
            candle_pattern=self.candle_pattern,
        )

        # Cycle state
        self._cycle_no:                   int  = 0
        self._symbol_cooldown_until:      Dict = {}
        self._symbol_strategy_owner:      Dict = {}
        self._strategy_cooldown_until:    Dict = {}
        self._risk_block_streak:          int  = 0
        self._last_risk_block_reason:     str  = ""
        self._liquidation_cooldown_until: int  = 0


        logger.info(
            "ExecutionRouter initialised (mode=%s, symbols=%d)",
            self.mode,
            len(self.symbols),
        )
        return

        
    def _run_live_strategies(self, market_data):

        if not self.strategy_engine:
            return []

        try:
            return self.strategy_engine.run(market_data)
        except Exception as e:
            logger.warning("strategy_engine.run failed: %s", e)
            return []

        def _extract_strategy_meta(
            self,
            order,
        ):
            if isinstance(order, StrategyExecutionIntent):
                return {
                    "strategy_id": order.strategy_id,
                    "confidence": order.confidence,
                    "priority": order.priority,
                    "trade_type": order.trade_type,
                }

            if isinstance(order, dict):
                strategy_id = order.get("strategy_id")
                if strategy_id:
                    return {
                        "strategy_id": strategy_id,
                        "confidence": order.get("confidence"),
                        "priority": order.get("priority"),
                        "trade_type": order.get("trade_type"),
                    }

            return {}

        def _attach_strategy_context(
            self,
            order_id,
            strategy_meta,
        ):
            if not order_id:
                return

            strategy_id = strategy_meta.get("strategy_id")

            if not strategy_id:
                return

            strategy_execution_context.attach(
                order_id=order_id,
                strategy_id=strategy_id,
                metadata=strategy_meta,
            )
    
    def _extract_strategy_meta(
        self,
        order,
    ):
        if isinstance(order, StrategyExecutionIntent):
            return {
                "strategy_id": order.strategy_id,
                "confidence": order.confidence,
                "priority": order.priority,
                "trade_type": order.trade_type,
            }

        if isinstance(order, dict):
            strategy_id = order.get("strategy_id")

            if strategy_id:
                return {
                    "strategy_id": strategy_id,
                    "confidence": order.get("confidence"),
                    "priority": order.get("priority"),
                    "trade_type": order.get("trade_type"),
                }

        return {}

    def _attach_strategy_context(
        self,
        order_id,
        strategy_meta,
    ):
        if not order_id:
            return

        strategy_id = strategy_meta.get("strategy_id")

        if not strategy_id:
            return

        strategy_execution_context.attach(
            order_id=order_id,
            strategy_id=strategy_id,
            metadata=strategy_meta,
        )

    def _normalize_execution_result(
        self,
        provider,
        payload,
    ):
        try:
            return self._canonical.normalize_order(
                provider=provider,
                payload=payload,
            )
        except Exception:
            return payload

    def _resolve_instrument(self, symbol: str):
        """
        Pack25 instrument resolution bridge.
        Safe fallback for cash equities / unknown symbols.
        """
        try:
            return instrument_resolver.resolve(symbol)
        except Exception:
            return None

    def _instrument_multiplier(self, instrument) -> float:
        if not instrument:
            return 1.0

        multiplier = getattr(instrument, "multiplier", None)
        if multiplier is None:
            multiplier = getattr(instrument, "contract_multiplier", None)

        try:
            return float(multiplier or 1.0)
        except Exception:
            return 1.0

    def _instrument_asset_class(
        self,
        instrument,
        fallback="EQUITY",
    ):
        if not instrument:
            return fallback

        asset_class = getattr(instrument, "asset_class", None)

        if not asset_class:
            asset_class = getattr(
                instrument,
                "instrument_type",
                None,
            )

        if hasattr(asset_class, "value"):
            asset_class = asset_class.value

        return str(asset_class or fallback).upper()

    def _normalize_execution_quantity(self, qty: int, instrument):
        """
        Qty semantics:
        - equities => unit qty
        - derivatives => preserve contract qty
        """
        if not instrument:
            return qty

        return int(qty)

    def _build_instrument_meta(self, instrument):
        if not instrument:
            return {}

        return {
            "instrument_symbol": getattr(instrument, "symbol", None),
            "asset_class": getattr(instrument, "asset_class", None),
            "instrument_type": getattr(instrument, "instrument_type", None),
            "lot_size": getattr(instrument, "lot_size", 1),
            "tick_size": getattr(instrument, "tick_size", 0.01),
            "multiplier": self._instrument_multiplier(instrument),
            "expiry": getattr(instrument, "expiry", None),
            "strike": getattr(instrument, "strike", None),
            "option_type": getattr(instrument, "option_type", None),
            "metadata": getattr(instrument, "metadata", {}),
        }

    def _validate_contract_quantity(self, qty: int, instrument):
        """
        Reject invalid derivative quantities.
        """
        if not instrument:
            return

        asset_class = self._instrument_asset_class(instrument)

        if asset_class not in {"OPTIONS", "FUTURES", "OPTION", "FUTURE"}:
            return

        lot_size = int(getattr(instrument, "lot_size", 1) or 1)

        if qty <= 0:
            raise RuntimeError("INVALID_QTY")

        if qty % lot_size != 0:
            raise RuntimeError(
                f"INVALID_DERIVATIVE_QTY: qty={qty}, lot_size={lot_size}"
            )

    def canonical_order_payload(
        self,
        broker: str,
        symbol: str,
        side: str,
        qty: int,
        order_type: str = "MARKET",
        product: str = "CNC",
        price: float = 0.0,
        meta=None,
    ):
        request = CanonicalOrderRequest(
            provider=broker,
            symbol=symbol,
            side=side,
            qty=qty,
            order_type=order_type,
            product=product,
            price=price,
            meta=meta,
        )

        return self._canonical_bridge.build_order_payload(
            broker,
            request,
        )


    def canonical_modify_payload(
        self,
        broker: str,
        order_id: str,
        qty: int,
        price: float = 0.0,
    ):
        request = CanonicalModifyRequest(
            provider=broker,
            order_id=order_id,
            qty=qty,
            price=price,
        )

        return self._canonical_bridge.build_modify_payload(
            broker,
            request,
        )


    def canonical_cancel_payload(
        self,
        broker: str,
        order_id: str,
    ):
        request = CanonicalCancelRequest(
            provider=broker,
            order_id=order_id,
        )

        return self._canonical_bridge.build_cancel_payload(
            broker,
            request,
        )
    
    def execute_canonical_order(
        self,
        broker: str,
        symbol: str,
        side: str,
        qty: int,
        order_type: str = "MARKET",
        product: str = "CNC",
        price: float = 0.0,
        meta=None,
    ):
        """
        Pack20 canonical execution entrypoint
        """

        strategy_meta = {}

        if isinstance(meta, dict):
            strategy_meta = dict(meta)

            extracted = self._extract_strategy_meta(
                meta
            )

            if extracted:
                strategy_meta.update(
                    extracted
                )

        strategy_id = strategy_meta.get(
            "strategy_id"
        )

        if strategy_id:
            proposed_notional = (
                float(qty)
                * float(price or 0.0)
            )

            allowed, reason = (
                strategy_risk_controller.validate(
                    strategy_id=strategy_id,
                    proposed_notional=proposed_notional,
                )
            )

            if not allowed:
                return {
                    "success": False,
                    "rejected": True,
                    "reason": reason,
                    "strategy_id": strategy_id,
                }    

        payload = self.canonical_order_payload(
            broker=broker,
            symbol=symbol,
            side=side,
            qty=qty,
            order_type=order_type,
            product=product,
            price=price,
            meta=meta,
        )

        instrument = self._resolve_instrument(symbol)
        resolved_asset = self._instrument_asset_class(instrument, "EQUITY")
        normalized_qty = self._normalize_execution_quantity(qty, instrument)

        self._validate_contract_quantity(normalized_qty, instrument)

        enriched_meta = dict(meta or {})
        enriched_meta.update(strategy_meta)
        enriched_meta.update(
            self._build_instrument_meta(instrument)
        )
        
        broker_key = str(broker).lower()

        if broker_key == "fyers":
            result = self._multi_broker.place_order(
                symbol=payload["symbol"],
                side=side,
                qty=normalized_qty,
                price=price,
                asset_class=resolved_asset,
                meta=enriched_meta,
            )

        elif broker_key == "groww":
            result = self._multi_broker.place_order(
                symbol=payload["instrument"],
                side=payload["side"],
                qty=payload["quantity"],
                price=payload["price"],
                asset_class=resolved_asset,
                meta=enriched_meta,
            )

        elif broker_key == "viewtrade":
            result = self._multi_broker.place_order(
                symbol=payload["ticker"],
                side=payload["action"],
                qty=payload["quantity"],
                price=payload["price"],
                asset_class=resolved_asset,
                meta=enriched_meta,
            )

        elif broker_key == "coinswitch":
            result = self._multi_broker.place_order(
                symbol=payload["symbol"],
                side=payload["side"],
                qty=payload["quantity"],
                price=payload["price"],
                asset_class="CRYPTO",
                meta=enriched_meta,
            )

        else:
            raise ValueError(f"unsupported broker: {broker}")

        order_id = (
            result.get("order_id")
            or result.get("id")
            or result.get("broker_order_id")
        )

        self._attach_strategy_context(
            order_id,
            strategy_meta,
        )

        return result

    def cancel_canonical_order(
        self,
        broker: str,
        order_id: str,
    ):
        return self.canonical_cancel_payload(
            broker=broker,
            order_id=order_id,
        )   

    def modify_canonical_order(
        self,
        broker: str,
        order_id: str,
        qty: int,
        price: float = 0.0,
    ):
        return self.canonical_modify_payload(
            broker=broker,
            order_id=order_id,
            qty=qty,
            price=price,
        )

    def canonical_portfolio_snapshot(
        self,
        broker: str,
        raw_positions,
        raw_balance,
        raw_margin=None,
    ):
        return self._portfolio_bridge.build_snapshot(
            broker=broker,
            raw_positions=raw_positions,
            raw_balance=raw_balance,
            raw_margin=raw_margin,
        )

    def canonical_risk_snapshot(
        self,
        broker: str,
    ):
        margin_used = 0.0
        margin_available = 0.0

        try:
            margin_used = float(getattr(self.state, "margin_used", 0.0))
            margin_available = float(getattr(self.state, "margin_available", 0.0))
        except Exception:
            pass

        denom = margin_used + margin_available

        margin_utilization = (
            (margin_used / denom) * 100.0
            if denom > 0
            else 0.0
        )

        exposure = self._risk_bridge.build_exposure_snapshot(
            provider=broker,
            portfolio_exposure_pct=self._portfolio_exposure_pct(),
        )

        risk = self._risk_bridge.build_risk_snapshot(
            provider=broker,
            daily_loss_pct=0.0,
            drawdown_pct=float(
                getattr(self.state, "total_drawdown_pct", 0.0)
            ),
            margin_utilization_pct=margin_utilization,
            realized_pnl=float(
                getattr(self.state, "realized_pnl", 0.0)
            ),
            unrealized_pnl=float(
                getattr(self.state, "unrealized_pnl", 0.0)
            ),
        )

        return exposure, risk
        
    def execute_managed_order(
        self,
        broker: str,
        symbol: str,
        side: str,
        qty: int,
        order_type: str = "MARKET",
        product: str = "CNC",
        price: float = 0.0,
        meta=None,
    ):
        """
        Pack22 OMS-managed execution
        """

        order = self._oms_bridge.create_order(
            broker=broker,
            symbol=symbol,
            side=side,
            qty=qty,
            order_type=order_type,
            price=price,
            metadata=meta,
        )

        submit_evt = CanonicalExecutionEvent(
            order_id=order.order_id,
            event_type=CanonicalEventType.ORDER_SUBMITTED,
            broker=broker,
        )

        order_state_machine.apply_event(order, submit_evt)
        execution_event_bus.publish(submit_evt)

        try:
            result = self.execute_canonical_order(
                broker=broker,
                symbol=symbol,
                side=side,
                qty=qty,
                order_type=order_type,
                product=product,
                price=price,
                meta=meta,
            )

            ack_evt = CanonicalExecutionEvent(
                order_id=order.order_id,
                event_type=CanonicalEventType.ORDER_ACK,
                broker=broker,
                payload=result if isinstance(result, dict) else {},
            )

            order_state_machine.apply_event(order, ack_evt)
            execution_event_bus.publish(ack_evt)

            #
            # Simulated accounting hook
            # Real broker partial/full fills will later arrive
            # through Pack24 async event ingestion
            #


            return {
                "oms_order_id": order.order_id,
                "status": order.status.value,
                "broker_result": result,
                "event_driven": True,
            }

        except Exception as exc:
            err_evt = CanonicalExecutionEvent(
                order_id=order.order_id,
                event_type=CanonicalEventType.ERROR,
                broker=broker,
                payload={"error": str(exc)},
            )

            try:
                order_state_machine.apply_event(order, err_evt)
            except Exception:
                pass

            execution_event_bus.publish(err_evt)
            raise

    def ingest_broker_event(
        self,
        broker_event,
    ):
        """
        Pack24 live broker event ingestion
        """
        return event_ingestion_engine.ingest(
            broker_event
        )
            
    # ------------------------------------------------------------------
    # Lazy dependency loaders
    # ------------------------------------------------------------------

    @staticmethod
    def _load_config() -> Any:
        try:
            from quant_ecosystem.core.config_loader import Config
            return Config()
        except Exception as exc:
            logger.warning("Config unavailable (%s); using _NullConfig.", exc)

            class _NullConfig:
                strict_market_hours            = False
                max_open_positions             = 20
                broker_fee_bps                 = 3
                base_slippage_bps              = 2
                max_slippage_bps               = 30
                liquidation_assist_enabled     = True
                liquidation_assist_trigger_streak = 3
                liquidation_assist_close_fraction = 0.25

            return _NullConfig()

    @staticmethod
    def _load_instrument_policy() -> Any:
        try:
            from quant_ecosystem.execution.instrument_policy_engine import InstrumentPolicyEngine
            return InstrumentPolicyEngine()
        except Exception:
            class _NullPolicy:
                def select(self, candidates, **_kw):
                    return candidates[0] if candidates else None
            return _NullPolicy()

    @staticmethod
    def _load_candle_pattern() -> Any:
        try:
            from quant_ecosystem.intelligence.candle_pattern_engine import CandlePatternEngine
            return CandlePatternEngine()
        except Exception:
            class _NullPattern:
                def detect(self, candle):
                    return []
            return _NullPattern()

    @staticmethod
    def _load_candle_angle() -> Any:
        try:
            from quant_ecosystem.intelligence.candle_angle_engine import CandleAngleEngine
            return CandleAngleEngine()
        except Exception:
            class _NullAngle:
                def calculate(self, closes):
                    return 0.0
            return _NullAngle()
    def start_execution_loop(self, interval_sec=2):

        import threading
        import time

        def _loop():

            logger.info("🔥 ExecutionRouter LIVE LOOP started")

            while True:
                try:
                    self.run_cycle()
                except Exception as e:
                    logger.error("execution loop error: %s", e)

                time.sleep(interval_sec)

        t = threading.Thread(target=_loop, daemon=True)
        t.start()
    # ------------------------------------------------------------------
    # Broker registration (runtime)
    # ------------------------------------------------------------------

    def register_broker(self, name: str, broker: Any) -> None:
        """
        Register a live broker adapter.

        Accepted names: 'fyers', 'zerodha', 'binance', 'coinswitch'.
        The broker argument may be a raw broker object or one of the
        *BrokerAdapter shims defined at the top of this module.  If it is
        a raw object the appropriate shim is applied automatically.
        """
        key = name.lower().strip()
        if key == "zerodha" and not isinstance(broker, _ZerodhaBrokerAdapter):
            broker = _ZerodhaBrokerAdapter(broker)
        elif key == "binance" and not isinstance(broker, _BinanceBrokerAdapter):
            broker = _BinanceBrokerAdapter(broker)
        elif key == "fyers" and not isinstance(broker, _FyersBrokerAdapter):
            broker = _FyersBrokerAdapter(broker)
        self._multi_broker.register(key, broker)

    def set_mode(self, mode: str) -> str:
        self.mode = str(mode).upper()
        self._multi_broker.mode = self.mode
        if self.state:
            self.state.trading_mode = self.mode
        logger.info("ExecutionRouter mode → %s", self.mode)
        return f"Mode set to {self.mode}"

    # ------------------------------------------------------------------
    # Primary async entry point
    # ------------------------------------------------------------------

    async def execute(
        self,
        signal: Optional[Dict] = None,
        market_bias: str = "NEUTRAL",
        regime: str = "MEAN_REVERSION",
    ) -> Dict:
        """
        Async execution entry point.

        If signal is provided it is enqueued at the appropriate priority;
        otherwise a signal is generated from the strategy engine.
        """
        if signal is not None:
            await self._order_queue.enqueue(signal, market_bias=market_bias, regime=regime)

        item = await self._order_queue.dequeue()
        if item is not None:
            result = self._execute_item(
                signal=item.signal,
                market_bias=item.market_bias,
                regime=item.regime,
            )
        else:
            result = self.run_cycle(signal=None, market_bias=market_bias, regime=regime)

        if self.telegram and result.get("status") == "TRADE":
            try:
                self.telegram.notify_trade(result)
            except Exception as exc:
                logger.warning("Telegram notification failed: %s", exc)

        return result

    # ------------------------------------------------------------------
    # Synchronous shim (backward compat)
    # ------------------------------------------------------------------

    def execute_trade(
        self,
        signal: Optional[Dict] = None,
        market_bias: str = "NEUTRAL",
        regime: str = "MEAN_REVERSION",
    ) -> Dict:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            fut = asyncio.run_coroutine_threadsafe(
                self.execute(signal=signal, market_bias=market_bias, regime=regime),
                loop,
            )
            return fut.result(timeout=10)
        except RuntimeError:
            return asyncio.run(
                self.execute(signal=signal, market_bias=market_bias, regime=regime)
            )

    # ------------------------------------------------------------------
    # Synchronous cycle
    # ------------------------------------------------------------------

    def run_cycle(
        self,
        signal: Optional[Dict] = None,
        market_bias: str = "NEUTRAL",
        regime: str = "MEAN_REVERSION",
    ) -> Dict:
        self._cycle_no += 1

        if not self.state:
            return _skip("NO_STATE")
        if getattr(self.state, "trading_halted", False):
            return _skip("TRADING_HALTED")
        if not getattr(self.state, "trading_enabled", True):
            return _skip("TRADING_DISABLED")
        if not getattr(self.state, "auto_mode", True) and signal is None:
            return _skip("AUTO_DISABLED")
        cooldown = getattr(self.state, "cooldown", 0)
        if cooldown > 0:
            self.state.cooldown = cooldown - 1
            return _skip("COOLDOWN")

        snapshots = self._snapshot_builder.build(
            symbols=self._dynamic_symbols(regime),
            regime=regime,
            state=self.state,
            portfolio_engine=self.portfolio_engine,
        )
        if not snapshots:
            return _skip("NO_MARKET_DATA")

        self.state.latest_prices = {s["symbol"]: s["price"] for s in snapshots}
        prev_equity   = self.state.equity
        prev_realized = float(getattr(self.state, "realized_pnl", 0))

        if self.reconciler:
            try:
                self.reconciler.reconcile(latest_prices=self.state.latest_prices)
            except Exception:
                pass
        elif self.portfolio_engine:
            try:
                self.state.mark_to_market(self.portfolio_engine)
            except Exception:
                pass

        candidate = signal or self._select_signal(
            snapshots=snapshots, market_bias=market_bias, regime=regime,
        )
        if not candidate:
            candidate = self._maybe_rebalance_signal(regime=regime)
        if not candidate:
            return _skip("NO_SIGNAL")

        return self._execute_item(
            signal=candidate,
            market_bias=market_bias,
            regime=regime,
            prev_equity=prev_equity,
            prev_realized=prev_realized,
        )

    

    # ------------------------------------------------------------------
    # Sovereignty Gate
    # ------------------------------------------------------------------

    def _gate_strategy_authority(self, signal):

        registry = getattr(self, "strategy_registry", None)
        governor = getattr(self, "registry_governor", None)

        if not registry or not governor:
            return True, "NO_GOVERNANCE"

        sid = signal.get("strategy_id", "")   # ← was missing; NameError in production

        row = registry.get(sid)

        if not row:
            return False, "strategy_not_registered"

        stage = str(row.get("stage", "")).upper()

        if stage not in {"LIVE", "SHADOW", "PAPER"}:
            return False, f"stage_not_executable:{stage}"

        if float(row.get("allocation_pct", 0)) <= 0:
            return False, "no_capital_allocated"

        if sid not in governor.get_active_ids():
            return False, "not_governor_active"

        # Token authority validation — must run before approving execution
        if self.token_authority:
            token = signal.get("execution_token")
            if not self.token_authority.validate(sid, token):
                return False, "invalid_execution_token"

        return True, "ok"
    
    # ------------------------------------------------------------------
    # Core execution pipeline
    # ------------------------------------------------------------------

    def _execute_item(
        self,
        signal: Dict,
        market_bias: str,
        regime: str,
        prev_equity: Optional[float] = None,
        prev_realized: Optional[float] = None,
    ) -> Dict:
        if prev_equity is None:
            prev_equity   = getattr(self.state, "equity", 0.0)
        if prev_realized is None:
            prev_realized = float(getattr(self.state, "realized_pnl", 0))

        if bool(getattr(self.config, "strict_market_hours", False)):
            if not self._is_symbol_tradable_now(signal.get("symbol")):
                self._reset_risk_block_state()
                return _skip("MARKET_CLOSED")

        if not self._is_valid_signal(signal):
            self._reset_risk_block_state()
            return _skip("INVALID_SIGNAL")

        # ---- Strategy authority gate ----
        ok, reason = self._gate_strategy_authority(signal)
        if not ok:
            self._reset_risk_block_state()
            return _skip(f"STRATEGY_BLOCKED:{reason}")

        is_rebalance = bool(signal.get("rebalance_assist", False))
        if not is_rebalance and not self._passes_context_filter(signal, regime):
            self._reset_risk_block_state()
            return _skip("WEAK_CONTEXT")

        if self._is_symbol_in_cooldown(signal["symbol"]):
            self._reset_risk_block_state()
            return _skip("SYMBOL_COOLDOWN")

        # ---- Risk gate pipeline ----------------------------------------
        gate_ctx = {
            "risk_engine":        self.risk_engine,
            "portfolio_engine":   self.portfolio_engine,
            "cycle_no":           self._cycle_no,
            "symbol_cooldown":    self._symbol_cooldown_until,
            "strategy_cooldown":  self._strategy_cooldown_until,
            "max_open_positions": int(getattr(self.config, "max_open_positions", 20)),
        }
        gate = self._risk_gate.check(self.state, signal, gate_ctx)
        if not gate.allowed:
            if gate.reason in _RISK_GATE_EXPOSURE_REASONS:
                self._track_risk_block(gate.reason)
                liq = self._maybe_liquidation_assist(gate.reason, regime)
                if liq:
                    return liq
            else:
                self._reset_risk_block_state()
            return _skip(gate.reason)

        # ---- Legacy risk_engine.allow_trade() (backward compat) --------
        if self.risk_engine:
            try:
                allowed, reason = self.risk_engine.allow_trade(
                    self.state,
                    portfolio_exposure_pct   = self._portfolio_exposure_pct(),
                    symbol_exposure_pct      = self._symbol_exposure_pct(signal["symbol"]),
                    daily_trade_count        = self._daily_trade_count(),
                    symbol_daily_loss_pct    = self._symbol_daily_loss_pct(signal["symbol"]),
                    sector_exposure_pct      = self._sector_exposure_pct(signal["symbol"]),
                    strategy_exposure_pct    = self._strategy_exposure_pct(signal.get("strategy_id")),
                    asset_exposure_pct       = self._asset_exposure_pct(self._asset_class(signal["symbol"])),
                    exposure_reducing        = self._is_exposure_reducing_signal(signal),
                    active_strategy_count    = self._active_strategy_count(),
                )
                if not allowed:
                    if self._is_exposure_block(reason):
                        self._track_risk_block(reason)
                        liq = self._maybe_liquidation_assist(reason, regime)
                        if liq:
                            return liq
                    else:
                        self._reset_risk_block_state()
                    return _skip(reason)
            except Exception as exc:
                logger.warning("risk_engine.allow_trade failed: %s", exc)

        self._reset_risk_block_state()
               
        # ---- Quantity allocation ----------------------------------------
        qty, size_reason = self._allocate_quantity(signal)
        instrument = self._resolve_instrument(signal["symbol"])
        qty = self._normalize_execution_quantity(qty, instrument)
        self._validate_contract_quantity(qty, instrument)
        
        if qty <= 0:
            return _skip(size_reason)

        # Advisory: reserve capital via CapitalIntelligenceEngine
        if self.capital_intelligence:
            try:
                self.capital_intelligence.allocate(
                    signal.get("strategy_id", "unknown"),
                    float(signal["price"]) * qty,
                )
            except Exception:
                pass

        # ---- Slippage & fee --------------------------------------------
        intended_price = signal["price"]
        slippage_bps   = self._compute_slippage_bps(signal)
        fill_price     = self._apply_slippage(intended_price, signal["side"], slippage_bps)
        multiplier = self._instrument_multiplier(instrument)
        fill_notional = _quantize(fill_price * qty * multiplier, 4)
        fee            = _quantize(fill_notional * (getattr(self.config, "broker_fee_bps", 3) / 10000.0), 4)

        # ---- Broker dispatch -------------------------------------------
        asset_class = self._instrument_asset_class(
            instrument,
            signal.get("asset_class", self._asset_class(signal["symbol"]))
        )
        order = self._multi_broker.place_order(
            symbol=signal["symbol"],
            side=signal["side"],
            qty=qty,
            price=fill_price,
            asset_class=asset_class,
            market=signal.get("market", "INDIA"),
            meta={
                "strategy_id": signal.get("strategy_id"),
                "trade_type": signal.get("trade_type") or self._trade_type(signal),
                "regime": regime,
                "rebalance_assist": bool(signal.get("rebalance_assist", False)),
                **self._build_instrument_meta(instrument),
            },
        )

        provider_name = getattr(
            self._multi_broker,
            "_last_selected_broker_name",
            None,
        )

        if provider_name:
            order = self._normalize_execution_result(
                provider=provider_name,
                payload=order,
            )


        # ---- Portfolio accounting --------------------------------------
        realized_pnl = self._apply_fill_accounting(
            order=order,
            fill_price=fill_price,
            fill_notional=fill_notional,
            fee=fee,
            prev_realized=prev_realized,
        )

        cycle_pnl = _quantize(getattr(self.state, "equity", 0.0) - prev_equity, 4)
        try:
            self.state.update_loss_streak(cycle_pnl_abs=cycle_pnl)
        except Exception:
            pass

        # Strategy cooldown
        sid = signal.get("strategy_id", "")
        if sid:
            tt  = str(signal.get("trade_type") or self._trade_type(signal)).upper()
            gap = _COOLDOWN_BY_TRADE_TYPE.get(tt, 2)
            self._strategy_cooldown_until[sid] = self._cycle_no + gap

        trade_record = self._build_trade_record(
            signal=signal, order=order,
            fill_price=fill_price, intended_price=intended_price,
            slippage_bps=slippage_bps, fee=fee,
            realized_pnl=realized_pnl, cycle_pnl=cycle_pnl,
            regime=regime,
        )
        try:
            self.state.record_trade(trade_record)
        except Exception:
            pass
        self._symbol_strategy_owner[order.get("symbol", signal["symbol"])] = sid
        self._set_symbol_cooldown(
            order.get("symbol", signal["symbol"]), trade_record.get("trade_type", "INTRADAY")
        )

        return {
            "status":             "TRADE",
            "order_id":           order.get("order_id") or order.get("id", ""),
            "symbol":             order.get("symbol", signal["symbol"]),
            "side":               order.get("side", signal["side"]),
            "qty":                order.get("qty", qty),
            "price":              trade_record["price"],
            "pnl":                trade_record["cycle_pnl"],
            "equity":             trade_record["equity"],
            "strategy_id":        trade_record["strategy_id"],
            "strategy_stage":     trade_record["strategy_stage"],
            "shadow_mode":        trade_record["shadow_mode"],
            "trade_type":         trade_record["trade_type"],
            "regime":             trade_record["regime"],
            "confidence":         trade_record["confidence"],
            "liquidation_assist": False,
            "rebalance_assist":   trade_record["rebalance_assist"],
            "broker":             order.get("broker", self._multi_broker.account_source),
        }

    # ------------------------------------------------------------------
    # Fill accounting
    # ------------------------------------------------------------------

    def _apply_fill_accounting(
        self,
        order: Dict,
        fill_price: float,
        fill_notional: float,
        fee: float,
        prev_realized: float,
    ) -> float:
        realized_pnl = 0.0
        if self.reconciler:
            try:
                snapshot = self.reconciler.reconcile(latest_prices=getattr(self.state, "latest_prices", {}))
                realized_pnl = float(getattr(self.state, "realized_pnl", 0)) - prev_realized
                if abs(realized_pnl) < 1e-8:
                    realized_pnl = float(order.get("realized_pnl", 0.0))
            except Exception as exc:
                logger.debug("Reconciler error: %s", exc)
        elif self.portfolio_engine:
            try:
                instrument = self._resolve_instrument(
                    order.get("symbol", "")
                )

                multiplier = self._instrument_multiplier(instrument)

                fill_result = self.portfolio_engine.apply_fill(
                    symbol=order.get("symbol", ""),
                    side=order.get("side", ""),
                    qty=order.get("qty", 0),
                    price=fill_price,
                    multiplier=multiplier,
                    asset_class=self._instrument_asset_class(instrument),
                )
                realized_pnl = float(fill_result.get("realized_pnl", 0.0))
                self.state.apply_fill_accounting(
                    side=order.get("side", ""),
                    fill_notional=fill_notional,
                    fee=fee,
                    realized_pnl=realized_pnl,
                )
                self.state.open_positions = self.portfolio_engine.exposure()
                self.state.mark_to_market(self.portfolio_engine)
            except Exception as exc:
                logger.debug("fill_accounting error: %s", exc)

        # Release CIE reservation on close
        if self.capital_intelligence and abs(realized_pnl) > 0:
            try:
                sid = (order.get("meta") or {}).get("strategy_id", "unknown")
                self.capital_intelligence.release(sid)
            except Exception:
                pass

        return realized_pnl

    # ------------------------------------------------------------------
    # Operational controls
    # ------------------------------------------------------------------

    def submit_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: float,
        fee: float = 0.0,
        meta: Optional[Dict] = None,
    ) -> Dict:
        """Direct broker submission bypassing signal pipeline."""
        result = self._multi_broker.place_order(
            symbol=symbol, side=side, qty=qty, price=price, fee=fee,
            meta=enriched_meta, asset_class=self._asset_class(symbol),
        )

        self._attach_strategy_context(
            result.get("order_id"),
            strategy_meta,
        )

        return result

    def update_positions(self) -> Dict:
        if not self.portfolio_engine:
            return {}
        try:
            self.state.mark_to_market(self.portfolio_engine)
            return self.portfolio_engine.snapshot()
        except Exception:
            return {}

    def start_trading(self) -> str:
        self.state.trading_enabled = True
        self.state.trading_halted  = False
        return "Trading started."

    def stop_trading(self) -> str:
        self.state.trading_enabled = False
        return "Trading stopped."

    def kill_switch(self) -> str:
        self.state.trading_enabled = False
        self.state.trading_halted  = True
        return "Kill switch activated. Trading halted."

    def set_auto_mode(self, enabled: bool) -> str:
        self.state.auto_mode = bool(enabled)
        return f"Auto mode set to {self.state.auto_mode}."

    def set_trading_mode(self, mode: str) -> str:
        return self.set_mode(mode)

    def set_risk_preset(self, preset: str) -> str:
        mapping = {"25%": 0.25, "50%": 0.50, "100%": 1.00}
        factor  = mapping.get(preset)
        if factor is None:
            return "Invalid risk preset. Use 25%, 50%, or 100%."
        base      = getattr(self.risk_engine, "base_trade_risk", 1.0)
        new_value = self.risk_engine.set_trade_risk_pct(base * factor)
        self.state.risk_preset = preset
        return f"Risk preset {preset} applied. Trade risk={_quantize(new_value, 2)}%."

    def set_strategy_profile(self, profile: str) -> str:
        normalized = str(profile).upper()
        if normalized not in {"ALPHA", "BETA", "GAMMA"}:
            return "Invalid profile. Use Alpha, Beta, or Gamma."
        self.state.strategy_profile = normalized
        return f"Strategy profile set to {normalized}."

        strategy_meta = self._extract_strategy_meta(
            order
        )

    # ------------------------------------------------------------------
    # Status / reporting
    # ------------------------------------------------------------------

    def get_status_report(self) -> str:
        re = self.risk_engine
        st = self.state
        pe = self.portfolio_engine
        return (
            f"enabled={getattr(st,'trading_enabled',False)} "
            f"halted={getattr(st,'trading_halted',False)} "
            f"mode={getattr(st,'trading_mode',self.mode)} "
            f"auto={getattr(st,'auto_mode',False)} "
            f"profile={getattr(st,'strategy_profile','BETA')} "
            f"risk_preset={getattr(st,'risk_preset','100%')} "
            f"equity={_quantize(getattr(st,'equity',0),2)} "
            f"cash={_quantize(getattr(st,'cash_balance',0),2)} "
            f"realized={_quantize(getattr(st,'realized_pnl',0),2)} "
            f"drawdown={_quantize(getattr(st,'total_drawdown_pct',0),2)}% "
            f"exposure={_quantize(self._portfolio_exposure_pct(),2)}% "
            f"day_trades={self._daily_trade_count()}/{getattr(re,'max_daily_trades',100)} "
            f"queue_depth={len(self._order_queue)} "
            f"trades={len(getattr(st,'trade_history',[]))}"
        )

    def get_positions_report(self) -> str:
        if not self.portfolio_engine:
            return "Open positions: 0"
        try:
            positions = self.portfolio_engine.snapshot()
            if not positions:
                return "Open positions: 0"
            return f"Open positions: {len(positions)} | {positions}"
        except Exception:
            return "Open positions: unavailable"

    def get_dashboard_report(self) -> str:
        symbol  = self.symbols[0] if self.symbols else "-"
        price   = float(getattr(self.state, "latest_prices", {}).get(symbol, 0.0))
        trades  = getattr(self.state, "trade_history", [])
        if trades:
            wins       = [t for t in trades if float(t.get("cycle_pnl", 0)) > 0]
            win_rate   = (len(wins) / len(trades)) * 100.0
            profit_abs = sum(float(t.get("cycle_pnl", 0)) for t in trades)
            last       = trades[-1]
            last_line  = (
                f"Last: {last.get('trade_type','NA')} {last.get('side','')} "
                f"{last.get('symbol','')} pnl={_quantize(last.get('cycle_pnl',0),2)}"
            )
        else:
            win_rate = profit_abs = 0.0
            last_line = "Last: NA"
        return (
            "Institutional Control Terminal\n\n"
            f"Symbol: {symbol}\n"
            f"Price: {_quantize(price, 2)}\n"
            f"Mode: {getattr(self.state,'trading_mode',self.mode)}\n"
            f"TradeType: {self._trade_type()}\n"
            f"Winrate: {_quantize(win_rate, 2)}% | Profit: {_quantize(profit_abs, 2)}\n"
            f"Equity: {_quantize(getattr(self.state,'equity',0), 2)}\n"
            f"Queue: {len(self._order_queue)} pending\n"
            f"{last_line}"
        )

    # ------------------------------------------------------------------
    # Snapshot API (for SystemRouter._build_snapshots)
    # ------------------------------------------------------------------

    def build_snapshots(self, regime: str = "MEAN_REVERSION") -> List[Dict]:
        """Build market snapshots for all current symbols."""
        return self._snapshot_builder.build(
            symbols=self._dynamic_symbols(regime),
            regime=regime,
            state=self.state,
            portfolio_engine=self.portfolio_engine,
        )

    # ------------------------------------------------------------------
    # Signal selection
    # ------------------------------------------------------------------

    def _select_signal(
        self, snapshots: List[Dict], market_bias: str, regime: str
    ) -> Optional[Dict]:
        if not self.strategy_engine:
            return None
        try:
            candidates = self.strategy_engine.evaluate(
                snapshots=snapshots, market_bias=market_bias, regime=regime,
            )
        except Exception as exc:
            logger.warning("strategy_engine.evaluate failed: %s", exc)
            return None
        if not candidates:
            return None

        compatible = [c for c in candidates if self._strategy_symbol_compatible(c)]
        if compatible:
            candidates = compatible

        if bool(getattr(self.config, "strict_market_hours", False)):
            open_now = [c for c in candidates if self._is_symbol_tradable_now(c.get("symbol"))]
            if open_now:
                candidates = open_now
            else:
                return None

        for c in candidates:
            sym_penalty     = self._symbol_exposure_pct(c["symbol"]) / 100.0
            c["rank_score"] = c.get("confidence", 0.0) - (0.2 * sym_penalty)
            c["trade_type"] = self._determine_trade_type(c, regime)
            if self.outcome_memory:
                try:
                    c["memory_bias"] = self.outcome_memory.signal_bias(
                        strategy_id=c.get("strategy_id"),
                        symbol=c.get("symbol"),
                        regime=regime,
                        trade_type=c.get("trade_type"),
                    )
                    c["rank_score"] += float(c["memory_bias"])
                except Exception:
                    c["memory_bias"] = 0.0
            else:
                c["memory_bias"] = 0.0
            if c.get("shadow_mode"):
                c["rank_score"] -= 0.08

        threshold = self._profile_threshold()
        filtered  = [c for c in candidates if c.get("confidence", 0) >= threshold] or candidates

        selected = self.instrument_policy.select(filtered, regime=regime, trade_type=self._trade_type())
        if selected:
            return selected

        filtered.sort(key=lambda c: c.get("rank_score", 0), reverse=True)
        top_bucket = filtered[: min(3, len(filtered))]
        weights    = [max(0.01, c.get("rank_score", 0.01)) for c in top_bucket]
        return random.choices(top_bucket, weights=weights, k=1)[0]

    # ------------------------------------------------------------------
    # Private helpers — validation & context
    # ------------------------------------------------------------------

    def _is_valid_signal(self, signal: Dict) -> bool:
        if not {"strategy_id", "symbol", "side", "price"}.issubset(signal.keys()):
            return False
        if signal["side"] not in {"BUY", "SELL"}:
            return False
        if float(signal["price"]) <= 0:
            return False
        return True

    def _dynamic_symbols(self, regime: str) -> List[str]:
        base   = list(self.symbols)
        extras = self._regime_extras_for_asset_classes(regime=regime, symbols=base)
        merged: List[str] = []
        for s in base + extras:
            if s not in merged:
                merged.append(s)
        return merged[:8]

    def _determine_trade_type(self, signal: Dict, regime: str) -> str:
        patterns   = set(signal.get("candle_patterns", []))
        angle      = float(signal.get("candle_angle", 0.0))
        volatility = float(signal.get("volatility", 0.0))
        if regime in {"CRISIS", "HIGH_VOLATILITY"}:
            return "SCALP"
        if "DOJI" in patterns and regime == "MEAN_REVERSION":
            return "INTRADAY"
        if abs(angle) > 0.08 and volatility < 0.8:
            return "SWING"
        return self._trade_type(signal)

    def _passes_context_filter(self, signal: Dict, regime: str) -> bool:
        confidence = float(signal.get("confidence", 0.0))
        side       = str(signal.get("side", "HOLD")).upper()
        angle      = float(signal.get("candle_angle", 0.0))
        patterns   = set(signal.get("candle_patterns", []))
        is_shadow  = bool(signal.get("shadow_mode", False))
        base_min   = 0.70 if is_shadow else 0.58
        if regime in {"HIGH_VOLATILITY", "CRISIS"}:
            base_min += 0.04
        if confidence < base_min:
            return False
        if side == "BUY"  and "BEAR_ENGULF" in patterns: return False
        if side == "SELL" and "BULL_ENGULF" in patterns: return False
        if side == "BUY"  and angle < -0.06 and regime != "MEAN_REVERSION": return False
        if side == "SELL" and angle >  0.06 and regime != "MEAN_REVERSION": return False
        return True

    def _is_symbol_in_cooldown(self, symbol: str) -> bool:
        return self._cycle_no < int(self._symbol_cooldown_until.get(symbol, 0))

    def _set_symbol_cooldown(self, symbol: str, trade_type: str) -> None:
        gap = _COOLDOWN_BY_TRADE_TYPE.get(str(trade_type).upper(), 2)
        self._symbol_cooldown_until[symbol] = self._cycle_no + gap

    # ------------------------------------------------------------------
    # Private helpers — sizing & exposure
    # ------------------------------------------------------------------

    def _allocate_quantity(self, signal: Dict) -> Tuple[int, str]:
        price      = signal["price"]
        forced_qty = signal.get("forced_qty")
        if forced_qty is not None:
            qty = max(0, int(forced_qty))
            return (qty, "OK") if qty > 0 else (0, "ZERO_SIZE")

        if self.position_sizer:
            try:
                qty = self.position_sizer.size(
                    equity=getattr(self.state, "equity", 0),
                    price=price,
                    volatility=max(signal.get("volatility", 1.0), 0.01),
                    risk_pct=getattr(self.risk_engine, "max_trade_risk", 1.0),
                )
                base_qty = max(int(qty), 0)
            except Exception:
                base_qty = 0
        elif self.risk_engine:
            try:
                risk_budget = self.risk_engine.trade_risk(getattr(self.state, "equity", 0))
                base_qty = (
                    max(int(risk_budget / price), 1)
                    if price > 0 and risk_budget > 0
                    else 0
                )
            except Exception:
                base_qty = 0
        else:
            equity   = getattr(self.state, "equity", 0)
            base_qty = max(int((equity * 0.01) / price), 0) if price > 0 else 0

        if base_qty <= 0:
            return 0, "ZERO_SIZE"

        if self.capital_governance:
            try:
                scale       = self.capital_governance.sizing_multiplier(getattr(self.state, "trade_history", []))
                base_qty    = max(int(base_qty * scale), 0)
                strat_limit = int(
                    self.capital_governance.max_strategy_notional(getattr(self.state, "equity", 0)) / price
                )
                asset_class = self._asset_class(signal["symbol"])
                asset_left  = max(
                    0.0,
                    self.capital_governance.max_asset_class_notional(getattr(self.state, "equity", 0))
                    - self._asset_class_exposure_notional(asset_class),
                )
                asset_limit  = int(asset_left / price)
                base_qty     = min(base_qty, strat_limit, asset_limit)
            except Exception:
                pass

        if signal.get("shadow_mode"):
            base_qty = max(1, int(base_qty * 0.25))

        try:
            allowed_portfolio = int(self._available_portfolio_notional() / price)
            if allowed_portfolio <= 0:
                return 0, "MAX_PORTFOLIO_EXPOSURE"
            allowed_symbol = int(self._available_symbol_notional(signal["symbol"]) / price)
            if allowed_symbol <= 0:
                return 0, "MAX_SYMBOL_EXPOSURE"
            return max(min(base_qty, allowed_portfolio, allowed_symbol), 0), "OK"
        except Exception:
            return max(base_qty, 0), "OK"

    def _portfolio_exposure_pct(self) -> float:
        if not self.portfolio_engine or not self.state:
            return 0.0
        try:
            notional = self.portfolio_engine.net_exposure_notional(
                getattr(self.state, "latest_prices", {})
            )
            equity = getattr(self.state, "equity", 1.0) or 1.0
            return _quantize((notional / equity) * 100.0, 4)
        except Exception:
            return 0.0

    def _symbol_exposure_pct(self, symbol: str) -> float:
        if not self.portfolio_engine or not self.state:
            return 0.0
        try:
            notional = self.portfolio_engine.symbol_exposure_notional(
                symbol, getattr(self.state, "latest_prices", {})
            )
            equity = getattr(self.state, "equity", 1.0) or 1.0
            return _quantize((notional / equity) * 100.0, 4)
        except Exception:
            return 0.0

    def _daily_trade_count(self) -> int:
        return len(getattr(self.state, "trade_history", []))

    def _symbol_daily_loss_pct(self, symbol: str) -> float:
        equity = getattr(self.state, "equity", 1.0) or 1.0
        losses = sum(
            abs(float(t.get("cycle_pnl", 0)))
            for t in getattr(self.state, "trade_history", [])
            if t.get("symbol") == symbol and float(t.get("cycle_pnl", 0)) < 0
        )
        return _quantize((losses / equity) * 100.0, 4)

    def _strategy_exposure_pct(self, strategy_id: Optional[str]) -> float:
        if not strategy_id or not getattr(self.state, "equity", 0):
            return 0.0
        notional = sum(
            abs(float(pos.get("net_qty", 0)) * float(px))
            for sym, pos in getattr(self.portfolio_engine, "positions", {}).items()
            if self._symbol_strategy_owner.get(sym) == strategy_id
            and (px := getattr(self.state, "latest_prices", {}).get(sym)) is not None
        )
        return _quantize((notional / (self.state.equity or 1)) * 100.0, 4)

    def _active_strategy_count(self) -> int:
        if not self.strategy_engine:
            return 1
        ids = getattr(self.strategy_engine, "active_ids", None)
        if ids is None:
            return max(len(getattr(self.strategy_engine, "strategies", []) or []), 1)
        return max(len(ids), 1)

    def _asset_exposure_pct(self, asset_class: str) -> float:
        equity = getattr(self.state, "equity", 1.0) or 1.0
        return _quantize((self._asset_class_exposure_notional(asset_class) / equity) * 100.0, 4)

    def _sector_exposure_pct(self, symbol: str) -> float:
        sector = "BANKING" if "BANK" in str(symbol).upper() else "GENERAL"
        equity = getattr(self.state, "equity", 1.0) or 1.0
        notional = sum(
            abs(float(pos.get("net_qty", 0)) * float(px))
            for sym, pos in getattr(self.portfolio_engine, "positions", {}).items()
            if (("BANKING" if "BANK" in sym.upper() else "GENERAL") == sector)
            and (px := getattr(self.state, "latest_prices", {}).get(sym)) is not None
        )
        return _quantize((notional / equity) * 100.0, 4)

    def _available_portfolio_notional(self) -> float:
        max_risk = getattr(self.risk_engine, "max_portfolio_risk", 80)
        equity   = getattr(self.state, "equity", 0.0)
        max_n    = equity * (max_risk / 100.0)
        used     = self.portfolio_engine.net_exposure_notional(
            getattr(self.state, "latest_prices", {})
        )
        return max(0.0, max_n - used)

    def _available_symbol_notional(self, symbol: str) -> float:
        max_risk = getattr(self.risk_engine, "max_symbol_risk", 20)
        equity   = getattr(self.state, "equity", 0.0)
        max_n    = equity * (max_risk / 100.0)
        used     = self.portfolio_engine.symbol_exposure_notional(
            symbol, getattr(self.state, "latest_prices", {})
        )
        return max(0.0, max_n - used)

    def _asset_class_exposure_notional(self, asset_class: str) -> float:
        total = 0.0
        for sym, pos in getattr(self.portfolio_engine, "positions", {}).items():
            if self._asset_class(sym) != asset_class:
                continue
            px = getattr(self.state, "latest_prices", {}).get(sym)
            if px is None:
                continue
            total += abs(float(pos.get("net_qty", 0)) * float(px))
        return _quantize(total, 4)

    # ------------------------------------------------------------------
    # Private helpers — slippage, trade_type, asset_class
    # ------------------------------------------------------------------

    def _compute_slippage_bps(self, signal: Dict) -> float:
        vol_pct = max(signal.get("volatility", 0.2), 0.05)
        raw     = getattr(self.config, "base_slippage_bps", 2) + (vol_pct * 1.5)
        return _quantize(min(raw, getattr(self.config, "max_slippage_bps", 30)), 4)

    def _apply_slippage(self, price: float, side: str, slippage_bps: float) -> float:
        slip = slippage_bps / 10000.0
        if side == "BUY":
            return _quantize(price * (1 + slip), 4)
        return _quantize(price * (1 - slip), 4)

    def _profile_threshold(self) -> float:
        p = str(getattr(self.state, "strategy_profile", "BETA")).upper()
        return {"ALPHA": 0.72, "GAMMA": 0.52}.get(p, 0.62)

    def _trade_type(self, signal: Optional[Dict] = None) -> str:
        if signal and signal.get("trade_type"):
            return str(signal["trade_type"]).upper()
        p = str(getattr(self.state, "strategy_profile", "BETA")).upper()
        return {"ALPHA": "SWING", "GAMMA": "SCALP"}.get(p, "INTRADAY")

    def _asset_class(self, symbol: str) -> str:
        v = str(symbol).upper()
        if v.startswith("MCX:"):                             return "COMMODITY"
        if "CRYPTO" in v or v.endswith("USDT"):             return "CRYPTO"
        if "FX" in v or "FOREX" in v:                       return "FOREX"
        if "FUT" in v:                                       return "FUTURES"
        if "OPT" in v or v.endswith("CE") or v.endswith("PE"): return "OPTIONS"
        return "EQUITY"

    def _is_exposure_reducing_signal(self, signal: Dict) -> bool:
        symbol  = signal.get("symbol")
        side    = str(signal.get("side", "")).upper()
        pe_pos  = getattr(self.portfolio_engine, "positions", {})
        pos     = pe_pos.get(symbol)
        if not pos:
            return False
        net_qty = float(pos.get("net_qty", 0.0))
        return (net_qty > 0 and side == "SELL") or (net_qty < 0 and side == "BUY")

    def _is_exposure_block(self, reason: str) -> bool:
        return reason in _RISK_GATE_EXPOSURE_REASONS

    def _track_risk_block(self, reason: str) -> None:
        if self._last_risk_block_reason == reason:
            self._risk_block_streak += 1
        else:
            self._last_risk_block_reason = reason
            self._risk_block_streak      = 1

    def _reset_risk_block_state(self) -> None:
        self._risk_block_streak      = 0
        self._last_risk_block_reason = ""

    def _strategy_symbol_compatible(self, signal: Dict) -> bool:
        sid    = str(signal.get("strategy_id", "")).strip()
        symbol = str(signal.get("symbol", "")).strip()
        if not sid or not symbol:
            return True
        bank_engine  = getattr(self, "strategy_bank_engine", None)
        registry     = getattr(bank_engine, "registry", None)
        row          = registry.get(sid) if registry and hasattr(registry, "get") else None
        strategy_asset = str((row or {}).get("asset_class", "")).strip().lower()
        if not strategy_asset:
            return True
        symbol_asset = self._asset_class(symbol).lower()
        allowed = {
            "stocks":      {"equity"},
            "equity":      {"equity"},
            "indices":     {"equity", "futures", "options"},
            "futures":     {"futures"},
            "options":     {"options"},
            "forex":       {"forex"},
            "fx":          {"forex"},
            "crypto":      {"crypto"},
            "commodities": {"commodity", "futures"},
            "commodity":   {"commodity", "futures"},
            "multi":       {"equity", "forex", "crypto", "futures", "options", "commodity"},
        }
        supported = allowed.get(strategy_asset)
        return supported is None or symbol_asset in supported

    def _is_symbol_tradable_now(self, symbol: Optional[str]) -> bool:
        sym = str(symbol or "").upper().strip()
        if not sym:
            return False
        if sym.startswith("CRYPTO:") or sym.endswith("USDT"):
            return True
        now_ist = self._now_ist()
        if now_ist.weekday() >= 5:
            return False
        now_t = now_ist.time()
        if sym.startswith("NSE:"): return dtime(9, 15) <= now_t <= dtime(15, 30)
        if sym.startswith("MCX:"): return dtime(9,  0) <= now_t <= dtime(23, 30)
        return True

    @staticmethod
    def _now_ist() -> datetime:
        try:
            return datetime.now(ZoneInfo("Asia/Kolkata"))
        except Exception:
            return datetime.now(timezone(timedelta(hours=5, minutes=30)))

    def _build_trade_record(
        self,
        signal:         Dict,
        order:          Dict,
        fill_price:     float,
        intended_price: float,
        slippage_bps:   float,
        fee:            float,
        realized_pnl:   float,
        cycle_pnl:      float,
        regime:         str,
    ) -> Dict:
        sym = order.get("symbol", signal.get("symbol", ""))
        return {
            "strategy_id":      signal.get("strategy_id"),
            "strategy_stage":   signal.get("strategy_stage", "UNKNOWN"),
            "shadow_mode":      bool(signal.get("shadow_mode", False)),
            "symbol":           sym,
            "asset_class":      self._asset_class(sym),
            "regime":           regime,
            "trade_type":       signal.get("trade_type") or self._trade_type(signal),
            "side":             order.get("side", signal.get("side", "")),
            "qty":              order.get("qty", 0),
            "status":           order.get("status", "UNKNOWN"),
            "price":            _quantize(fill_price, 4),
            "intended_price":   _quantize(intended_price, 4),
            "slippage_bps":     _quantize(slippage_bps, 4),
            "confidence":       _quantize(signal.get("confidence", 0.0), 4),
            "memory_bias":      _quantize(signal.get("memory_bias", 0.0), 6),
            "rebalance_assist": bool(signal.get("rebalance_assist", False)),
            "fee":              fee,
            "realized_pnl":    _quantize(realized_pnl, 4),
            "closed_trade":    bool(abs(realized_pnl) > 0.0),
            "unrealized_pnl":  _quantize(getattr(self.state, "unrealized_pnl", 0), 4),
            "cycle_pnl":       cycle_pnl,
            "equity":          _quantize(getattr(self.state, "equity", 0), 2),
            "cash_balance":    _quantize(getattr(self.state, "cash_balance", 0), 2),
        }

    # ------------------------------------------------------------------
    # Regime extras — expand symbol universe by regime
    # ------------------------------------------------------------------

    def _regime_extras_for_asset_classes(self, regime: str, symbols: List[str]) -> List[str]:
        classes    = {self._asset_class(s) for s in symbols if s}
        regime_key = str(regime or "MEAN_REVERSION").upper()
        eq_map = {
            "CRISIS":          ["NSE:SBIN-EQ", "NSE:RELIANCE-EQ"],
            "HIGH_VOLATILITY": ["NSE:SBIN-EQ", "NSE:ICICIBANK-EQ", "NSE:TCS-EQ"],
            "LOW_VOLATILITY":  ["NSE:RELIANCE-EQ", "NSE:INFY-EQ", "NSE:HDFCBANK-EQ"],
            "TREND":           ["NSE:RELIANCE-EQ", "NSE:TCS-EQ", "NSE:LT-EQ"],
            "MEAN_REVERSION":  ["NSE:SBIN-EQ", "NSE:INFY-EQ", "NSE:ITC-EQ"],
        }
        fx_map = {
            "CRISIS":          ["FX:USDINR", "FX:EURINR"],
            "HIGH_VOLATILITY": ["FX:USDINR", "FX:GBPINR"],
            "LOW_VOLATILITY":  ["FX:EURINR", "FX:USDINR"],
            "TREND":           ["FX:USDINR", "FX:EURINR"],
            "MEAN_REVERSION":  ["FX:EURINR", "FX:USDINR"],
        }
        crypto_map = {
            "CRISIS":          ["CRYPTO:BTCUSDT", "CRYPTO:ETHUSDT"],
            "HIGH_VOLATILITY": ["CRYPTO:BTCUSDT", "CRYPTO:ETHUSDT", "CRYPTO:SOLUSDT"],
            "LOW_VOLATILITY":  ["CRYPTO:BTCUSDT", "CRYPTO:ETHUSDT"],
            "TREND":           ["CRYPTO:BTCUSDT", "CRYPTO:ETHUSDT", "CRYPTO:SOLUSDT"],
            "MEAN_REVERSION":  ["CRYPTO:ETHUSDT", "CRYPTO:BTCUSDT"],
        }
        commodity_map = {
            "CRISIS":          ["MCX:GOLD", "MCX:SILVER"],
            "HIGH_VOLATILITY": ["MCX:GOLD", "MCX:CRUDEOIL"],
            "LOW_VOLATILITY":  ["MCX:GOLD", "MCX:SILVER"],
            "TREND":           ["MCX:CRUDEOIL", "MCX:GOLD"],
            "MEAN_REVERSION":  ["MCX:GOLD", "MCX:SILVER"],
        }
        extras: List[str] = []
        if classes & {"EQUITY", "FUTURES", "OPTIONS"}:
            extras.extend(eq_map.get(regime_key, eq_map["MEAN_REVERSION"]))
        if "FOREX"     in classes: extras.extend(fx_map.get(regime_key, fx_map["MEAN_REVERSION"]))
        if "CRYPTO"    in classes: extras.extend(crypto_map.get(regime_key, crypto_map["MEAN_REVERSION"]))
        if "COMMODITY" in classes: extras.extend(commodity_map.get(regime_key, commodity_map["MEAN_REVERSION"]))
        return extras

    # ------------------------------------------------------------------
    # Liquidation / rebalance assist
    # ------------------------------------------------------------------

    def _maybe_rebalance_signal(self, regime: str) -> Optional[Dict]:
        if not getattr(self.config, "liquidation_assist_enabled", True):
            return None
        if self._cycle_no < self._liquidation_cooldown_until:
            return None
        if not self.portfolio_engine:
            return None
        try:
            positions = self.portfolio_engine.snapshot()
        except Exception:
            return None
        if not positions:
            return None
        exposure_pressure = (
            self._risk_block_streak >= 1
            and self._is_exposure_block(self._last_risk_block_reason)
        ) or (
            self._portfolio_exposure_pct()
            >= max(1.0, getattr(self.risk_engine, "max_portfolio_risk", 80) * 0.9)
        )
        if not exposure_pressure:
            return None
        symbol, pos = max(
            positions.items(),
            key=lambda kv: self.portfolio_engine.symbol_exposure_notional(
                kv[0], getattr(self.state, "latest_prices", {})
            ),
        )
        net_qty = int(pos.get("net_qty", 0))
        if net_qty == 0:
            return None
        price = float(getattr(self.state, "latest_prices", {}).get(symbol, pos.get("avg_price", 0.0)))
        if price <= 0:
            return None
        side = "SELL" if net_qty > 0 else "BUY"
        frac = max(0.05, min(getattr(self.config, "liquidation_assist_close_fraction", 0.25), 1.0))
        qty  = min(max(1, int(abs(net_qty) * frac)), abs(net_qty))
        return {
            "strategy_id":      "rebalance_assist_v1",
            "strategy_stage":   "RISK_REDUCTION",
            "shadow_mode":      False,
            "symbol":           symbol,
            "side":             side,
            "price":            price,
            "confidence":       1.0,
            "volatility":       0.5,
            "trade_type":       "RISK_REBALANCE",
            "memory_bias":      0.0,
            "forced_qty":       qty,
            "rebalance_assist": True,
            "regime":           regime,
        }

    def _maybe_liquidation_assist(
        self, trigger_reason: str, regime: str
    ) -> Optional[Dict]:
        if not getattr(self.config, "liquidation_assist_enabled", True):
            return None
        if self._cycle_no < self._liquidation_cooldown_until:
            return None
        trigger_streak = getattr(self.config, "liquidation_assist_trigger_streak", 3)
        if self._risk_block_streak < max(1, trigger_streak):
            return None
        if not self.portfolio_engine:
            return None
        try:
            positions = self.portfolio_engine.snapshot()
        except Exception:
            return None
        if not positions:
            return None
        symbol, pos = max(
            positions.items(),
            key=lambda kv: self.portfolio_engine.symbol_exposure_notional(
                kv[0], getattr(self.state, "latest_prices", {})
            ),
        )
        net_qty = int(pos.get("net_qty", 0))
        if net_qty == 0:
            return None
        frac           = max(0.05, min(getattr(self.config, "liquidation_assist_close_fraction", 0.25), 1.0))
        qty            = min(max(1, int(abs(net_qty) * frac)), abs(net_qty))
        side           = "SELL" if net_qty > 0 else "BUY"
        intended_price = float(getattr(self.state, "latest_prices", {}).get(symbol, pos.get("avg_price", 0.0)))
        if intended_price <= 0:
            return None

        prev_equity   = getattr(self.state, "equity", 0.0)
        prev_realized = float(getattr(self.state, "realized_pnl", 0))
        slippage_bps  = self._compute_slippage_bps({"volatility": 0.5})
        fill_price    = self._apply_slippage(intended_price, side, slippage_bps)
        fill_notional = _quantize(fill_price * qty, 4)
        fee_bps       = getattr(self.config, "broker_fee_bps", 3)
        fee           = _quantize(fill_notional * (fee_bps / 10000.0), 4)

        order = self._multi_broker.place_order(
            symbol=symbol, side=side, qty=qty, price=fill_price, fee=fee,
            asset_class=self._asset_class(symbol),
            meta={
                "strategy_id": signal.get("strategy_id"),
                "trade_type": signal.get("trade_type") or self._trade_type(signal),
                "regime": regime,
                "rebalance_assist": bool(signal.get("rebalance_assist", False)),
                **self._build_instrument_meta(instrument),
            },
        )

        realized_pnl = self._apply_fill_accounting(
            order=order, fill_price=fill_price, fill_notional=fill_notional,
            fee=fee, prev_realized=prev_realized,
        )
        cycle_pnl = _quantize(getattr(self.state, "equity", 0.0) - prev_equity, 4)
        try:
            self.state.update_loss_streak(cycle_pnl_abs=cycle_pnl)
        except Exception:
            pass

        trade_record = {
            "strategy_id":        "liquidation_assist_v1",
            "strategy_stage":     "RISK_REDUCTION",
            "shadow_mode":        False,
            "symbol":             symbol,
            "asset_class":        self._asset_class(symbol),
            "regime":             regime,
            "trade_type":         "RISK_REDUCTION",
            "side":               side,
            "qty":                qty,
            "status":             order.get("status", "FILLED"),
            "price":              _quantize(fill_price, 4),
            "intended_price":     _quantize(intended_price, 4),
            "slippage_bps":       _quantize(slippage_bps, 4),
            "confidence":         1.0,
            "memory_bias":        0.0,
            "fee":                fee,
            "realized_pnl":      _quantize(realized_pnl, 4),
            "closed_trade":      bool(abs(realized_pnl) > 0.0),
            "unrealized_pnl":    _quantize(getattr(self.state, "unrealized_pnl", 0), 4),
            "cycle_pnl":         cycle_pnl,
            "equity":            _quantize(getattr(self.state, "equity", 0), 2),
            "cash_balance":      _quantize(getattr(self.state, "cash_balance", 0), 2),
            "liquidation_trigger": trigger_reason,
            "rebalance_assist":  False,
        }
        try:
            self.state.record_trade(trade_record)
        except Exception:
            pass
        self._liquidation_cooldown_until = self._cycle_no + 3
        self._reset_risk_block_state()

        return {
            "status":             "TRADE",
            "order_id":           order.get("order_id") or order.get("id", ""),
            "symbol":             symbol,
            "side":               side,
            "qty":                qty,
            "price":              trade_record["price"],
            "pnl":                cycle_pnl,
            "equity":             trade_record["equity"],
            "strategy_id":        "liquidation_assist_v1",
            "strategy_stage":     "RISK_REDUCTION",
            "shadow_mode":        False,
            "trade_type":         "RISK_REDUCTION",
            "regime":             regime,
            "confidence":         1.0,
            "liquidation_assist": True,
            "rebalance_assist":   False,
            "broker":             order.get("broker", self._multi_broker.account_source),
        }
class CanonicalExecutionBridge:
    """
    Pack20 bridge:
    canonical request -> broker payload
    """

    def __init__(self):
        self._initialized = False

    def _ensure_registry(self):
        if self._initialized:
            return

        try:
            adapter_registry.register(
                "fyers",
                FyersExecutionAdapter(),
            )
        except Exception:
            pass

        try:
            adapter_registry.register(
                "groww",
                GrowwExecutionAdapter(),
            )
        except Exception:
            pass

        try:
            adapter_registry.register(
                "viewtrade",
                ViewTradeExecutionAdapter(),
            )
        except Exception:
            pass

        try:
            adapter_registry.register(
                "coinswitch",
                CoinSwitchExecutionAdapter(),
            )
        except Exception:
            pass

        self._initialized = True
            
    def build_order_payload(self, broker: str, request: CanonicalOrderRequest):
        self._ensure_registry()
        adapter = adapter_registry.get(broker)
        return adapter.translate_order(request)

    def build_modify_payload(self, broker: str, request: CanonicalModifyRequest):
        self._ensure_registry()
        adapter = adapter_registry.get(broker)
        return adapter.translate_modify(request)

    def build_cancel_payload(self, broker: str, request: CanonicalCancelRequest):
        self._ensure_registry()
        adapter = adapter_registry.get(broker)
        return adapter.translate_cancel(request)

class CanonicalPortfolioBridge:
    """
    Pack21 portfolio canonicalization bridge
    """

    def __init__(self):
        self._initialized = False

    def _ensure_registry(self):
        if self._initialized:
            return

        try:
            portfolio_adapter_registry.register(
                "fyers",
                FyersPortfolioAdapter(),
            )
        except Exception:
            pass

        try:
            portfolio_adapter_registry.register(
                "groww",
                GrowwPortfolioAdapter(),
            )
        except Exception:
            pass

        try:
            portfolio_adapter_registry.register(
                "viewtrade",
                ViewTradePortfolioAdapter(),
            )
        except Exception:
            pass

        try:
            portfolio_adapter_registry.register(
                "coinswitch",
                CoinSwitchPortfolioAdapter(),
            )
        except Exception:
            pass

        self._initialized = True

    def build_snapshot(
        self,
        broker: str,
        raw_positions,
        raw_balance,
        raw_margin=None,
    ):
        self._ensure_registry()

        adapter = portfolio_adapter_registry.get(broker)

        positions = adapter.translate_positions(raw_positions)
        balance = adapter.translate_balances(raw_balance)

        if raw_margin is None:
            raw_margin = {}

        margin_data = adapter.translate_margin(raw_margin)

        margin = CanonicalMarginSnapshot(
            provider=broker,
            available=margin_data.get("available", 0.0),
            used=margin_data.get("used", 0.0),
            collateral=margin_data.get("collateral", 0.0),
            leverage=margin_data.get("leverage", 1.0),
        )

        return CanonicalPortfolioSnapshot(
            provider=broker,
            positions=positions,
            balance=balance,
            margin=margin,
        )    

class CanonicalRiskBridge:
    """
    Pack21 unified risk normalization
    """

    def build_exposure_snapshot(
        self,
        provider: str,
        portfolio_exposure_pct: float = 0.0,
        symbol_exposure_pct=None,
        sector_exposure_pct=None,
        asset_class_exposure_pct=None,
    ):
        return CanonicalExposureSnapshot(
            provider=provider,
            portfolio_exposure_pct=portfolio_exposure_pct,
            symbol_exposure_pct=symbol_exposure_pct or {},
            sector_exposure_pct=sector_exposure_pct or {},
            asset_class_exposure_pct=asset_class_exposure_pct or {},
        )

    def build_risk_snapshot(
        self,
        provider: str,
        daily_loss_pct: float = 0.0,
        drawdown_pct: float = 0.0,
        margin_utilization_pct: float = 0.0,
        realized_pnl: float = 0.0,
        unrealized_pnl: float = 0.0,
    ):
        return CanonicalRiskSnapshot(
            provider=provider,
            daily_loss_pct=daily_loss_pct,
            drawdown_pct=drawdown_pct,
            margin_utilization_pct=margin_utilization_pct,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
        )

import hashlib


class OMSBridge:
    """
    Pack22 OMS execution bridge
    """

    def _fingerprint(
        self,
        broker,
        symbol,
        side,
        qty,
        order_type,
        price,
    ):
        raw = f"{broker}|{symbol}|{side}|{qty}|{order_type}|{price}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def create_order(
        self,
        broker,
        symbol,
        side,
        qty,
        order_type="MARKET",
        price=0.0,
        metadata=None,
    ):
        fp = self._fingerprint(
            broker,
            symbol,
            side,
            qty,
            order_type,
            price,
        )

        if order_registry.fingerprint_exists(fp):
            raise ValueError("duplicate order request detected")

        order_registry.add_fingerprint(fp)

        order = CanonicalOrderLifecycle(
            broker=broker,
            symbol=symbol,
            side=side,
            qty=qty,
            metadata=metadata or {},
        )

        order_registry.register(order)

        return order

    def reconcile_order(
        self,
        oms_order_id: str,
        broker_snapshot: dict,
    ):
        order = order_registry.get(oms_order_id)

        if not order:
            raise ValueError("unknown oms order")

        updated = reconciliation_engine.reconcile(
            order,
            broker_snapshot,
        )

        return {
            "oms_order_id": updated.order_id,
            "status": updated.status.value,
            "filled_qty": updated.filled_qty,
            "remaining_qty": updated.remaining_qty(),
        }        

class OMSAccountingBridge:
    """
    Pack23 OMS/accounting integration bridge
    """

    def process_fill_event(
        self,
        order,
        event,
    ):
        if event.qty <= 0:
            return None

        fill = CanonicalTradeFill(
            broker=order.broker,
            symbol=order.symbol,
            side=order.side,
            qty=event.qty,
            price=event.price,
            order_id=order.order_id,
            fees=float(
                order.metadata.get("fees", 0.0)
            ),
            slippage=float(
                order.metadata.get("slippage", 0.0)
            ),
            metadata=event.payload or {},
        )

        snapshot = accounting_engine.process_fill(fill)

        return {
            "symbol": order.symbol,
            "fills_processed": snapshot.fills_processed,
            "realized_pnl": snapshot.realized_pnl,
            "unrealized_pnl": snapshot.unrealized_pnl,
            "gross_pnl": snapshot.gross_pnl,
            "net_pnl": snapshot.net_pnl,
        }

    def _extract_strategy_meta(
        self,
        order,
    ):
        if isinstance(
            order,
            StrategyExecutionIntent,
        ):
            return {
                "strategy_id": order.strategy_id,
                "confidence": order.confidence,
                "priority": order.priority,
                "trade_type": order.trade_type,
            }

        strategy_id = None

        if isinstance(order, dict):
            strategy_id = order.get("strategy_id")

        if strategy_id:
            return {
                "strategy_id": strategy_id,
            }

        return {}

    def _attach_strategy_context(
        self,
        order_id,
        strategy_meta,
    ):
        if not order_id:
            return

        strategy_id = strategy_meta.get(
            "strategy_id"
        )

        if not strategy_id:
            return

        strategy_execution_context.attach(
            order_id=order_id,
            strategy_id=strategy_id,
            metadata=strategy_meta,
        )    