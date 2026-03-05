"""
indicator_library.py
Vectorized indicator library for the Quant Ecosystem feature pipeline.
All functions accept numpy arrays and return numpy arrays.
Designed for high-throughput batch computation across thousands of symbols.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Trend Indicators
# ---------------------------------------------------------------------------

def ema(close: NDArray[np.float64], period: int) -> NDArray[np.float64]:
    """Exponential Moving Average — vectorized using cumulative weights."""
    if len(close) < period:
        return np.full(len(close), np.nan)
    alpha = 2.0 / (period + 1)
    out = np.empty(len(close), dtype=np.float64)
    out[:period - 1] = np.nan
    out[period - 1] = np.mean(close[:period])
    for i in range(period, len(close)):
        out[i] = close[i] * alpha + out[i - 1] * (1.0 - alpha)
    return out


def sma(close: NDArray[np.float64], period: int) -> NDArray[np.float64]:
    """Simple Moving Average using cumsum for O(n) performance."""
    if len(close) < period:
        return np.full(len(close), np.nan)
    cumsum = np.cumsum(np.insert(close, 0, 0.0))
    out = np.empty(len(close), dtype=np.float64)
    out[:period - 1] = np.nan
    out[period - 1:] = (cumsum[period:] - cumsum[:len(close) - period + 1]) / period
    return out


def dema(close: NDArray[np.float64], period: int) -> NDArray[np.float64]:
    """Double EMA — removes lag."""
    e1 = ema(close, period)
    e2 = ema(e1, period)
    return 2.0 * e1 - e2


def tema(close: NDArray[np.float64], period: int) -> NDArray[np.float64]:
    """Triple EMA."""
    e1 = ema(close, period)
    e2 = ema(e1, period)
    e3 = ema(e2, period)
    return 3.0 * e1 - 3.0 * e2 + e3


def wma(close: NDArray[np.float64], period: int) -> NDArray[np.float64]:
    """Weighted Moving Average."""
    weights = np.arange(1, period + 1, dtype=np.float64)
    weight_sum = weights.sum()
    out = np.full(len(close), np.nan)
    for i in range(period - 1, len(close)):
        out[i] = np.dot(close[i - period + 1 : i + 1], weights) / weight_sum
    return out


def hma(close: NDArray[np.float64], period: int) -> NDArray[np.float64]:
    """Hull Moving Average — reduces lag significantly."""
    half = max(1, period // 2)
    sqrt_p = max(1, int(np.sqrt(period)))
    wma_half = wma(close, half)
    wma_full = wma(close, period)
    diff = 2.0 * wma_half - wma_full
    return wma(diff, sqrt_p)


def donchian(high: NDArray[np.float64], low: NDArray[np.float64],
             period: int) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Donchian Channel — upper, mid, lower."""
    upper = np.full(len(high), np.nan)
    lower = np.full(len(low), np.nan)
    for i in range(period - 1, len(high)):
        upper[i] = np.max(high[i - period + 1 : i + 1])
        lower[i] = np.min(low[i - period + 1 : i + 1])
    mid = (upper + lower) / 2.0
    return upper, mid, lower


# ---------------------------------------------------------------------------
# Momentum Indicators
# ---------------------------------------------------------------------------

def rsi(close: NDArray[np.float64], period: int = 14) -> NDArray[np.float64]:
    """Wilder RSI — vectorized."""
    if len(close) < period + 1:
        return np.full(len(close), np.nan)
    delta = np.diff(close)
    gains = np.clip(delta, 0.0, None)
    losses = np.clip(-delta, 0.0, None)
    out = np.full(len(close), np.nan)
    avg_gain = gains[:period].mean()
    avg_loss = losses[:period].mean()
    for i in range(period, len(close) - 1):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss > 0 else 10.0
        out[i + 1] = 100.0 - (100.0 / (1.0 + rs))
    return out


