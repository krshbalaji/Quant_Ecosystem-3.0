from typing import Dict, Optional, Tuple


class CorrelationGuard:
    def __init__(
        self,
        total_capital: float,
        max_thesis_exposure_pct: float = 0.25,
        max_group_exposures: int = 2,
    ) -> None:
        self.total_capital = float(max(total_capital, 1.0))
        self.max_thesis_exposure_pct = float(max(0.0, min(max_thesis_exposure_pct, 1.0)))
        self.max_group_exposures = max(1, int(max_group_exposures))
        self.exposures: Dict[str, float] = {}
        self.group_counts: Dict[str, int] = {}

    @property
    def thesis_threshold(self) -> float:
        return self.total_capital * self.max_thesis_exposure_pct

    def evaluate(
        self,
        thesis: Optional[str],
        amount: float,
        group: Optional[str] = None,
    ) -> Tuple[bool, str]:
        amount = float(max(0.0, amount))
        if not thesis or amount <= 0.0:
            return True, "correlation guard: no thesis or zero amount"

        thesis_key = str(thesis).strip().upper()
        existing = float(self.exposures.get(thesis_key, 0.0))
        if existing + amount > self.thesis_threshold:
            return (
                False,
                "correlation guard: same thesis exposure too high",
            )

        if group:
            group_key = str(group).strip().upper()
            existing_group = int(self.group_counts.get(group_key, 0))
            if existing_group >= self.max_group_exposures:
                return (
                    False,
                    "correlation guard: duplicate thesis group exposure limit reached",
                )

        return True, "correlation guard: exposure acceptable"

    def record_exposure(
        self,
        thesis: str,
        amount: float,
        group: Optional[str] = None,
    ) -> None:
        amount = float(max(0.0, amount))
        thesis_key = str(thesis).strip().upper()
        self.exposures[thesis_key] = float(self.exposures.get(thesis_key, 0.0)) + amount
        if group:
            group_key = str(group).strip().upper()
            self.group_counts[group_key] = int(self.group_counts.get(group_key, 0)) + 1

    def release_exposure(
        self,
        thesis: str,
        amount: float,
        group: Optional[str] = None,
    ) -> None:
        amount = float(max(0.0, amount))
        thesis_key = str(thesis).strip().upper()
        self.exposures[thesis_key] = max(0.0, float(self.exposures.get(thesis_key, 0.0)) - amount)
        if group:
            group_key = str(group).strip().upper()
            self.group_counts[group_key] = max(0, int(self.group_counts.get(group_key, 0)) - 1)

    def get_exposure(self, thesis: str) -> float:
        return float(self.exposures.get(str(thesis).strip().upper(), 0.0))
