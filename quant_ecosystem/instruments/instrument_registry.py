"""
QE3 Instrument Registry
Pack25
"""

from typing import Dict

from quant_ecosystem.instruments.instrument_models import (
    CanonicalInstrument,
)


class InstrumentRegistry:
    """
    Symbol cache / instrument cache
    """

    def __init__(self):
        self._instruments: Dict[
            str,
            CanonicalInstrument
        ] = {}

    def register(
        self,
        instrument: CanonicalInstrument,
    ):
        self._instruments[
            instrument.symbol
        ] = instrument

    def get(self, symbol: str):
        return self._instruments.get(symbol)

    def exists(self, symbol: str):
        return symbol in self._instruments

    def clear(self):
        self._instruments.clear()

    def all(self):
        return self._instruments


instrument_registry = InstrumentRegistry()