def macd(close: NDArray[np.float64], fast: int = 12, slow: int = 26,
         signal: int = 9) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """MACD — returns (macd_line, signal_line, histogram)."""
    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def stochastic(high: NDArray[np.float64], low: NDArray[np.float64],
               close: NDArray[np.float64], k_period: int = 14,
               d_period: int = 3) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Stochastic Oscillator."""
    k = np.full(len(close), np.nan)
    for i in range(k_period - 1, len(close)):
        highest = np.max(high[i - k_period + 1 : i + 1])
        lowest = np.min(low[i - k_period + 1 : i + 1])
        denom = highest - lowest
        k[i] = 0.0 if denom == 0 else (close[i] - lowest) / denom * 100.0
    d = sma(k, d_period)
    return k, d


def cci(high: NDArray[np.float64], low: NDArray[np.float64],
        close: NDArray[np.float64], period: int = 20) -> NDArray[np.float64]:
    """Commodity Channel Index."""
    tp = (high + low + close) / 3.0
    out = np.full(len(close), np.nan)
    for i in range(period - 1, len(close)):
        window = tp[i - period + 1 : i + 1]
        mean = window.mean()
        mad = np.abs(window - mean).mean()
        out[i] = 0.0 if mad == 0 else (tp[i] - mean) / (0.015 * mad)
    return out


def roc(close: NDArray[np.float64], period: int = 10) -> NDArray[np.float64]:
    """Rate of Change."""
    out = np.full(len(close), np.nan)
    for i in range(period, len(close)):
        prev = close[i - period]
        out[i] = ((close[i] - prev) / prev * 100.0) if prev != 0 else 0.0
    return out


def williams_r(high: NDArray[np.float64], low: NDArray[np.float64],
               close: NDArray[np.float64], period: int = 14) -> NDArray[np.float64]:
    """Williams %R."""
    out = np.full(len(close), np.nan)
    for i in range(period - 1, len(close)):
        hh = np.max(high[i - period + 1 : i + 1])
        ll = np.min(low[i - period + 1 : i + 1])
        denom = hh - ll
        out[i] = 0.0 if denom == 0 else (hh - close[i]) / denom * -100.0
    return out


# ---------------------------------------------------------------------------
# Volatility Indicators
# ---------------------------------------------------------------------------

def atr(high: NDArray[np.float64], low: NDArray[np.float64],
        close: NDArray[np.float64], period: int = 14) -> NDArray[np.float64]:
    """Average True Range — Wilder smoothing."""
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum.reduce([
        high - low,
        np.abs(high - prev_close),
        np.abs(low - prev_close),
    ])
    out = np.full(len(close), np.nan)
    if len(tr) < period:
        return out
    out[period - 1] = tr[:period].mean()
    alpha = 1.0 / period
    for i in range(period, len(tr)):
        out[i] = tr[i] * alpha + out[i - 1] * (1.0 - alpha)
    return out


def bollinger_bands(close: NDArray[np.float64], period: int = 20,
                    std_dev: float = 2.0) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Bollinger Bands — upper, mid (SMA), lower."""
    mid = sma(close, period)
    std = np.full(len(close), np.nan)
    for i in range(period - 1, len(close)):
        std[i] = np.std(close[i - period + 1 : i + 1], ddof=0)
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return upper, mid, lower


