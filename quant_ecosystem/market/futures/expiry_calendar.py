import calendar
from datetime import date


class ExpiryCalendar:

    MONTH_CODES = {
        1: "JAN",
        2: "FEB",
        3: "MAR",
        4: "APR",
        5: "MAY",
        6: "JUN",
        7: "JUL",
        8: "AUG",
        9: "SEP",
        10: "OCT",
        11: "NOV",
        12: "DEC",
    }

    def last_thursday(
        self,
        year,
        month,
    ):
        month_days = calendar.monthcalendar(
            year,
            month,
        )

        thursdays = [
            week[calendar.THURSDAY]
            for week in month_days
            if week[calendar.THURSDAY] != 0
        ]

        return date(
            year,
            month,
            thursdays[-1],
        )

    def next_monthly_expiry(
        self,
        from_date=None,
    ):
        if from_date is None:
            from_date = date.today()

        expiry = self.last_thursday(
            from_date.year,
            from_date.month,
        )

        if from_date <= expiry:
            return expiry

        month = from_date.month + 1
        year = from_date.year

        if month > 12:
            month = 1
            year += 1

        return self.last_thursday(
            year,
            month,
        )

    def contract_code(
        self,
        dt,
    ):
        return (
            f"{dt.year % 100:02d}"
            f"{self.MONTH_CODES[dt.month]}"
        )


expiry_calendar = ExpiryCalendar()