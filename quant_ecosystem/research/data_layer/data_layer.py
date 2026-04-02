from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable


logger = logging.getLogger(__name__)


@dataclass
class DataPacket:
    symbol: str
    timeframe: str
    source: str
    mode: str
    payload: dict[str, Any]


class DataLayer:
    """Normalizes market data access across live, paper, and synthetic modes."""

    def __init__(self, config: Any = None, market_data: Any = None) -> None:
        self.config = config
        self.market_data = market_data
        self.data_mode = str(getattr(config, "data_mode", "SYNTHETIC")).upper()
        self.environment = str(getattr(config, "environment", "DEV")).upper()
        self._sources: dict[str, Callable[..., Any]] = {}

    def register_source(self, name: str, reader: Callable[..., Any]) -> None:
        self._sources[str(name).lower().strip()] = reader

    def get_mode(self) -> str:
        return self.data_mode

    def fetch_market_data(
        self,
        symbol: str,
        timeframe: str = "5m",
        source: str | None = None,
        allow_synthetic: bool = True,
    ) -> DataPacket:
        payload = None
        resolved_source = str(source or "").lower().strip()

        price = self.market_data.get_price_sync(symbol)

        return {
            "symbol": symbol,
            "price": price,
            "timeframe": timeframe,
        }

        if resolved_source and resolved_source in self._sources:
            payload = self._safe_read(self._sources[resolved_source], symbol=symbol, timeframe=timeframe)
        elif self.market_data is not None:
            payload = self._fetch_from_market_engine(symbol=symbol, timeframe=timeframe)
            resolved_source = resolved_source or "market_engine"

        normalized = self.normalize(symbol=symbol, timeframe=timeframe, payload=payload)
        if normalized is None and allow_synthetic:
            resolved_source = "synthetic"
            normalized = self.synthetic(symbol=symbol, timeframe=timeframe)

        if normalized is None:
            raise ValueError(f"No valid data available for {symbol}")

        packet = DataPacket(
            symbol=symbol,
            timeframe=timeframe,
            source=resolved_source or "unknown",
            mode=self.data_mode,
            payload=normalized,
        )
        logger.debug(
            "DataLayer packet ready | symbol=%s timeframe=%s source=%s mode=%s",
            packet.symbol,
            packet.timeframe,
            packet.source,
            packet.mode,
        )
        return packet

    def normalize(self, symbol: str, timeframe: str, payload: Any) -> dict[str, Any] | None:
        if payload is None:
            return None

        if isinstance(payload, dict):
            data = dict(payload)
        elif isinstance(payload, list):
            closes = [self._to_float(item.get("close", item)) for item in payload if item is not None]
            data = {"close": closes}
        else:
            return None

        close = data.get("close", [])
        if isinstance(close, (int, float)):
            close = [float(close)]
        close = [self._to_float(item) for item in list(close or []) if item is not None]
        if not close:
            return None

        latest = close[-1]
        high = [self._to_float(item) for item in list(data.get("high", close) or close)]
        low = [self._to_float(item) for item in list(data.get("low", close) or close)]
        open_ = [self._to_float(item) for item in list(data.get("open", close) or close)]
        volume = [self._to_float(item) for item in list(data.get("volume", [1000.0] * len(close)) or [1000.0])]
        timestamps = list(data.get("timestamp", []) or data.get("timestamps", []) or [])
        if not timestamps:
            step = self._timeframe_delta(timeframe)
            base = datetime.utcnow() - (step * max(len(close) - 1, 0))
            timestamps = [(base + (step * idx)).strftime("%Y-%m-%dT%H:%M:%SZ") for idx in range(len(close))]

        normalized = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": timestamps,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "latest_price": latest,
            "valid": True,
        }
        return normalized if self.validate(normalized) else None

    def validate(self, payload: dict[str, Any]) -> bool:
        required = ("symbol", "timeframe", "close", "latest_price")
        for key in required:
            if key not in payload:
                return False
        close = list(payload.get("close", []) or [])
        return bool(close) and all(item is not None for item in close)

    def synthetic(self, symbol: str, timeframe: str = "5m") -> dict[str, Any]:
        base = 100.0 + (sum(ord(ch) for ch in str(symbol)) % 75)
        candles = [round(base + (idx * 0.35), 2) for idx in range(20)]
        volume = [1000.0 + (idx * 45.0) for idx in range(20)]
        payload = {
            "symbol": symbol,
            "timeframe": timeframe,
            "open": candles,
            "high": [value + 0.45 for value in candles],
            "low": [value - 0.45 for value in candles],
            "close": candles,
            "volume": volume,
        }
        normalized = self.normalize(symbol=symbol, timeframe=timeframe, payload=payload)
        if normalized is None:
            raise ValueError(f"Failed to synthesize market data for {symbol}")
        normalized["source_mode"] = "SYNTHETIC"
        return normalized

    def _fetch_from_market_engine(self, symbol: str, timeframe: str) -> Any:
        engine = self.market_data
        readers = (
            ("get_snapshot", {"symbol": symbol, "timeframe": timeframe}),
            ("fetch", {"symbol": symbol, "timeframe": timeframe}),
            ("get_market_data", {"symbol": symbol, "timeframe": timeframe}),
            ("get_price", {"symbol": symbol}),
        )
        for method_name, kwargs in readers:
            reader = getattr(engine, method_name, None)
            if callable(reader):
                payload = self._safe_read(reader, **kwargs)
                if payload is not None:
                    if method_name == "get_price":
                        return {"close": [payload]}
                    return payload
        return None

    def _safe_read(self, reader: Callable[..., Any], **kwargs: Any) -> Any:
        try:
            return reader(**kwargs)
        except TypeError:
            try:
                return reader(*kwargs.values())
            except Exception as exc:  # noqa: BLE001
                logger.debug("DataLayer source call failed | error=%s", exc)
                return None
        except Exception as exc:  # noqa: BLE001
            logger.debug("DataLayer source call failed | error=%s", exc)
            return None

    def _timeframe_delta(self, timeframe: str) -> timedelta:
        mapping = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "1d": timedelta(days=1),
        }
        return mapping.get(str(timeframe).lower(), timedelta(minutes=5))

    def _to_float(self, value: Any) -> float:
        try:
            return float(value)
        except Exception:  # noqa: BLE001
            return 0.0