def keltner_channels(high: NDArray[np.float64], low: NDArray[np.float64],
                     close: NDArray[np.float64], ema_period: int = 20,
                     atr_period: int = 10, multiplier: float = 2.0
                     ) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Keltner Channels."""
    mid = ema(close, ema_period)
    a = atr(high, low, close, atr_period)
    upper = mid + multiplier * a
    lower = mid - multiplier * a
    return upper, mid, lower


def historical_volatility(close: NDArray[np.float64],
                          period: int = 21, annualize: bool = True) -> NDArray[np.float64]:
    """Log-return historical volatility."""
    log_ret = np.log(close[1:] / np.where(close[:-1] == 0, 1e-10, close[:-1]))
    log_ret = np.insert(log_ret, 0, np.nan)
    out = np.full(len(close), np.nan)
    for i in range(period, len(close)):
        out[i] = np.std(log_ret[i - period + 1 : i + 1], ddof=1)
    if annualize:
        out *= np.sqrt(252)
    return out


def true_range(high: NDArray[np.float64], low: NDArray[np.float64],
               close: NDArray[np.float64]) -> NDArray[np.float64]:
    """True Range — raw, single bar."""
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    return np.maximum.reduce([
        high - low,
        np.abs(high - prev_close),
        np.abs(low - prev_close),
    ])


# ---------------------------------------------------------------------------
# Volume Indicators
# ---------------------------------------------------------------------------

def vwap(high: NDArray[np.float64], low: NDArray[np.float64],
         close: NDArray[np.float64], volume: NDArray[np.float64]) -> NDArray[np.float64]:
    """Cumulative VWAP (resets each call — pass session data)."""
    tp = (high + low + close) / 3.0
    cum_tp_vol = np.cumsum(tp * volume)
    cum_vol = np.cumsum(volume)
    safe_vol = np.where(cum_vol == 0, 1e-10, cum_vol)
    return cum_tp_vol / safe_vol


def obv(close: NDArray[np.float64], volume: NDArray[np.float64]) -> NDArray[np.float64]:
    """On-Balance Volume."""
    direction = np.sign(np.diff(close))
    direction = np.insert(direction, 0, 0.0)
    return np.cumsum(direction * volume)


def cmf(high: NDArray[np.float64], low: NDArray[np.float64],
        close: NDArray[np.float64], volume: NDArray[np.float64],
        period: int = 21) -> NDArray[np.float64]:
    """Chaikin Money Flow."""
    denom = high - low
    mf_multiplier = np.where(denom == 0, 0.0, (2.0 * close - low - high) / denom)
    mf_volume = mf_multiplier * volume
    out = np.full(len(close), np.nan)
    for i in range(period - 1, len(close)):
        vol_sum = volume[i - period + 1 : i + 1].sum()
        out[i] = 0.0 if vol_sum == 0 else mf_volume[i - period + 1 : i + 1].sum() / vol_sum
    return out


def volume_zscore(volume: NDArray[np.float64], period: int = 20) -> NDArray[np.float64]:
    """Volume z-score vs rolling window."""
    out = np.full(len(volume), np.nan)
    for i in range(period - 1, len(volume)):
        window = volume[i - period + 1 : i + 1]
        mean, std = window.mean(), window.std(ddof=1)
        out[i] = 0.0 if std == 0 else (volume[i] - mean) / std
    return out


# ---------------------------------------------------------------------------
# Statistical / Factor Indicators
# ---------------------------------------------------------------------------

def zscore(series: NDArray[np.float64], period: int = 20) -> NDArray[np.float64]:
    """Rolling z-score."""
    out = np.full(len(series), np.nan)
    for i in range(period - 1, len(series)):
        window = series[i - period + 1 : i + 1]
        mean, std = window.mean(), window.std(ddof=1)
        out[i] = 0.0 if std == 0 else (series[i] - mean) / std
    return out


def rolling_correlation(x: NDArray[np.float64], y: NDArray[np.float64],
                         period: int = 20) -> NDArray[np.float64]:
    """Rolling Pearson correlation."""
    out = np.full(len(x), np.nan)
    for i in range(period - 1, len(x)):
        xw = x[i - period + 1 : i + 1]
        yw = y[i - period + 1 : i + 1]
        if np.std(xw) == 0 or np.std(yw) == 0:
            out[i] = 0.0
        else:
            out[i] = float(np.corrcoef(xw, yw)[0, 1])
    return out


def rolling_beta(asset_rets: NDArray[np.float64], bench_rets: NDArray[np.float64],
                 period: int = 60) -> NDArray[np.float64]:
    """Rolling beta vs benchmark."""
    out = np.full(len(asset_rets), np.nan)
    for i in range(period - 1, len(asset_rets)):
        aw = asset_rets[i - period + 1 : i + 1]
        bw = bench_rets[i - period + 1 : i + 1]
        var_b = np.var(bw, ddof=1)
        out[i] = 0.0 if var_b == 0 else float(np.cov(aw, bw, ddof=1)[0, 1] / var_b)
    return out


def hurst_exponent(series: NDArray[np.float64], min_lag: int = 2,
                   max_lag: int = 20) -> float:
    """Hurst exponent — classify mean-reversion vs trend vs random walk."""
    lags = range(min_lag, max_lag + 1)
    tau = [np.std(np.subtract(series[lag:], series[:-lag])) for lag in lags]
    if len(tau) < 2 or max(tau) == 0:
        return 0.5
    poly = np.polyfit(np.log(list(lags)), np.log(tau), 1)
    return float(poly[0])


def log_returns(close: NDArray[np.float64]) -> NDArray[np.float64]:
    """Log returns array."""
    safe_prev = np.where(close[:-1] == 0, 1e-10, close[:-1])
    ret = np.log(close[1:] / safe_prev)
    return np.insert(ret, 0, 0.0)


def sharpe_rolling(returns: NDArray[np.float64], period: int = 60,
                   rf: float = 0.0) -> NDArray[np.float64]:
    """Rolling annualized Sharpe."""
    out = np.full(len(returns), np.nan)
    for i in range(period - 1, len(returns)):
        w = returns[i - period + 1 : i + 1]
        std = np.std(w, ddof=1)
        if std == 0:
            out[i] = 0.0
        else:
            out[i] = (np.mean(w) - rf) / std * np.sqrt(252)
    return out


def max_drawdown_rolling(returns: NDArray[np.float64], period: int = 60) -> NDArray[np.float64]:
    """Rolling max drawdown as percentage."""
    out = np.full(len(returns), np.nan)
    for i in range(period - 1, len(returns)):
        w = returns[i - period + 1 : i + 1]
        equity = np.cumprod(1.0 + w)
        peak = np.maximum.accumulate(equity)
        dd = (peak - equity) / np.where(peak == 0, 1e-10, peak)
        out[i] = float(np.max(dd) * 100.0)
    return out


# ---------------------------------------------------------------------------
# Cross-sectional
# ---------------------------------------------------------------------------

def cross_section_rank(matrix: NDArray[np.float64]) -> NDArray[np.float64]:
    """
    Rank each column (symbol) relative to peers at each timestep.
    matrix shape: (time, symbols)
    Returns rank percentile in [0, 1].
    """
    from scipy.stats import rankdata
    ranked = np.apply_along_axis(
        lambda row: rankdata(row, method="average") / len(row), axis=1, arr=matrix
    )
    return ranked


def cross_section_zscore(matrix: NDArray[np.float64]) -> NDArray[np.float64]:
    """Cross-sectional z-score: demean and scale by std across symbols at each t."""
    mean = np.nanmean(matrix, axis=1, keepdims=True)
    std = np.nanstd(matrix, axis=1, ddof=1, keepdims=True)
    safe_std = np.where(std == 0, 1.0, std)
    return (matrix - mean) / safe_std


# ---------------------------------------------------------------------------
# Utility: batch compute over price matrix
# ---------------------------------------------------------------------------

def batch_rsi(close_matrix: NDArray[np.float64], period: int = 14) -> NDArray[np.float64]:
    """Apply RSI to each column (symbol) in a (time, symbols) matrix."""
    T, N = close_matrix.shape
    out = np.full((T, N), np.nan)
    for j in range(N):
        out[:, j] = rsi(close_matrix[:, j], period)
    return out


def batch_ema(close_matrix: NDArray[np.float64], period: int) -> NDArray[np.float64]:
    """Apply EMA to each column in a (time, symbols) matrix."""
    T, N = close_matrix.shape
    out = np.full((T, N), np.nan)
    for j in range(N):
        out[:, j] = ema(close_matrix[:, j], period)
    return out
