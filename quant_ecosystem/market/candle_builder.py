from typing import Dict, List


class CandleBuilder:
    """
    Adapter utilities to normalise broker tick / candle payloads into a
    standard OHLCV dictionary representation.
    """

    def build_from_fyers(self, data: Dict) -> List[Dict]:
        """
        Convert FYERS 'history' style response into a list of OHLCV dicts.
        """
        candles: List[Dict] = []
        rows = data.get("candles") or []
        for c in rows:
            if not isinstance(c, (list, tuple)) or len(c) < 6:
                continue
            candles.append(
                {
                    "time": c[0],
                    "open": c[1],
                    "high": c[2],
                    "low": c[3],
                    "close": c[4],
                    "volume": c[5],
                }
            )
        return candles
