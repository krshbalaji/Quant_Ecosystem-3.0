from dataclasses import dataclass, field
from typing import Dict, Optional, Union

from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.risk.correlation_guard import CorrelationGuard
from quant_ecosystem.risk.reserve_manager import ReserveManager


DEFAULT_BUCKET_WEIGHTS: Dict[ProfileTypes, float] = {
    ProfileTypes.SCALP: 0.10,
    ProfileTypes.INTRADAY: 0.20,
    ProfileTypes.SWING: 0.20,
    ProfileTypes.FNO: 0.10,
    ProfileTypes.MULTIBAGGER: 0.25,
    ProfileTypes.INVESTMENT: 0.15,
}


@dataclass
class CapitalBucket:
    profile: ProfileTypes
    weight: float
    allocated_capital: float = 0.0
    used_capital: float = 0.0
    metadata: Dict[str, object] = field(default_factory=dict)

    @property
    def available(self) -> float:
        return max(0.0, float(self.allocated_capital) - float(self.used_capital))


class CapitalAllocatorV2:
    def __init__(
        self,
        total_capital: float = 100_000.0,
        reserve_pct: float = 0.0,
        bucket_weights: Optional[Dict[ProfileTypes, float]] = None,
        reserve_manager: Optional[ReserveManager] = None,
        correlation_guard: Optional[CorrelationGuard] = None,
        db_enabled: bool = False,
    ) -> None:
        self.total_capital = float(total_capital)
        self.reserve_pct = float(max(0.0, reserve_pct))
        self.db_enabled = bool(db_enabled)

        self.bucket_weights = bucket_weights or DEFAULT_BUCKET_WEIGHTS
        self.buckets: Dict[ProfileTypes, CapitalBucket] = {
            profile: CapitalBucket(profile=profile, weight=float(weight))
            for profile, weight in self.bucket_weights.items()
        }

        self.reserve_manager = reserve_manager or ReserveManager(
            total_capital=self.total_capital,
            reserve_pct=self.reserve_pct,
        )
        self.correlation_guard = correlation_guard or CorrelationGuard(total_capital=self.total_capital)

        self._rebuild_allocations()
        if self.db_enabled:
            self._initialize_database()
            self._sync_buckets_to_db()

    def _normalize_profile(self, profile: Union[str, ProfileTypes, object]) -> ProfileTypes:
        if isinstance(profile, ProfileTypes):
            return profile
        if hasattr(profile, "name"):
            try:
                return ProfileTypes(str(getattr(profile, "name")).upper())
            except ValueError:
                pass
        try:
            return ProfileTypes(str(profile).upper())
        except ValueError as exc:
            raise ValueError(f"Unknown profile: {profile}") from exc

    def _rebuild_allocations(self) -> None:
        effective_pct = max(0.0, 1.0 - self.reserve_pct)
        for bucket in self.buckets.values():
            bucket.allocated_capital = round(self.total_capital * bucket.weight * effective_pct, 2)
            bucket.used_capital = min(bucket.used_capital, bucket.allocated_capital)
        self.reserve_manager.set_total_capital(self.total_capital)
        self.reserve_manager.set_reserve_pct(self.reserve_pct)

    def _initialize_database(self) -> None:
        try:
            from quant_ecosystem.storage.organism_db import init_db  # noqa: F401
            init_db()
        except Exception:
            pass

    def _sync_buckets_to_db(self) -> None:
        try:
            from quant_ecosystem.storage.organism_db import dumps_json, get_connection, utc_now

            now = utc_now()
            with get_connection() as conn:
                for bucket in self.buckets.values():
                    conn.execute(
                        "INSERT OR REPLACE INTO capital_buckets"
                        "(id, created_at, updated_at, profile, allocated_capital, used_capital, available_capital, metadata)"
                        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            f"bucket:{bucket.profile.value}",
                            now,
                            now,
                            bucket.profile.value,
                            bucket.allocated_capital,
                            bucket.used_capital,
                            bucket.available,
                            dumps_json(bucket.metadata),
                        ),
                    )
                conn.commit()
        except Exception:
            pass

    def get_bucket_size(self, profile: Union[str, ProfileTypes]) -> float:
        bucket = self.buckets[self._normalize_profile(profile)]
        return float(bucket.allocated_capital)

    def get_available_budget(self, profile: Union[str, ProfileTypes]) -> float:
        bucket = self.buckets[self._normalize_profile(profile)]
        return float(bucket.available)

    def can_allocate(
        self,
        profile: Union[str, ProfileTypes],
        amount: float,
        allow_reserve: bool = False,
    ) -> bool:
        amount = float(max(0.0, amount))
        available = self.get_available_budget(profile)
        if amount <= available:
            return True
        if allow_reserve and self.reserve_manager.can_consume(profile, amount - available):
            return True
        return False

    def consume_budget(
        self,
        profile: Union[str, ProfileTypes],
        amount: float,
        allow_reserve: bool = False,
    ) -> bool:
        amount = float(max(0.0, amount))
        bucket = self.buckets[self._normalize_profile(profile)]
        if amount <= bucket.available:
            bucket.used_capital += amount
            if self.db_enabled:
                self._sync_buckets_to_db()
            return True

        if allow_reserve:
            remainder = amount - bucket.available
            if self.reserve_manager.can_consume(profile, remainder):
                if bucket.available > 0:
                    bucket.used_capital += bucket.available
                self.reserve_manager.consume(remainder)
                if self.db_enabled:
                    self._sync_buckets_to_db()
                return True

        return False

    def release_budget(
        self,
        profile: Union[str, ProfileTypes],
        amount: float,
        to_reserve: bool = False,
    ) -> None:
        amount = float(max(0.0, amount))
        if to_reserve:
            self.reserve_manager.release(amount)
            return

        bucket = self.buckets[self._normalize_profile(profile)]
        bucket.used_capital = max(0.0, bucket.used_capital - amount)
        if self.db_enabled:
            self._sync_buckets_to_db()

    def get_total_used(self) -> float:
        return float(sum(bucket.used_capital for bucket in self.buckets.values()))

    def get_total_available(self) -> float:
        return float(sum(bucket.available for bucket in self.buckets.values()))

    def unlock_reserve_for_premium(self, reason: str = "premium opportunity") -> bool:
        return self.reserve_manager.unlock_for_premium(reason)

    def record_thesis_exposure(
        self,
        thesis: str,
        amount: float,
        group: Optional[str] = None,
    ) -> None:
        self.correlation_guard.record_exposure(thesis, amount, group=group)

    def can_open_thesis(
        self,
        thesis: str,
        amount: float,
        group: Optional[str] = None,
    ) -> bool:
        allowed, _ = self.correlation_guard.evaluate(thesis, amount, group=group)
        return allowed

    def get_thesis_exposure(self, thesis: str) -> float:
        return self.correlation_guard.get_exposure(thesis)
