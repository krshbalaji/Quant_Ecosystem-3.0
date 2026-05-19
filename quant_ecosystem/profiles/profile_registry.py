from typing import Type

from ..contracts.profile_types import ProfileTypes
from .base_profile import BaseProfile
from .fno_profile import FNOProfile
from .investment_profile import InvestmentProfile
from .intraday_profile import IntradayProfile
from .multibagger_profile import MultibaggerProfile
from .scalp_profile import ScalpProfile
from .swing_profile import SwingProfile


PROFILE_REGISTRY: dict[ProfileTypes, Type[BaseProfile]] = {
    ProfileTypes.SCALP: ScalpProfile,
    ProfileTypes.INTRADAY: IntradayProfile,
    ProfileTypes.SWING: SwingProfile,
    ProfileTypes.FNO: FNOProfile,
    ProfileTypes.MULTIBAGGER: MultibaggerProfile,
    ProfileTypes.INVESTMENT: InvestmentProfile,
}


def get_profile(profile_type: ProfileTypes) -> BaseProfile:
    profile_cls = PROFILE_REGISTRY.get(profile_type)
    if profile_cls is None:
        raise ValueError(f"Unsupported profile type: {profile_type}")
    return profile_cls()
