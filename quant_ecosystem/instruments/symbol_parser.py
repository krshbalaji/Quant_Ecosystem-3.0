"""
QE3 Symbol Parser
Pack25
"""

import re

from quant_ecosystem.instruments.instrument_models import (
    AssetClass,
    InstrumentType,
    OptionType,
    CanonicalInstrument,
)


OPTION_RE = re.compile(
    r"^([A-Z]+)(\d{2})([A-Z]{3})(\d+)(CE|PE)$"
)

FUTURE_RE = re.compile(
    r"^([A-Z]+)(\d{2})([A-Z]{3})FUT$"
)

FOREX_RE = re.compile(
    r"^[A-Z]{6}$"
)

CRYPTO_RE = re.compile(
    r"^[A-Z]{5,12}$"
)


class SymbolParser:
    MONTHS = {
        "JAN": "01",
        "FEB": "02",
        "MAR": "03",
        "APR": "04",
        "MAY": "05",
        "JUN": "06",
        "JUL": "07",
        "AUG": "08",
        "SEP": "09",
        "OCT": "10",
        "NOV": "11",
        "DEC": "12",
    }

    def parse(self, symbol: str):
        symbol = str(symbol).strip().upper()

        #
        # Exchange equity style
        # NSE:SBIN-EQ
        #
        if ":" in symbol and symbol.endswith("-EQ"):
            exchange, rest = symbol.split(":", 1)
            underlying = rest.replace("-EQ", "")

            return CanonicalInstrument(
                symbol=symbol,
                asset_class=AssetClass.EQUITY,
                instrument_type=InstrumentType.SPOT,
                exchange=exchange,
                underlying=underlying,
                currency="INR",
            )

        #
        # Option
        # NIFTY25JUN24500CE
        #
        m = OPTION_RE.match(symbol)
        if m:
            underlying, yy, mon, strike, opt = m.groups()

            return CanonicalInstrument(
                symbol=symbol,
                asset_class=AssetClass.OPTION,
                instrument_type=InstrumentType.DERIVATIVE,
                underlying=underlying,
                expiry=f"20{yy}-{self.MONTHS[mon]}",
                strike=float(strike),
                option_type=(
                    OptionType.CALL
                    if opt == "CE"
                    else OptionType.PUT
                ),
                currency="INR",
            )

        #
        # Future
        # BANKNIFTY25JULFUT
        #
        m = FUTURE_RE.match(symbol)
        if m:
            underlying, yy, mon = m.groups()

            return CanonicalInstrument(
                symbol=symbol,
                asset_class=AssetClass.FUTURE,
                instrument_type=InstrumentType.DERIVATIVE,
                underlying=underlying,
                expiry=f"20{yy}-{self.MONTHS[mon]}",
                currency="INR",
            )

        #
        # Forex
        # EURUSD
        #
        if FOREX_RE.match(symbol):
            major_pairs = {
                "EURUSD",
                "GBPUSD",
                "USDJPY",
                "USDCHF",
                "AUDUSD",
                "USDCAD",
                "NZDUSD",
            }

            if symbol in major_pairs:
                return CanonicalInstrument(
                    symbol=symbol,
                    asset_class=AssetClass.FOREX,
                    instrument_type=InstrumentType.SPOT,
                    currency=symbol[3:],
                    underlying=symbol[:3],
                )

        #
        # Crypto
        # BTCUSDT
        #
        crypto_quotes = {
            "USDT",
            "USD",
            "INR",
            "BTC",
            "ETH",
        }

        for quote in crypto_quotes:
            if symbol.endswith(quote) and len(symbol) > len(quote):
                base = symbol[:-len(quote)]

                return CanonicalInstrument(
                    symbol=symbol,
                    asset_class=AssetClass.CRYPTO,
                    instrument_type=InstrumentType.SPOT,
                    underlying=base,
                    currency=quote,
                )

        #
        # Commodity
        #
        commodity_symbols = {
            "XAUUSD",
            "XAGUSD",
            "WTIUSD",
            "BRENTUSD",
        }

        if symbol in commodity_symbols:
            return CanonicalInstrument(
                symbol=symbol,
                asset_class=AssetClass.COMMODITY,
                instrument_type=InstrumentType.SPOT,
                underlying=symbol[:3],
                currency="USD",
            )

        #
        # Simple US equity fallback
        #
        if symbol.isalpha() and len(symbol) <= 8:
            return CanonicalInstrument(
                symbol=symbol,
                asset_class=AssetClass.EQUITY,
                instrument_type=InstrumentType.SPOT,
                underlying=symbol,
                currency="USD",
            )

        raise ValueError(
            f"unsupported symbol format: {symbol}"
        )


symbol_parser = SymbolParser()