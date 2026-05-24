"""
QE3 Contract Specifications
Pack25
"""

from quant_ecosystem.instruments.instrument_models import (
    AssetClass,
)


DEFAULT_SPECS = {
    AssetClass.EQUITY: {
        "lot_size": 1,
        "tick_size": 0.01,
        "contract_multiplier": 1.0,
        "margin_profile": "cash",
    },
    AssetClass.ETF: {
        "lot_size": 1,
        "tick_size": 0.01,
        "contract_multiplier": 1.0,
        "margin_profile": "cash",
    },
    AssetClass.INDEX: {
        "lot_size": 1,
        "tick_size": 0.01,
        "contract_multiplier": 1.0,
        "margin_profile": "reference",
    },
    AssetClass.OPTION: {
        "lot_size": 75,
        "tick_size": 0.05,
        "contract_multiplier": 75.0,
        "margin_profile": "derivative",
    },
    AssetClass.FUTURE: {
        "lot_size": 25,
        "tick_size": 0.05,
        "contract_multiplier": 25.0,
        "margin_profile": "derivative",
    },
    AssetClass.FOREX: {
        "lot_size": 1000,
        "tick_size": 0.0001,
        "contract_multiplier": 1000.0,
        "margin_profile": "leveraged",
    },
    AssetClass.CRYPTO: {
        "lot_size": 1,
        "tick_size": 0.01,
        "contract_multiplier": 1.0,
        "margin_profile": "spot_or_margin",
    },
    AssetClass.COMMODITY: {
        "lot_size": 1,
        "tick_size": 0.01,
        "contract_multiplier": 1.0,
        "margin_profile": "commodity",
    },
}


class ContractSpecs:
    def apply(self, instrument):
        spec = DEFAULT_SPECS.get(instrument.asset_class)

        if not spec:
            return instrument

        instrument.lot_size = spec["lot_size"]
        instrument.tick_size = spec["tick_size"]
        instrument.contract_multiplier = spec["contract_multiplier"]

        instrument.metadata["margin_profile"] = spec[
            "margin_profile"
        ]

        return instrument


contract_specs = ContractSpecs()