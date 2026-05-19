from typing import Optional, Set

from quant_ecosystem.contracts.profile_types import ProfileTypes


class ReserveManager:
    def __init__(
        self,
        total_capital: float,
        reserve_pct: float = 0.0,
        locked_profiles: Optional[Set[ProfileTypes]] = None,
    ) -> None:
        self.total_capital = float(total_capital)
        self.reserve_pct = float(max(0.0, reserve_pct))
        self.locked_profiles = locked_profiles or {
            ProfileTypes.SCALP,
            ProfileTypes.INTRADAY,
        }

        self.reserve_amount = round(self.total_capital * self.reserve_pct, 2)
        self.available = float(self.reserve_amount)
        self.unlocked = False
        self.unlock_reason = ""

    def set_total_capital(self, total_capital: float) -> None:
        self.total_capital = float(total_capital)
        self.reserve_amount = round(self.total_capital * self.reserve_pct, 2)
        self.available = min(self.available, self.reserve_amount)

    def set_reserve_pct(self, reserve_pct: float) -> None:
        self.reserve_pct = float(max(0.0, reserve_pct))
        self.reserve_amount = round(self.total_capital * self.reserve_pct, 2)
        self.available = min(self.available, self.reserve_amount)

    def can_consume(self, profile: ProfileTypes, amount: float) -> bool:
        amount = float(max(0.0, amount))
        if amount <= 0.0 or amount > self.available:
            return False

        profile_enum = profile if isinstance(profile, ProfileTypes) else ProfileTypes(str(profile).upper())
        if profile_enum in self.locked_profiles and not self.unlocked:
            return False

        return True

    def consume(self, amount: float) -> bool:
        amount = float(max(0.0, amount))
        if amount > self.available:
            return False
        self.available = max(0.0, self.available - amount)
        return True

    def release(self, amount: float) -> None:
        amount = float(max(0.0, amount))
        self.available = min(self.reserve_amount, self.available + amount)

    def unlock_for_premium(self, reason: str = "premium opportunity") -> bool:
        if self.available <= 0.0:
            return False
        self.unlocked = True
        self.unlock_reason = reason
        return True

    def reset(self) -> None:
        self.available = float(self.reserve_amount)
        self.unlocked = False
        self.unlock_reason = ""
