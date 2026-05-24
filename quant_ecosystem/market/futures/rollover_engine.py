from datetime import date

from quant_ecosystem.market.futures.expiry_calendar import (
    expiry_calendar,
)


class RolloverEngine:

    def should_roll(
        self,
        from_date=None,
        roll_days_before=3,
    ):
        if from_date is None:
            from_date = date.today()

        expiry = expiry_calendar.next_monthly_expiry(
            from_date
        )

        days_left = (
            expiry - from_date
        ).days

        return days_left <= roll_days_before

    def roll_target(
        self,
        root_symbol,
        from_date=None,
    ):
        from quant_ecosystem.market.futures.continuous_contract_mapper import (
            continuous_contract_mapper,
        )

        return continuous_contract_mapper.next_contract(
            root_symbol,
            from_date,
        )


rollover_engine = RolloverEngine()