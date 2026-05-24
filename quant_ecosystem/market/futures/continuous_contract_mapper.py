from quant_ecosystem.market.futures.expiry_calendar import (
    expiry_calendar,
)


class ContinuousContractMapper:

    def front_month_contract(
        self,
        root_symbol,
        from_date=None,
    ):
        expiry = expiry_calendar.next_monthly_expiry(
            from_date
        )

        code = expiry_calendar.contract_code(
            expiry
        )

        return f"{root_symbol}{code}FUT"

    def next_contract(
        self,
        root_symbol,
        from_date=None,
    ):
        expiry = expiry_calendar.next_monthly_expiry(
            from_date
        )

        month = expiry.month + 1
        year = expiry.year

        if month > 12:
            month = 1
            year += 1

        from datetime import date

        next_dt = date(year, month, 1)

        next_expiry = expiry_calendar.next_monthly_expiry(
            next_dt
        )

        code = expiry_calendar.contract_code(
            next_expiry
        )

        return f"{root_symbol}{code}FUT"


continuous_contract_mapper = ContinuousContractMapper()