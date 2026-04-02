"""
factor_dataset_builder.py
==========================
Builds Fama-French-style factor datasets for quantitative research.

Factors computed:
  Price-based:    momentum_1m, momentum_3m, momentum_12m, reversal_1w
  Risk:           realized_vol_20d, realized_vol_5d, beta_vs_nifty, max_drawdown_20d
  Technical:      rsi_14, adx_14, bb_percentile, atr_pct
  Microstructure: amihud_illiquidity, volume_trend, relative_volume
  Cross-section:  cs_momentum_rank, cs_vol_rank, cs_return_rank

Output is a structured factor matrix suitable for:
  - Portfolio construction (risk parity, factor tilt)
  - Alpha signal generation (factor scoring)
  - Regime detection (factor dispersion, correlation)
  - Overfitting detection in backtests

Usage:
    builder = FactorDatasetBuilder()
    factors = builder.compute(
        datasets={"SBIN": arr, "BTCUSDT": arr2},
        lookback=252,
    )
    # factors: Dict[str, Dict[str, float]]  {symbol: {factor_name: value}}
    factor_matrix = builder.to_matrix(factors)  # (N_symbols, N_factors)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Per-symbol factor computation (pure, vectorised)
# ---------------------------------------------------------------------------

def _safe_last(arr: np.ndarray, default: float = np.nan) -> float:
    return float(arr[-1]) if len(arr) > 0 and not np.isnan(arr[-1]) else default


def compute_momentum_factors(close: np.ndarray) -> Dict[str, float]:
    """Price momentum at multiple horizons."""
    n = len(close)
    factors: Dict[str, float] = {}

    for label, lookback in [("1w", 5), ("1m", 21), ("3m", 63), ("6m", 126), ("12m", 252)]:
        if n > lookback:
            ret = (close[-1] - close[-lookback]) / (close[-lookback] + 1e-9)
            factors[f"mom_{label}"] = round(float(ret), 6)
        else:
            factors[f"mom_{label}"] = np.nan

    # 1-week reversal (short-term mean reversion signal)
    if n > 5:
        factors["reversal_1w"] = -factors.get("mom_1w", 0.0)

    return factors


def compute_risk_factors(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    volume: np.ndarray,
    benchmark: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """Risk and volatility factors."""
    factors: Dict[str, float] = {}
    n = len(close)

    # Realized volatility
    if n > 5:
        log_ret = np.diff(np.log(close + 1e-9))
        factors["rvol_5d"]  = round(float(log_ret[-5:].std()  * np.sqrt(252)), 6) if n > 5  else np.nan
        factors["rvol_20d"] = round(float(log_ret[-20:].std() * np.sqrt(252)), 6) if n > 20 else np.nan
        factors["rvol_60d"] = round(float(log_ret[-60:].std() * np.sqrt(252)), 6) if n > 60 else np.nan

        # Ratio of short-to-long vol (vol regime indicator)
        if not np.isnan(factors.get("rvol_5d", np.nan)) and not np.isnan(factors.get("rvol_60d", np.nan)):
            factors["vol_ratio_5_60"] = round(
                factors["rvol_5d"] / (factors["rvol_60d"] + 1e-9), 4
            )

    # Max drawdown over 20 days
    if n > 20:
        roll_max = np.maximum.accumulate(close[-20:])
        dd = (close[-20:] - roll_max) / (roll_max + 1e-9)
        factors["max_dd_20d"] = round(float(abs(dd.min())), 6)

    # Beta vs benchmark
    if benchmark is not None and n > 20:
        min_len = min(n, len(benchmark))
        asset_ret = np.diff(np.log(close[-min_len:] + 1e-9))
        bench_ret = np.diff(np.log(benchmark[-min_len:] + 1e-9))
        if len(asset_ret) > 5 and bench_ret.std() > 1e-9:
            cov = np.cov(asset_ret, bench_ret)[0, 1]
            factors["beta"] = round(float(cov / (bench_ret.var() + 1e-9)), 4)

    return factors


def compute_technical_factors(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    volume: np.ndarray,
) -> Dict[str, float]:
    """Technical indicator-based factors."""
    factors: Dict[str, float] = {}
    n = len(close)

    # RSI-14
    if n > 15:
        delta = np.diff(close)
        gain = np.where(delta > 0, delta, 0.0)
        loss = np.where(delta < 0, -delta, 0.0)
        avg_g = gain[-14:].mean()
        avg_l = loss[-14:].mean()
        rs = avg_g / (avg_l + 1e-9)
        factors["rsi_14"] = round(float(100 - 100 / (1 + rs)), 4)

    # Bollinger percentile (where is price within the band)
    if n > 20:
        mu = close[-20:].mean()
        sigma = close[-20:].std()
        if sigma > 0:
            bb_z = (close[-1] - mu) / sigma
            # Map to [0, 1]: -2std = 0, +2std = 1
            factors["bb_pct"] = round(float(np.clip((bb_z + 2) / 4, 0, 1)), 4)

    # ATR as % of price
    if n > 14:
        tr_list = []
        for i in range(1, min(15, n)):
            hl = high[-i] - low[-i]
            hc = abs(high[-i] - close[-i-1]) if i < n-1 else hl
            lc = abs(low[-i]  - close[-i-1]) if i < n-1 else hl
            tr_list.append(max(hl, hc, lc))
        atr = float(np.mean(tr_list))
        factors["atr_pct"] = round(atr / (close[-1] + 1e-9), 6)

    # Relative volume
    if n > 20:
        avg_vol = volume[-20:].mean()
        factors["rel_volume"] = round(float(volume[-1] / (avg_vol + 1e-9)), 4)

    # Price vs 52-week high/low
    if n >= 252:
        hi_52 = high[-252:].max()
        lo_52 = low[-252:].min()
        rng = hi_52 - lo_52
        factors["pct_52w_high"] = round(float((close[-1] - lo_52) / (rng + 1e-9)), 4)

    return factors


def compute_microstructure_factors(
    close: np.ndarray,
    volume: np.ndarray,
) -> Dict[str, float]:
    """Market microstructure and liquidity factors."""
    factors: Dict[str, float] = {}
    n = len(close)

    # Amihud illiquidity (|return| / dollar volume proxy)
    if n > 20:
        returns = abs(np.diff(np.log(close[-21:] + 1e-9)))
        dollar_vol = (close[-20:] * volume[-20:]).clip(1)
        amihud = float(np.mean(returns / dollar_vol))
        factors["amihud"] = round(amihud * 1e6, 6)  # scaled for readability

    # Volume trend (linear slope over 20 days, normalised)
    if n > 20:
        x = np.arange(20, dtype=np.float64)
        y = volume[-20:].astype(np.float64)
        if y.std() > 0:
            slope = float(np.polyfit(x, y, 1)[0])
            factors["vol_trend"] = round(slope / (y.mean() + 1e-9), 6)

    # Price autocorrelation (mean-reversion vs momentum)
    if n > 20:
        ret = np.diff(np.log(close[-21:] + 1e-9))
        if len(ret) > 2 and ret.std() > 1e-9:
            autocorr = float(np.corrcoef(ret[:-1], ret[1:])[0, 1])
            factors["autocorr_1"] = round(autocorr, 4)

    return factors


# ---------------------------------------------------------------------------
# Cross-sectional (universe-level) factors
# ---------------------------------------------------------------------------

def compute_cs_factors(
    all_factors: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    """
    Add cross-sectional rank factors across the universe.
    E.g., cs_mom_rank = momentum rank within universe [0..1].
    """
    if len(all_factors) < 2:
        return all_factors

    cs_vars = ["mom_1m", "mom_3m", "rvol_20d", "rsi_14", "rel_volume"]

    for var in cs_vars:
        vals = {
            sym: f.get(var, np.nan)
            for sym, f in all_factors.items()
        }
        valid = {s: v for s, v in vals.items() if not np.isnan(v)}
        if len(valid) < 2:
            continue
        sorted_syms = sorted(valid.keys(), key=lambda s: valid[s])
        n = len(sorted_syms)
        for rank, sym in enumerate(sorted_syms):
            all_factors[sym][f"cs_rank_{var}"] = round(rank / (n - 1), 4)

    return all_factors


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

@dataclass
class FactorSnapshot:
    """All factors for a single symbol."""
    symbol:    str
    factors:   Dict[str, float]
    timestamp: float = field(default_factory=time.time)

    def get(self, factor_name: str, default: float = np.nan) -> float:
        return self.factors.get(factor_name, default)

    def to_dict(self) -> Dict[str, Any]:
        return {"symbol": self.symbol, "factors": self.factors, "timestamp": self.timestamp}


class FactorDatasetBuilder:
    """
    Builds rich factor datasets for the research pipeline.

    Computes 40+ factors per symbol including momentum, risk,
    technical, microstructure, and cross-sectional ranks.

    Integration with ResearchPipelineManager:
        datasets = research_dataset_builder.build(symbols, timeframe)
        factors = factor_dataset_builder.compute(datasets)
        # Inject into feature store or use directly in alpha scoring

    Integration with SignalQualityEngine:
        factor_z = builder.factor_zscore("SBIN", "mom_1m", lookback=252)
        # Use for signal quality assessment
    """

    def __init__(
        self,
        benchmark_symbol: Optional[str] = None,
        benchmark_data: Optional[np.ndarray] = None, **kwargs
    ) -> None:
        self.benchmark_symbol = benchmark_symbol
        self.benchmark_data = benchmark_data  # shape (N, 5) OHLCV
        self._snapshots: Dict[str, FactorSnapshot] = {}

    def compute(
        self,
        datasets: Dict[str, np.ndarray],
        lookback: int = 252,
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute all factors for each symbol.
        datasets: {symbol: array shape (N, 5)}
        Returns: {symbol: {factor_name: value}}
        """
        all_factors: Dict[str, Dict[str, float]] = {}

        benchmark = None
        if self.benchmark_data is not None:
            benchmark = self.benchmark_data[:, 3]  # close
        elif self.benchmark_symbol and self.benchmark_symbol in datasets:
            benchmark = datasets[self.benchmark_symbol][:, 3]

        for sym, arr in datasets.items():
            if arr is None or len(arr) < 20:
                continue
            arr = arr[-lookback:]
            open_ = arr[:, 0];  high = arr[:, 1]
            low   = arr[:, 2];  close = arr[:, 3];  volume = arr[:, 4]

            factors: Dict[str, float] = {}
            factors.update(compute_momentum_factors(close))
            factors.update(compute_risk_factors(close, high, low, volume, benchmark))
            factors.update(compute_technical_factors(close, high, low, volume))
            factors.update(compute_microstructure_factors(close, volume))

            all_factors[sym] = factors

        # Cross-sectional enrichment
        all_factors = compute_cs_factors(all_factors)

        # Store snapshots
        for sym, f in all_factors.items():
            self._snapshots[sym] = FactorSnapshot(symbol=sym, factors=f)

        return all_factors

    def to_matrix(
        self,
        factors: Dict[str, Dict[str, float]],
        factor_names: Optional[List[str]] = None,
    ) -> Tuple[np.ndarray, List[str], List[str]]:
        """
        Convert factor dict to matrix form.
        Returns (matrix shape (N_symbols, N_factors), symbols, factor_names).
        """
        symbols = sorted(factors.keys())
        if not symbols:
            return np.array([]), [], []

        # Collect common factor names
        if factor_names is None:
            all_names: set = set()
            for f in factors.values():
                all_names.update(f.keys())
            factor_names = sorted(all_names)

        matrix = np.full((len(symbols), len(factor_names)), np.nan)
        for i, sym in enumerate(symbols):
            for j, fname in enumerate(factor_names):
                val = factors[sym].get(fname, np.nan)
                if not np.isnan(val):
                    matrix[i, j] = val

        return matrix, symbols, factor_names

    def get_snapshot(self, symbol: str) -> Optional[FactorSnapshot]:
        return self._snapshots.get(symbol)

    def factor_zscore(
        self,
        symbol: str,
        factor_name: str,
        all_factors: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> float:
        """Return cross-sectional z-score of a factor for a given symbol."""
        source = all_factors or {s: snap.factors for s, snap in self._snapshots.items()}
        vals = np.array([
            f.get(factor_name, np.nan) for f in source.values()
            if not np.isnan(f.get(factor_name, np.nan))
        ])
        if len(vals) < 2:
            return 0.0
        sym_val = source.get(symbol, {}).get(factor_name, np.nan)
        if np.isnan(sym_val):
            return 0.0
        mu, sigma = vals.mean(), vals.std()
        return float((sym_val - mu) / (sigma + 1e-9))

    def top_symbols_by_factor(
        self,
        factor_name: str,
        n: int = 10,
        ascending: bool = False,
        all_factors: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> List[Tuple[str, float]]:
        """Return top-N symbols ranked by a specific factor."""
        source = all_factors or {s: snap.factors for s, snap in self._snapshots.items()}
        ranked = [
            (sym, f.get(factor_name, np.nan))
            for sym, f in source.items()
            if not np.isnan(f.get(factor_name, np.nan))
        ]
        ranked.sort(key=lambda x: x[1], reverse=not ascending)
        return ranked[:n]
