You are building strategies for Quant Ecosystem 3.0.

Strategies must follow institutional quant standards.

Every strategy must return:

{
    "signal": "BUY | SELL | NONE",
    "confidence": float,
    "stop_loss_pct": float,
    "take_profit_pct": float
}

Strategies must NEVER place trades directly.
Only return signals.

Execution is handled by ExecutionRouter.

------------------------------------------------

STRATEGY TYPES REQUIRED

The system must maintain multiple independent strategy classes.

1 Trend Following
2 Mean Reversion
3 Momentum
4 Breakout
5 Volatility Expansion
6 Statistical Arbitrage
7 Intraday Microstructure

Each strategy must work independently.

------------------------------------------------

REGIME FILTER

Before producing signals strategies must check:

market