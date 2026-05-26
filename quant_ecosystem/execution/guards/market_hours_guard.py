class MarketHoursGuard:

    def check(
        self,
        strict_market_hours=False,
        market_open=True,
    ):
        if strict_market_hours and not market_open:
            raise RuntimeError(
                "Market is closed"
            )