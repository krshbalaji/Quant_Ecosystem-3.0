"""
QE3 Instrument Resolver
Pack25
"""

from quant_ecosystem.instruments.instrument_registry import (
    instrument_registry,
)

from quant_ecosystem.instruments.symbol_parser import (
    symbol_parser,
)

from quant_ecosystem.instruments.contract_specs import (
    contract_specs,
)


class InstrumentResolver:
    """
    Parse + enrich + cache
    """

    def resolve(self, symbol: str):
        cached = instrument_registry.get(symbol)

        if cached:
            return cached

        instrument = symbol_parser.parse(symbol)

        contract_specs.apply(instrument)

        instrument_registry.register(instrument)

        return instrument

    def clear(self):
        instrument_registry.clear()


instrument_resolver = InstrumentResolver()