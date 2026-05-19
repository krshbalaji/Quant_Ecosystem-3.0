from enum import Enum


class ProfileTypes(str, Enum):
    SCALP = "SCALP"
    INTRADAY = "INTRADAY"
    SWING = "SWING"
    FNO = "FNO"
    MULTIBAGGER = "MULTIBAGGER"
    INVESTMENT = "INVESTMENT"
