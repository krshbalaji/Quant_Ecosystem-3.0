import random
from datetime import datetime, time as dtime, timedelta, timezone
from zoneinfo import ZoneInfo

from quant_ecosystem.core.config_loader import Config
from quant_ecosystem.execution.instrument_policy_engine import InstrumentPolicyEngine
from quant_ecosystem.intelligence.candle_angle_engine import CandleAngleEngine
from quant_ecosystem.intelligence.candle_pattern_engine import CandlePatternEngine
from quant_ecosystem.utils.decimal_utils import quantize


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
        outcome_memory=None,
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
        self.outcome_memory = outcome_memory
        self.telegram = None
        self.config = Config()
        self.instrument_policy = InstrumentPolicyEngine()
        self.candle_pattern = CandlePatternEngine()
        self.candle_angle = CandleAngleEngine()
        self._cycle_no = 0
        self._symbol_cooldown_until = {}
        self._symbol_strategy_owner = {}
        self._risk_block_streak = 0
        self._last_risk_block_reason = ""
        self._liquidation_cooldown_until = 0

    async def execute(self, signal=None, market_bias="NEUTRAL", regime="MEAN_REVERSION"):
        result = self.run_cycle(signal=signal, market_bias=market_bias, regime=regime)
        if self.telegram:
            self.telegram.notify_trade(result)
        return result

    def run_cycle(self, signal=None, market_bias="NEUTRAL", regime="MEAN_REVERSION"):
        self._cycle_no += 1
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
        prev_realized_account = float(self.state.realized_pnl)
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
            rebalance_signal = self._maybe_rebalance_signal(regime=regime)
            if rebalance_signal:
                candidate_signal = rebalance_signal
        if not candidate_signal:
            return {"status": "SKIP", "reason": "NO_SIGNAL"}
        if bool(getattr(self.config, "strict_market_hours", False)):
            if not self._is_symbol_tradable_now(candidate_signal.get("symbol")):
                self._reset_risk_block_state()
                return {"status": "SKIP", "reason": "MARKET_CLOSED"}
        if not self._is_valid_signal(candidate_signal):
            self._reset_risk_block_state()
            return {"status": "SKIP", "reason": "INVALID_SIGNAL"}
        is_rebalance = bool(candidate_signal.get("rebalance_assist", False))
        if (not is_rebalance) and (not self._passes_context_filter(candidate_signal, regime)):
            self._reset_risk_block_state()
            return {"status": "SKIP", "reason": "WEAK_CONTEXT"}
        if self._is_symbol_in_cooldown(candidate_signal["symbol"]):
            self._reset_risk_block_state()
            return {"status": "SKIP", "reason": "SYMBOL_COOLDOWN"}

        exposure_pct = self._portfolio_exposure_pct()
        symbol = candidate_signal["symbol"]
        symbol_exposure_pct = self._symbol_exposure_pct(symbol)
        daily_trade_count = self._daily_trade_count()
        symbol_daily_loss_pct = self._symbol_daily_loss_pct(symbol)
        asset_exposure_pct = self._asset_exposure_pct(self._asset_class(symbol))
        strategy_exposure_pct = self._strategy_exposure_pct(candidate_signal.get("strategy_id"))
        sector_exposure_pct = self._sector_exposure_pct(symbol)
        exposure_reducing = self._is_exposure_reducing_signal(candidate_signal)
        active_strategy_count = self._active_strategy_count()
        allowed, reason = self.risk_engine.allow_trade(
            self.state,
            portfolio_exposure_pct=exposure_pct,
            symbol_exposure_pct=symbol_exposure_pct,
            daily_trade_count=daily_trade_count,
            symbol_daily_loss_pct=symbol_daily_loss_pct,
            sector_exposure_pct=sector_exposure_pct,
            strategy_exposure_pct=strategy_exposure_pct,
            asset_exposure_pct=asset_exposure_pct,
            exposure_reducing=exposure_reducing,
            active_strategy_count=active_strategy_count,
        )
        if not allowed:
            if self._is_exposure_block(reason):
                self._track_risk_block(reason)
                liquidation = self._maybe_liquidation_assist(trigger_reason=reason, regime=regime)
                if liquidation:
                    return liquidation
            else:
                self._reset_risk_block_state()
            return {"status": "SKIP", "reason": reason}
        self._reset_risk_block_state()

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
                "rebalance_assist": bool(candidate_signal.get("rebalance_assist", False)),
            },
        )
        if self.reconciler:
            snapshot = self.reconciler.reconcile(latest_prices=self.state.latest_prices)
            realized_pnl = float(self.state.realized_pnl) - prev_realized_account
            if abs(realized_pnl) < 1e-8:
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
            "memory_bias": quantize(candidate_signal.get("memory_bias", 0.0), 6),
            "rebalance_assist": bool(candidate_signal.get("rebalance_assist", False)),
            "fee": fee,
            "realized_pnl": quantize(realized_pnl, 4),
            "closed_trade": bool(abs(realized_pnl) > 0.0),
            "unrealized_pnl": quantize(self.state.unrealized_pnl, 4),
            "cycle_pnl": cycle_pnl,
            "equity": quantize(self.state.equity, 2),
            "cash_balance": quantize(self.state.cash_balance, 2),
        }
        self.state.record_trade(trade_record)
        self._symbol_strategy_owner[order["symbol"]] = candidate_signal["strategy_id"]
        self._set_symbol_cooldown(order["symbol"], trade_record["trade_type"])

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
            "liquidation_assist": False,
            "rebalance_assist": trade_record["rebalance_assist"],
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
            f"day_trades={self._daily_trade_count()}/{self.risk_engine.max_daily_trades} "
            f"survival_mode={getattr(self, 'survival_mode', 'NORMAL')} "
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
        compatible = [item for item in candidates if self._strategy_symbol_compatible(item)]
        if compatible:
            candidates = compatible
        if bool(getattr(self.config, "strict_market_hours", False)):
            open_now = [item for item in candidates if self._is_symbol_tradable_now(item.get("symbol"))]
            if open_now:
                candidates = open_now
            else:
                return None

        for candidate in candidates:
            symbol_penalty = self._symbol_exposure_pct(candidate["symbol"]) / 100.0
            candidate["rank_score"] = candidate.get("confidence", 0.0) - (0.2 * symbol_penalty)
            candidate["trade_type"] = self._determine_trade_type(candidate, regime)
            if self.outcome_memory:
                candidate["memory_bias"] = self.outcome_memory.signal_bias(
                    strategy_id=candidate.get("strategy_id"),
                    symbol=candidate.get("symbol"),
                    regime=regime,
                    trade_type=candidate.get("trade_type"),
                )
                candidate["rank_score"] += float(candidate["memory_bias"])
            else:
                candidate["memory_bias"] = 0.0
            if candidate.get("shadow_mode"):
                # Stricter bar in shadow deployment.
                candidate["rank_score"] -= 0.08

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
        extras = self._regime_extras_for_asset_classes(regime=regime, symbols=base)

        merged = []
        for symbol in base + extras:
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

    def _passes_context_filter(self, signal, regime):
        confidence = float(signal.get("confidence", 0.0))
        side = str(signal.get("side", "HOLD")).upper()
        angle = float(signal.get("candle_angle", 0.0))
        patterns = set(signal.get("candle_patterns", []))
        is_shadow = bool(signal.get("shadow_mode", False))

        base_min = 0.58
        if is_shadow:
            base_min = 0.70
        if regime in {"HIGH_VOLATILITY", "CRISIS"}:
            base_min += 0.04
        if confidence < base_min:
            return False

        if side == "BUY" and "BEAR_ENGULF" in patterns:
            return False
        if side == "SELL" and "BULL_ENGULF" in patterns:
            return False
        if side == "BUY" and angle < -0.06 and regime != "MEAN_REVERSION":
            return False
        if side == "SELL" and angle > 0.06 and regime != "MEAN_REVERSION":
            return False
        return True

    def _is_symbol_in_cooldown(self, symbol):
        return self._cycle_no < int(self._symbol_cooldown_until.get(symbol, 0))

    def _set_symbol_cooldown(self, symbol, trade_type):
        t = str(trade_type).upper()
        if t == "SCALP":
            gap = 1
        elif t == "SWING":
            gap = 3
        else:
            gap = 2
        self._symbol_cooldown_until[symbol] = self._cycle_no + gap

    def _allocate_quantity(self, signal):
        price = signal["price"]
        forced_qty = signal.get("forced_qty")
        if forced_qty is not None:
            qty = max(0, int(forced_qty))
            if qty <= 0:
                return 0, "ZERO_SIZE"
            return qty, "OK"

        if self.position_sizer:
            qty = self.position_sizer.size(
                equity=self.state.equity,
                price=price,
                volatility=max(signal.get("volatility", 1.0), 0.01),
                risk_pct=self.risk_engine.max_trade_risk,
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

    def _daily_trade_count(self):
        return len(self.state.trade_history)

    def _symbol_daily_loss_pct(self, symbol):
        if self.state.equity <= 0:
            return 100.0
        losses = 0.0
        for item in self.state.trade_history:
            if item.get("symbol") != symbol:
                continue
            pnl = float(item.get("cycle_pnl", 0.0))
            if pnl < 0:
                losses += abs(pnl)
        return quantize((losses / self.state.equity) * 100.0, 4)

    def _strategy_exposure_pct(self, strategy_id):
        if self.state.equity <= 0 or not strategy_id:
            return 0.0
        notional = 0.0
        for sym, pos in self.portfolio_engine.positions.items():
            owner = self._symbol_strategy_owner.get(sym)
            if owner != strategy_id:
                continue
            px = self.state.latest_prices.get(sym)
            if px is None:
                continue
            notional += abs(float(pos.get("net_qty", 0.0)) * float(px))
        return quantize((notional / self.state.equity) * 100.0, 4)

    def _active_strategy_count(self):
        if not self.strategy_engine:
            return 1
        ids = getattr(self.strategy_engine, "active_ids", None)
        if ids is None:
            return max(len(getattr(self.strategy_engine, "strategies", []) or []), 1)
        return max(len(ids), 1)

    def _asset_exposure_pct(self, asset_class):
        if self.state.equity <= 0:
            return 100.0
        notional = self._asset_class_exposure_notional(asset_class)
        return quantize((notional / self.state.equity) * 100.0, 4)

    def _sector_exposure_pct(self, symbol):
        # Basic proxy until explicit sector master is integrated.
        # Banking bucket is monitored more tightly because concentration spikes faster.
        sector = "BANKING" if "BANK" in str(symbol).upper() else "GENERAL"
        if self.state.equity <= 0:
            return 100.0
        notional = 0.0
        for sym, pos in self.portfolio_engine.positions.items():
            sym_sector = "BANKING" if "BANK" in str(sym).upper() else "GENERAL"
            if sym_sector != sector:
                continue
            px = self.state.latest_prices.get(sym)
            if px is None:
                continue
            notional += abs(float(pos.get("net_qty", 0.0)) * float(px))
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
        if value.startswith("MCX:"):
            return "COMMODITY"
        if "CRYPTO" in value or value.endswith("USDT"):
            return "CRYPTO"
        if "FX" in value or "FOREX" in value:
            return "FOREX"
        if "FUT" in value:
            return "FUTURES"
        if "OPT" in value:
            return "OPTIONS"
        return "EQUITY"

    def _regime_extras_for_asset_classes(self, regime, symbols):
        classes = {self._asset_class(symbol) for symbol in list(symbols or []) if symbol}
        extras = []
        eq_map = {
            "CRISIS": ["NSE:SBIN-EQ", "NSE:RELIANCE-EQ"],
            "HIGH_VOLATILITY": ["NSE:SBIN-EQ", "NSE:ICICIBANK-EQ", "NSE:TCS-EQ"],
            "LOW_VOLATILITY": ["NSE:RELIANCE-EQ", "NSE:INFY-EQ", "NSE:HDFCBANK-EQ"],
            "TREND": ["NSE:RELIANCE-EQ", "NSE:TCS-EQ", "NSE:LT-EQ"],
            "MEAN_REVERSION": ["NSE:SBIN-EQ", "NSE:INFY-EQ", "NSE:ITC-EQ"],
        }
        fx_map = {
            "CRISIS": ["FX:USDINR", "FX:EURINR"],
            "HIGH_VOLATILITY": ["FX:USDINR", "FX:GBPINR"],
            "LOW_VOLATILITY": ["FX:EURINR", "FX:USDINR"],
            "TREND": ["FX:USDINR", "FX:EURINR"],
            "MEAN_REVERSION": ["FX:EURINR", "FX:USDINR"],
        }
        crypto_map = {
            "CRISIS": ["CRYPTO:BTCUSDT", "CRYPTO:ETHUSDT"],
            "HIGH_VOLATILITY": ["CRYPTO:BTCUSDT", "CRYPTO:ETHUSDT", "CRYPTO:SOLUSDT"],
            "LOW_VOLATILITY": ["CRYPTO:BTCUSDT", "CRYPTO:ETHUSDT"],
            "TREND": ["CRYPTO:BTCUSDT", "CRYPTO:ETHUSDT", "CRYPTO:SOLUSDT"],
            "MEAN_REVERSION": ["CRYPTO:ETHUSDT", "CRYPTO:BTCUSDT"],
        }
        commodity_map = {
            "CRISIS": ["MCX:GOLD", "MCX:SILVER"],
            "HIGH_VOLATILITY": ["MCX:GOLD", "MCX:CRUDEOIL"],
            "LOW_VOLATILITY": ["MCX:GOLD", "MCX:SILVER"],
            "TREND": ["MCX:CRUDEOIL", "MCX:GOLD"],
            "MEAN_REVERSION": ["MCX:GOLD", "MCX:SILVER"],
        }
        regime_key = str(regime or "MEAN_REVERSION").upper()
        if "EQUITY" in classes or "FUTURES" in classes or "OPTIONS" in classes:
            extras.extend(eq_map.get(regime_key, eq_map["MEAN_REVERSION"]))
        if "FOREX" in classes:
            extras.extend(fx_map.get(regime_key, fx_map["MEAN_REVERSION"]))
        if "CRYPTO" in classes:
            extras.extend(crypto_map.get(regime_key, crypto_map["MEAN_REVERSION"]))
        if "COMMODITY" in classes:
            extras.extend(commodity_map.get(regime_key, commodity_map["MEAN_REVERSION"]))
        return extras

    def _strategy_symbol_compatible(self, signal):
        sid = str(signal.get("strategy_id", "")).strip()
        symbol = str(signal.get("symbol", "")).strip()
        if not sid or not symbol:
            return True
        bank_engine = getattr(self, "strategy_bank_engine", None)
        registry = getattr(bank_engine, "registry", None)
        row = registry.get(sid) if registry and hasattr(registry, "get") else None
        strategy_asset = str((row or {}).get("asset_class", "")).strip().lower()
        if not strategy_asset:
            return True
        symbol_asset = self._asset_class(symbol).lower()
        allowed = {
            "stocks": {"equity"},
            "equity": {"equity"},
            "indices": {"equity", "futures", "options"},
            "futures": {"futures"},
            "options": {"options"},
            "forex": {"forex"},
            "fx": {"forex"},
            "crypto": {"crypto"},
            "commodities": {"commodity", "futures"},
            "commodity": {"commodity", "futures"},
            "multi": {"equity", "forex", "crypto", "futures", "options", "commodity"},
        }
        supported = allowed.get(strategy_asset, None)
        if not supported:
            return True
        return symbol_asset in supported

    def _is_symbol_tradable_now(self, symbol):
        sym = str(symbol or "").upper().strip()
        if not sym:
            return False
        if sym.startswith("CRYPTO:") or sym.endswith("USDT"):
            return True

        now_ist = self._now_ist()
        if now_ist.weekday() >= 5:
            return False
        now_t = now_ist.time()

        if sym.startswith("NSE:"):
            return dtime(9, 15) <= now_t <= dtime(15, 30)
        if sym.startswith("MCX:"):
            return dtime(9, 0) <= now_t <= dtime(23, 30)
        return True

    def _now_ist(self):
        try:
            return datetime.now(ZoneInfo("Asia/Kolkata"))
        except Exception:
            ist = timezone(timedelta(hours=5, minutes=30))
            return datetime.now(ist)

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

    def _is_exposure_reducing_signal(self, signal):
        symbol = signal.get("symbol")
        side = str(signal.get("side", "")).upper()
        pos = self.portfolio_engine.positions.get(symbol)
        if not pos:
            return False
        net_qty = float(pos.get("net_qty", 0.0))
        if net_qty > 0 and side == "SELL":
            return True
        if net_qty < 0 and side == "BUY":
            return True
        return False

    def _is_exposure_block(self, reason):
        return reason in {
            "MAX_STRATEGY_EXPOSURE",
            "MAX_PORTFOLIO_EXPOSURE",
            "MAX_SYMBOL_EXPOSURE",
            "MAX_SECTOR_EXPOSURE",
            "MAX_ASSET_EXPOSURE",
        }

    def _maybe_rebalance_signal(self, regime):
        if not self.config.liquidation_assist_enabled:
            return None
        if self._cycle_no < self._liquidation_cooldown_until:
            return None

        positions = self.portfolio_engine.snapshot()
        if not positions:
            return None

        # Trigger when exposure pressure already exists from recent blocks or current portfolio saturation.
        exposure_pressure = (
            self._risk_block_streak >= 1
            and self._is_exposure_block(self._last_risk_block_reason)
        ) or (self._portfolio_exposure_pct() >= max(1.0, self.risk_engine.max_portfolio_risk * 0.9))
        if not exposure_pressure:
            return None

        symbol, pos = max(
            positions.items(),
            key=lambda kv: self.portfolio_engine.symbol_exposure_notional(kv[0], self.state.latest_prices),
        )
        net_qty = int(pos.get("net_qty", 0))
        if net_qty == 0:
            return None
        price = float(self.state.latest_prices.get(symbol, pos.get("avg_price", 0.0)))
        if price <= 0:
            return None

        side = "SELL" if net_qty > 0 else "BUY"
        qty = max(1, int(abs(net_qty) * max(0.05, min(self.config.liquidation_assist_close_fraction, 1.0))))
        qty = min(qty, abs(net_qty))
        return {
            "strategy_id": "rebalance_assist_v1",
            "strategy_stage": "RISK_REDUCTION",
            "shadow_mode": False,
            "symbol": symbol,
            "side": side,
            "price": price,
            "confidence": 1.0,
            "volatility": 0.5,
            "trade_type": "RISK_REBALANCE",
            "memory_bias": 0.0,
            "forced_qty": qty,
            "rebalance_assist": True,
            "regime": regime,
        }

    def _track_risk_block(self, reason):
        if self._last_risk_block_reason == reason:
            self._risk_block_streak += 1
        else:
            self._last_risk_block_reason = reason
            self._risk_block_streak = 1

    def _reset_risk_block_state(self):
        self._risk_block_streak = 0
        self._last_risk_block_reason = ""

    def _maybe_liquidation_assist(self, trigger_reason, regime):
        if not self.config.liquidation_assist_enabled:
            return None
        if self._cycle_no < self._liquidation_cooldown_until:
            return None
        if self._risk_block_streak < max(1, self.config.liquidation_assist_trigger_streak):
            return None

        positions = self.portfolio_engine.snapshot()
        if not positions:
            return None

        symbol, pos = max(
            positions.items(),
            key=lambda kv: self.portfolio_engine.symbol_exposure_notional(kv[0], self.state.latest_prices),
        )
        net_qty = int(pos.get("net_qty", 0))
        if net_qty == 0:
            return None

        close_fraction = max(0.05, min(self.config.liquidation_assist_close_fraction, 1.0))
        qty = max(1, int(abs(net_qty) * close_fraction))
        qty = min(qty, abs(net_qty))
        side = "SELL" if net_qty > 0 else "BUY"
        intended_price = float(self.state.latest_prices.get(symbol, pos.get("avg_price", 0.0)))
        if intended_price <= 0:
            return None

        prev_equity = self.state.equity
        prev_realized = float(self.state.realized_pnl)
        volatility = 0.5
        slippage_bps = self._compute_slippage_bps({"volatility": volatility})
        fill_price = self._apply_slippage(intended_price, side, slippage_bps)
        fill_notional = quantize(fill_price * qty, 4)
        fee = quantize(fill_notional * (self.config.broker_fee_bps / 10000.0), 4)

        order = self.broker.place_order(
            symbol=symbol,
            side=side,
            qty=qty,
            price=fill_price,
            fee=fee,
            meta={
                "strategy_id": "liquidation_assist_v1",
                "trade_type": "RISK_REDUCTION",
                "regime": regime,
                "trigger_reason": trigger_reason,
            },
        )

        if self.reconciler:
            self.reconciler.reconcile(latest_prices=self.state.latest_prices)
            realized_pnl = float(self.state.realized_pnl) - prev_realized
            if abs(realized_pnl) < 1e-8:
                realized_pnl = float(order.get("realized_pnl", 0.0))
        else:
            fill_result = self.portfolio_engine.apply_fill(symbol=symbol, side=side, qty=qty, price=fill_price)
            realized_pnl = float(fill_result["realized_pnl"])
            self.state.apply_fill_accounting(
                side=side,
                fill_notional=fill_notional,
                fee=fee,
                realized_pnl=realized_pnl,
            )
            self.state.mark_to_market(self.portfolio_engine)

        cycle_pnl = quantize(self.state.equity - prev_equity, 4)
        trade_record = {
            "strategy_id": "liquidation_assist_v1",
            "strategy_stage": "RISK_REDUCTION",
            "shadow_mode": False,
            "symbol": symbol,
            "asset_class": self._asset_class(symbol),
            "regime": regime,
            "trade_type": "RISK_REDUCTION",
            "side": side,
            "qty": qty,
            "status": order.get("status", "FILLED"),
            "price": quantize(fill_price, 4),
            "intended_price": quantize(intended_price, 4),
            "slippage_bps": quantize(slippage_bps, 4),
            "confidence": 1.0,
            "memory_bias": 0.0,
            "fee": fee,
            "realized_pnl": quantize(realized_pnl, 4),
            "closed_trade": bool(abs(realized_pnl) > 0.0),
            "unrealized_pnl": quantize(self.state.unrealized_pnl, 4),
            "cycle_pnl": cycle_pnl,
            "equity": quantize(self.state.equity, 2),
            "cash_balance": quantize(self.state.cash_balance, 2),
            "liquidation_trigger": trigger_reason,
        }
        self.state.record_trade(trade_record)
        self._liquidation_cooldown_until = self._cycle_no + 3
        self._reset_risk_block_state()

        return {
            "status": "TRADE",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "pnl": cycle_pnl,
            "equity": trade_record["equity"],
            "strategy_id": "liquidation_assist_v1",
            "strategy_stage": "RISK_REDUCTION",
            "shadow_mode": False,
            "trade_type": "RISK_REDUCTION",
            "regime": regime,
            "confidence": 1.0,
            "price": trade_record["price"],
            "liquidation_assist": True,
        }
