"""Order slicing strategies for execution intelligence."""

from __future__ import annotations

from typing import Dict, List


class OrderSlicer:
    """Breaks large orders into slices for TWAP/VWAP/stealth execution."""

    def slice_order(
        self,
        quantity: int,
        method: str = "equal",
        slice_count: int = 10,
        volume_profile: List[float] | None = None,
    ) -> List[Dict]:
        qty = max(0, int(quantity))
        if qty <= 0:
            return []
        n = max(1, int(slice_count))
        n = min(n, qty)
        method_key = str(method or "equal").upper()

        if method_key == "VWAP" and volume_profile:
            return self._vwap_slices(qty, n, volume_profile)
        if method_key == "TWAP":
            return self._equal_slices(qty, n, spacing="time")
        return self._equal_slices(qty, n, spacing="equal")

    def _equal_slices(self, qty: int, n: int, spacing: str) -> List[Dict]:
        base = qty // n
        rem = qty % n
        out = []
        for i in range(n):
            q = base + (1 if i < rem else 0)
            out.append({"slice_no": i + 1, "quantity": q, "schedule": spacing})
        return out

    def _vwap_slices(self, qty: int, n: int, profile: List[float]) -> List[Dict]:
        if not profile:
            return self._equal_slices(qty, n, spacing="vwap_fallback")
        p = profile[:n]
        total = sum(max(0.0, float(v)) for v in p)
        if total <= 1e-9:
            return self._equal_slices(qty, n, spacing="vwap_fallback")
        raw = [int(round((max(0.0, float(v)) / total) * qty)) for v in p]
        delta = qty - sum(raw)
        idx = 0
        while delta != 0 and raw:
            j = idx % len(raw)
            if delta > 0:
                raw[j] += 1
                delta -= 1
            elif raw[j] > 0:
                raw[j] -= 1
                delta += 1
            idx += 1
        return [{"slice_no": i + 1, "quantity": raw[i], "schedule": "vwap"} for i in range(len(raw)) if raw[i] > 0]

