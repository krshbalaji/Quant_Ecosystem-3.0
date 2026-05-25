from quant_ecosystem.research import (
    TechnicalSignal,
    signal_confidence_engine,
)


class TechnicalSignalEngine:

    def sma(
        self,
        series,
        period,
    ):
        if (
            not series
            or len(series) < period
        ):
            return 0.0

        window = series[-period:]

        return sum(window) / period

    def ema(
        self,
        series,
        period,
    ):
        if (
            not series
            or len(series) < period
        ):
            return 0.0

        multiplier = (
            2 / (period + 1)
        )

        ema_value = sum(
            series[:period]
        ) / period

        for price in series[period:]:
            ema_value = (
                (price - ema_value)
                * multiplier
            ) + ema_value

        return ema_value

    def sma_crossover(
        self,
        symbol,
        series,
        fast=10,
        slow=20,
    ):
        fast_sma = self.sma(
            series,
            fast,
        )

        slow_sma = self.sma(
            series,
            slow,
        )

        direction = (
            "LONG"
            if fast_sma > slow_sma
            else "SHORT"
        )

        confidence = abs(
            fast_sma - slow_sma
        )

        return TechnicalSignal(
            symbol=symbol,
            signal_type="SMA_CROSSOVER",
            direction=direction,
            confidence=signal_confidence_engine.normalize(
                confidence
            ),
        )

    def ema_trend(
        self,
        symbol,
        series,
        fast=12,
        slow=26,
    ):
        fast_ema = self.ema(
            series,
            fast,
        )

        slow_ema = self.ema(
            series,
            slow,
        )

        direction = (
            "LONG"
            if fast_ema > slow_ema
            else "SHORT"
        )

        confidence = abs(
            fast_ema - slow_ema
        )

        return TechnicalSignal(
            symbol=symbol,
            signal_type="EMA_TREND",
            direction=direction,
            confidence=signal_confidence_engine.normalize(
                confidence
            ),
        )

    def breakout(
        self,
        symbol,
        series,
        lookback=20,
    ):
        if len(series) < lookback:
            return None

        high = max(
            series[-lookback:-1]
        )

        last = series[-1]

        direction = (
            "LONG"
            if last > high
            else "NEUTRAL"
        )

        confidence = (
            ((last - high) / high) * 100
            if high else 0
        )

        return TechnicalSignal(
            symbol=symbol,
            signal_type="BREAKOUT",
            direction=direction,
            confidence=signal_confidence_engine.normalize(
                confidence
            ),
        )

    def momentum(
        self,
        symbol,
        series,
        lookback=10,
    ):
        if len(series) <= lookback:
            return None

        start = series[-lookback - 1]
        end = series[-1]

        if start == 0:
            return None

        pct = (
            ((end - start) / start)
            * 100
        )

        direction = (
            "LONG"
            if pct > 0
            else "SHORT"
        )

        return TechnicalSignal(
            symbol=symbol,
            signal_type="MOMENTUM",
            direction=direction,
            confidence=signal_confidence_engine.normalize(
                abs(pct)
            ),
        )

    def mean_reversion(
        self,
        symbol,
        series,
        period=20,
    ):
        mean = self.sma(
            series,
            period,
        )

        if mean == 0:
            return None

        last = series[-1]

        deviation = (
            ((last - mean) / mean)
            * 100
        )

        direction = (
            "SHORT"
            if deviation > 0
            else "LONG"
        )

        return TechnicalSignal(
            symbol=symbol,
            signal_type="MEAN_REVERSION",
            direction=direction,
            confidence=signal_confidence_engine.normalize(
                abs(deviation)
            ),
        )


technical_signal_engine = (
    TechnicalSignalEngine()
)