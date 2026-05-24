from quant_ecosystem.market.options.option_models import (
    CanonicalOptionContract,
    CanonicalOptionChain,
)


class OptionChainNormalizer:

    def normalize_fyers(
        self,
        underlying,
        expiry,
        raw_chain,
        spot_price=0.0,
    ):
        calls = []
        puts = []

        for item in raw_chain:
            option_type = str(
                item.get("option_type", "")
            ).upper()

            contract = CanonicalOptionContract(
                symbol=item.get("symbol", ""),
                underlying=underlying,
                strike=float(item.get("strike", 0.0)),
                expiry=expiry,
                option_type=option_type,
                bid=float(item.get("bid", 0.0)),
                ask=float(item.get("ask", 0.0)),
                ltp=float(item.get("ltp", 0.0)),
                volume=int(item.get("volume", 0)),
                open_interest=int(
                    item.get("open_interest", 0)
                ),
                implied_volatility=float(
                    item.get("iv", 0.0)
                ),
                metadata=item,
            )

            if option_type == "CE":
                calls.append(contract)

            elif option_type == "PE":
                puts.append(contract)

        return CanonicalOptionChain(
            underlying=underlying,
            expiry=expiry,
            calls=calls,
            puts=puts,
            spot_price=spot_price,
        )

    def normalize_generic(
        self,
        underlying,
        expiry,
        calls,
        puts,
        spot_price=0.0,
    ):
        return CanonicalOptionChain(
            underlying=underlying,
            expiry=expiry,
            calls=calls,
            puts=puts,
            spot_price=spot_price,
        )