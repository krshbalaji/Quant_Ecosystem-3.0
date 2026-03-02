import random

from core.config_loader import Config
from execution.instrument_policy_engine import InstrumentPolicyEngine
from intelligence.candle_angle_engine import CandleAngleEngine
from intelligence.candle_pattern_engine import CandlePatternEngine
from utils.decimal_utils import quantize


class ExecutionRouter:

    def __init__(
        self,
        broker,
        risk_engine,
        state,
        market_data=None,
        strategy_engine=None,
        portfolio_engine=None,
        reconciler=None,
        capital_governance=None,
        position_sizer=None,
        symbols=None,
    ):
        self.broker = broker
        self.risk_engine = risk_engine
        self.state = state
        self.market_data = market_data
        self.strategy_engine = strategy_engine
        self.portfolio_engine = portfolio_engine
        self.reconciler = reconciler
        self.capital_governance = capital_governance
        self.position_sizer = position_sizer
        self.symbols = symbols or ["NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:INFY-EQ"]
        self.telegram = None
        self.config = Config()
        self.instrument_policy = InstrumentPolicyEngine()
        self.candle_pattern = CandlePatternEngine()
        self.candle_angle = CandleAngleEngine()

    async def execute(self, signal=None, market_bias="NEUTRAL", regime="MEAN_REVERSION"):
        result = self.run_cycle(signal=signal, market_bias=market_bias, regime=regime)
        if self.telegram:
            self.telegram.notify_trade(result)
        return result

    def run_cycle(self, signal=None, market_bias="NEUTRAL", regime="MEAN_REVERSION"):
        if self.state.trading_halted:
            return {"status": "SKIP", "reason": "TRADING_HALTED"}
        if not self.state.trading_enabled:
            return {"status": "SKIP", "reason": "TRADING_DISABLED"}
        if not self.state.auto_mode and signal is None:
            return {"status": "SKIP", "reason": "AUTO_DISABLED"}
        if self.state.cooldown > 0:
            self.state.cooldown -= 1
            return {"status": "SKIP", "reason": "COOLDOWN"}

        snapshots = self._build_snapshots(regime=regime)
        if not snapshots:
            return {"status": "SKIP", "reason": "NO_MARKET_DATA"}

        self.state.latest_prices = {snap["symbol"]: snap["price"] for snap in snapshots}
        prev_equity = self.state.equity
        if self.reconciler:
            self.reconciler.reconcile(latest_prices=self.state.latest_prices)
        else:
            self.state.mark_to_market(self.portfolio_engine)

        candidate_signal = signal or self._select_signal(
            snapshots=snapshots,
            market_bias=market_bias,
            regime=regime,
        )
        if not candidate_signal:
            return {"status": "SKIP", "reason": "NO_SIGNAL"}
        if not self._is_valid_signal(candidate_signal):
            return {"status": "SKIP", "reason": "INVALID_SIGNAL"}

        exposure_pct = self._portfolio_exposure_pct()
        symbol_exposure_pct = self._symbol_exposure_pct(candidate_signal["symbol"])
        allowed, reason = self.risk_engine.allow_trade(
            self.state,
            portfolio_exposure_pct=exposure_pct,
            symbol_exposure_pct=symbol_exposure_pct,
        )
        if not allowed:
            return {"status": "SKIP", "reason": reason}

        qty, size_reason = self._allocate_quantity(candidate_signal)
        if qty <= 0:
            return {"status": "SKIP", "reason": size_reason}

        intended_price = candidate_signal["price"]
        slippage_bps = self._compute_slippage_bps(candidate_signal)
        fill_price = self._apply_slippage(intended_price, candidate_signal["side"], slippage_bps)
        fill_notional = quantize(fill_price * qty, 4)
        fee = quantize(fill_notional * (self.config.broker_fee_bps / 10000.0), 4)

        order = self.broker.place_order(
            symbol=candidate_signal["symbol"],
            side=candidate_signal["side"],
            qty=qty,
            price=fill_price,
            fee=fee,
            meta={
                "strategy_id": candidate_signal["strategy_id"],
                "trade_type": candidate_signal.get("trade_type") or self._trade_type(candidate_signal),
                "regime": regime,
            },
        )
        if self.reconciler:
            snapshot = self.reconciler.reconcile(latest_prices=self.state.latest_prices)
            realized_pnl = float(order.get("realized_pnl", 0.0))
            broker_orders = snapshot.get("orders", [])
            if broker_orders:
                self.state.turnover = quantize(
                    sum(float(item.get("price", 0.0)) * float(item.get("qty", 0.0)) for item in broker_orders),
                    4,
                )
        else:
            fill_result = self.portfolio_engine.apply_fill(
                symbol=order["symbol"],
                side=order["side"],
                qty=order["qty"],
                price=fill_price,
            )
            realized_pnl = float(fill_result["realized_pnl"])
            self.state.apply_fill_accounting(
                side=order["side"],
                fill_notional=fill_notional,
                fee=fee,
                realized_pnl=realized_pnl,
            )

            self.state.open_positions = self.portfolio_engine.exposure()
            self.state.mark_to_market(self.portfolio_engine)
        cycle_pnl = quantize(self.state.equity - prev_equity, 4)
        self.state.update_loss_streak(cycle_pnl_abs=cycle_pnl)

        trade_record = {
            "strategy_id": candidate_signal["strategy_id"],
            "strategy_stage": candidate_signal.get("strategy_stage", "UNKNOWN"),
            "shadow_mode": bool(candidate_signal.get("shadow_mode", False)),
            "symbol": order["symbol"],
            "asset_class": self._asset_class(order["symbol"]),
            "regime": regime,
            "trade_type": candidate_signal.get("trade_type") or self._trade_type(candidate_signal),
            "side": order["side"],
            "qty": order["qty"],
            "status": order.get("status", "UNKNOWN"),
            "price": quantize(fill_price, 4),
            "intended_price": quantize(intended_price, 4),
            "slippage_bps": quantize(slippage_bps, 4),
            "confidence": quantize(candidate_signal.get("confidence", 0.0), 4),
            "fee": fee,
            "realized_pnl": quantize(realized_pnl, 4),
            "unrealized_pnl": quantize(self.state.unrealized_pnl, 4),
            "cycle_pnl": cycle_pnl,
            "equity": quantize(self.state.equity, 2),
            "cash_balance": quantize(self.state.cash_balance, 2),
        }
        self.state.record_trade(trade_record)

        return {
            "status": "TRADE",
            "symbol": order["symbol"],
            "side": order["side"],
            "qty": order["qty"],
            "pnl": trade_record["cycle_pnl"],
            "equity": trade_record["equity"],
            "strategy_id": trade_record["strategy_id"],
            "strategy_stage": trade_record["strategy_stage"],
            "shadow_mode": trade_record["shadow_mode"],
            "trade_type": trade_record["trade_type"],
            "regime": trade_record["regime"],
            "confidence": trade_record["confidence"],
            "price": trade_record["price"],
        }

    def start_trading(self):
        self.state.trading_enabled = True
        self.state.trading_halted = False
        return "Trading started."

    def stop_trading(self):
        self.state.trading_enabled = False
        return "Trading stopped."

    def kill_switch(self):
        self.state.trading_enabled = False
        self.state.trading_halted = True
        return "Kill switch activated. Trading halted."

    def set_auto_mode(self, enabled):
        self.state.auto_mode = bool(enabled)
        return f"Auto mode set to {self.state.auto_mode}."

    def set_trading_mode(self, mode):
        normalized = str(mode).upper()
        if normalized not in {"PAPER", "LIVE"}:
            return "Invalid mode. Use PAPER or LIVE."
        self.state.trading_mode = normalized
        return f"Trading mode set to {normalized}."

    def set_risk_preset(self, preset):
        mapping = {"25%": 0.25, "50%": 0.50, "100%": 1.00}
        factor = mapping.get(preset)
        if factor is None:
            return "Invalid risk preset. Use 25%, 50%, or 100%."
        base = self.risk_engine.base_trade_risk
        new_value = self.risk_engine.set_trade_risk_pct(base * factor)
        self.state.risk_preset = preset
        return f"Risk preset {preset} applied. Trade risk={quantize(new_value, 2)}%."

    def set_strategy_profile(self, profile):
        normalized = str(profile).upper()
        if normalized not in {"ALPHA", "BETA", "GAMMA"}:
            return "Invalid profile. Use Alpha, Beta, or Gamma."
        self.state.strategy_profile = normalized
        return f"Strategy profile set to {normalized}."

    def get_status_report(self):
        return (
            f"enabled={self.state.trading_enabled} "
            f"halted={self.state.trading_halted} "
            f"mode={self.state.trading_mode} "
            f"auto={self.state.auto_mode} "
            f"profile={self.state.strategy_profile} "
            f"risk_preset={self.state.risk_preset} "
            f"source={self.state.account_source} "
            f"equity={quantize(self.state.equity, 2)} "
            f"cash={quantize(self.state.cash_balance, 2)} "
            f"realized={quantize(self.state.realized_pnl, 2)} "
            f"unrealized={quantize(self.state.unrealized_pnl, 2)} "
            f"fees={quantize(self.state.fees_paid, 2)} "
            f"drawdown={quantize(self.state.total_drawdown_pct, 2)}% "
            f"exposure={quantize(self._portfolio_exposure_pct(), 2)}% "
            f"sync={self.state.last_reconciled_at or 'NA'} "
            f"cooldown={self.state.cooldown} "
            f"consecutive_losses={self.state.consecutive_losses} "
            f"trades={len(self.state.trade_history)}"
        )

    def get_positions_report(self):
        positions = self.portfolio_engine.snapshot()
        if not positions:
            return "Open positions: 0"
        return f"Open positions: {len(positions)} | {positions}"

    def get_strategy_report(self):
        strategies = self.strategy_engine.strategies if self.strategy_engine else []
        if self.strategy_engine and self.strategy_engine.active_ids is not None:
            ids = [item["id"] for item in strategies if item["id"] in self.strategy_engine.active_ids]
        else:
            ids = [item["id"] for item in strategies]
        if not ids:
            return "Active strategies: none (all rejected/disabled)"
        return "Active strategies: " + ", ".join(ids)

    def get_dashboard_report(self):
        price = 0.0
        if self.symbols:
            symbol = self.symbols[0]
            price = float(self.state.latest_prices.get(symbol, 0.0))
        else:
            symbol = "-"

        trades = self.state.trade_history
        if trades:
            wins = [item for item in trades if float(item.get("cycle_pnl", 0.0)) > 0]
            win_rate = (len(wins) / len(trades)) * 100.0
            profit_abs = sum(float(item.get("cycle_pnl", 0.0)) for item in trades)
            last = trades[-1]
            last_line = (
                f"Last: {last.get('trade_type', 'NA')} {last.get('side', '')} "
                f"{last.get('symbol', '')} pnl={quantize(last.get('cycle_pnl', 0), 2)}"
            )
        else:
            win_rate = 0.0
            profit_abs = 0.0
            last_line = "Last: NA"

        return (
            "Institutional Control Terminal\n\n"
            f"Symbol: {symbol}\n"
            f"Price: {quantize(price, 2)}\n"
            f"Mode: {self.state.trading_mode}\n"
            f"TradeType: {self._trade_type()}\n"
            f"Risk: {quantize(self.risk_engine.max_trade_risk, 2)}%\n"
            f"Profile: {self.state.strategy_profile}\n"
            f"Winrate: {quantize(win_rate, 2)}% | Profit: {quantize(profit_abs, 2)}\n"
            f"Equity: {quantize(self.state.equity, 2)} | Cash: {quantize(self.state.cash_balance, 2)}\n"
            f"Realized: {quantize(self.state.realized_pnl, 2)} | Unrealized: {quantize(self.state.unrealized_pnl, 2)}\n"
            f"Source: {self.state.account_source}\n"
            f"Sync: {self.state.last_reconciled_at or 'NA'}\n"
            f"B.Pos/Ord/Trd: {self.state.broker_positions_count}/{self.state.broker_orders_count}/{self.state.broker_trades_count}\n"
            f"Auto: {self.state.auto_mode}\n"
            f"{last_line}"
        )

    def _build_snapshots(self, regime):
        if not self.market_data:
            return []
        symbols = self._dynamic_symbols(regime)
        snapshots = []
        for symbol in symbols:
            raw = self.market_data.get_snapshot(symbol=symbol, lookback=60)
            snapshots.append(self._enrich_snapshot(raw))
        return snapshots

    def _select_signal(self, snapshots, market_bias, regime):
        if not self.strategy_engine:
            return None

        candidates = self.strategy_engine.evaluate(
            snapshots=snapshots,
            market_bias=market_bias,
            regime=regime,
        )
        if not candidates:
            return None

        for candidate in candidates:
            symbol_penalty = self._symbol_exposure_pct(candidate["symbol"]) / 100.0
            candidate["rank_score"] = candidate.get("confidence", 0.0) - (0.2 * symbol_penalty)
            candidate["trade_type"] = self._determine_trade_type(candidate, regime)

        threshold = self._profile_threshold()
        filtered = [item for item in candidates if item.get("confidence", 0.0) >= threshold]
        if not filtered:
            filtered = candidates

        trade_type = self._trade_type()
        selected = self.instrument_policy.select(filtered, regime=regime, trade_type=trade_type)
        if selected:
            return selected

        filtered.sort(key=lambda item: item.get("rank_score", 0), reverse=True)
        top_bucket = filtered[: min(3, len(filtered))]
        weighted = [max(0.01, item.get("rank_score", 0.01)) for item in top_bucket]
        return random.choices(top_bucket, weights=weighted, k=1)[0]

    def _is_valid_signal(self, signal):
        required_fields = {"strategy_id", "symbol", "side", "price"}
        if not required_fields.issubset(set(signal.keys())):
            return False
        if signal["side"] not in {"BUY", "SELL"}:
            return False
        if signal["price"] <= 0:
            return False
        return True

    def _dynamic_symbols(self, regime):
        base = list(self.symbols)
        if regime == "CRISIS":
            extra = ["NSE:SBIN-EQ", "NSE:RELIANCE-EQ"]
        elif regime == "HIGH_VOLATILITY":
            extra = ["NSE:SBIN-EQ", "NSE:ICICIBANK-EQ", "NSE:TCS-EQ"]
        elif regime == "LOW_VOLATILITY":
            extra = ["NSE:RELIANCE-EQ", "NSE:INFY-EQ", "NSE:HDFCBANK-EQ"]
        elif regime == "TREND":
            extra = ["NSE:RELIANCE-EQ", "NSE:TCS-EQ", "NSE:LT-EQ"]
        else:
            extra = ["NSE:SBIN-EQ", "NSE:INFY-EQ", "NSE:ITC-EQ"]

        merged = []
        for symbol in base + extra:
            if symbol not in merged:
                merged.append(symbol)
        return merged[:8]

    def _enrich_snapshot(self, snapshot):
        closes = snapshot.get("close", [])
        if len(closes) < 3:
            snapshot["candle_angle"] = 0.0
            snapshot["candle_patterns"] = []
            return snapshot

        candle = {
            "open": float(closes[-2]),
            "close": float(closes[-1]),
            "high": max(float(closes[-1]), float(closes[-2])),
            "low": min(float(closes[-1]), float(closes[-2])),
        }
        snapshot["candle_angle"] = quantize(self.candle_angle.calculate(closes[-20:]), 6)
        snapshot["candle_patterns"] = self.candle_pattern.detect(candle)
        return snapshot

    def _determine_trade_type(self, signal, regime):
        patterns = set(signal.get("candle_patterns", []))
        angle = float(signal.get("candle_angle", 0.0))
        volatility = float(signal.get("volatility", 0.0))

        if regime in {"CRISIS", "HIGH_VOLATILITY"}:
            return "SCALP"
        if "DOJI" in patterns and regime == "MEAN_REVERSION":
            return "INTRADAY"
        if abs(angle) > 0.08 and volatility < 0.8:
            return "SWING"
        return self._trade_type(signal)

    def _allocate_quantity(self, signal):
        price = signal["price"]

        if self.position_sizer:
            qty = self.position_sizer.size(
                equity=self.state.equity,
                price=price,
                volatility=max(signal.get("volatility", 1.0), 0.01),
            )
            base_qty = max(int(qty), 0)
        else:
            risk_budget = self.risk_engine.trade_risk(self.state.equity)
            base_qty = int(risk_budget / price)

        if base_qty <= 0:
            return 0, "ZERO_SIZE"

        if self.capital_governance:
            scale = self.capital_governance.sizing_multiplier(self.state.trade_history)
            base_qty = max(int(base_qty * scale), 0)
            strategy_limit_qty = int(self.capital_governance.max_strategy_notional(self.state.equity) / price)
            asset_class = self._asset_class(signal["symbol"])
            asset_left = max(
                0.0,
                self.capital_governance.max_asset_class_notional(self.state.equity)
                - self._asset_class_exposure_notional(asset_class),
            )
            asset_limit_qty = int(asset_left / price)
            base_qty = min(base_qty, strategy_limit_qty, asset_limit_qty)

        if signal.get("shadow_mode"):
            # Shadow deployment in PAPER mode to gather evidence safely.
            base_qty = max(1, int(base_qty * 0.25))

        allowed_by_portfolio = int(self._available_portfolio_notional() / price)
        if allowed_by_portfolio <= 0:
            return 0, "MAX_PORTFOLIO_EXPOSURE"

        allowed_by_symbol = int(self._available_symbol_notional(signal["symbol"]) / price)
        if allowed_by_symbol <= 0:
            return 0, "MAX_SYMBOL_EXPOSURE"

        final_qty = min(base_qty, allowed_by_portfolio, allowed_by_symbol)
        return max(final_qty, 0), "OK"

    def _portfolio_exposure_pct(self):
        notional = self.portfolio_engine.net_exposure_notional(self.state.latest_prices)
        if self.state.equity <= 0:
            return 100.0
        return quantize((notional / self.state.equity) * 100.0, 4)

    def _symbol_exposure_pct(self, symbol):
        notional = self.portfolio_engine.symbol_exposure_notional(symbol, self.state.latest_prices)
        if self.state.equity <= 0:
            return 100.0
        return quantize((notional / self.state.equity) * 100.0, 4)

    def _available_portfolio_notional(self):
        max_notional = self.state.equity * (self.risk_engine.max_portfolio_risk / 100.0)
        used = self.portfolio_engine.net_exposure_notional(self.state.latest_prices)
        return max(0.0, max_notional - used)

    def _available_symbol_notional(self, symbol):
        max_notional = self.state.equity * (self.risk_engine.max_symbol_risk / 100.0)
        used = self.portfolio_engine.symbol_exposure_notional(symbol, self.state.latest_prices)
        return max(0.0, max_notional - used)

    def _compute_slippage_bps(self, signal):
        volatility_pct = max(signal.get("volatility", 0.2), 0.05)
        raw = self.config.base_slippage_bps + (volatility_pct * 1.5)
        return quantize(min(raw, self.config.max_slippage_bps), 4)

    def _apply_slippage(self, price, side, slippage_bps):
        slip = slippage_bps / 10000.0
        if side == "BUY":
            return quantize(price * (1 + slip), 4)
        return quantize(price * (1 - slip), 4)

    def _profile_threshold(self):
        profile = str(self.state.strategy_profile).upper()
        if profile == "ALPHA":
            return 0.72
        if profile == "GAMMA":
            return 0.52
        return 0.62

    def _trade_type(self, signal=None):
        if signal and signal.get("trade_type"):
            return str(signal["trade_type"]).upper()
        profile = str(self.state.strategy_profile).upper()
        if profile == "ALPHA":
            return "SWING"
        if profile == "GAMMA":
            return "SCALP"
        return "INTRADAY"

    def _asset_class(self, symbol):
        value = symbol.upper()
        if "CRYPTO" in value or value.endswith("USDT"):
            return "CRYPTO"
        if "FX" in value or "FOREX" in value:
            return "FOREX"
        if "FUT" in value:
            return "FUTURES"
        if "OPT" in value:
            return "OPTIONS"
        return "EQUITY"

    def _asset_class_exposure_notional(self, asset_class):
        total = 0.0
        for symbol, pos in self.portfolio_engine.positions.items():
            if self._asset_class(symbol) != asset_class:
                continue
            price = self.state.latest_prices.get(symbol)
            if price is None:
                continue
            total += abs(pos["net_qty"] * price)
        return quantize(total, 4)
