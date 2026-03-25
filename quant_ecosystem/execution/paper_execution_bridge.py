import random
import time


class PaperExecutionBridge:

    def __init__(self, portfolio_engine, alpha_book):

        self.portfolio = portfolio_engine
        self.alpha_book = alpha_book

        self.last_trade_time = {}
        self.alpha_score = {}

        self.MAX_ACTIVE_TRADES = 3
        self.TRADE_COOLDOWN = 3  # cycles

    # -----------------------------------------
    # SIGNAL INTELLIGENCE
    # -----------------------------------------

    def _alpha_signal(self, alpha):

        confidence = getattr(alpha, "alpha_confidence", 0.5)

        # confidence gate
        if confidence < 0.4:
            return None

        if alpha.family == "breakout":
            return "BUY"

        if alpha.family == "ema_stack":
            return "BUY"

        if alpha.family == "pullback_trend":
            return random.choice(["BUY", "SELL"])

        return None

    # -----------------------------------------
    # EXECUTION LOOP
    # -----------------------------------------

    def route_signals(self, snapshot):

        active_positions = len(self.portfolio.positions)

        for g in self.alpha_book.live_alphas:

            if active_positions >= self.MAX_ACTIVE_TRADES:
                break

            last_time = self.last_trade_time.get(g)

            if last_time is not None and (snapshot.get("cycle_id",0) - last_time) < self.TRADE_COOLDOWN:
                continue

            side = self._alpha_signal(g)

            if side is None:
                continue

            price = random.uniform(100, 200)
            qty = 1

            weight = getattr(g, "capital_weight", 0.1)

            # map weight → position size
            qty = max(1, int(weight * 10))

            # suppress ultra weak alpha
            if weight < 0.05:
                return

            result = self.portfolio.apply_fill(
                symbol=g.symbol,
                side=side,
                qty=qty,
                price=price
            )

            pnl = result["realized_pnl"]

            # feedback scoring
            self.alpha_score[g] = self.alpha_score.get(g, 0) + pnl

            self.last_trade_time[g] = snapshot.get("cycle_id",0)

            print(
                f"[EXECUTE] {side} {g.family} {g.symbol} "
                f"price={price:.2f} pnl={pnl:.2f} score={self.alpha_score[g]:.2f}"
            )

            active_positions += 1

            pnl = getattr(g, "realized_pnl", 0.0)
            
            print(
                f"[EXECUTE] {side} {g.family} {g.symbol} "
                f"qty={qty} weight={weight:.2f} pnl={pnl:.2f}"
            )