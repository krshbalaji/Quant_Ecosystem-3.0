from enum import Enum

REALITY_MODE = True
PRIMARY_SYMBOL = "^NSEI"

class MarketMode(Enum):
    SYNTH = "SYNTH"
    HISTORICAL = "HISTORICAL"
    PAPER = "PAPER"
    LIVE = "LIVE"
    

class MarketModeController:
    _mode = MarketMode.SYNTH

    @classmethod
    def set_mode(cls, mode):

        from quant_ecosystem.core.market_mode import REALITY_MODE

        if REALITY_MODE:
            print("🛑 REALITY MODE LOCK → forcing HISTORICAL")
            cls._mode = MarketMode.HISTORICAL
            return

        print(f"🌐 MARKET MODE SWITCH → {mode.value}")
        cls._mode = mode

    @classmethod
    def get_mode(cls) -> MarketMode:
        return cls._mode

    @classmethod
    def is_synth(cls):
        return cls._mode == MarketMode.SYNTH

    @classmethod
    def is_historical(cls):
        return cls._mode == MarketMode.HISTORICAL

    @classmethod
    def is_paper(cls):
        return cls._mode == MarketMode.PAPER

    @classmethod
    def is_live(cls):
        return cls._mode == MarketMode.LIVE

   
    