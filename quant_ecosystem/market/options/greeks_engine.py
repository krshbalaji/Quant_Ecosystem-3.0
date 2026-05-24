import math

from quant_ecosystem.market.options.greeks_models import (
    CanonicalGreeks,
)


class GreeksEngine:

    @staticmethod
    def _norm_pdf(x):
        return (
            math.exp(-0.5 * x * x)
            / math.sqrt(2 * math.pi)
        )

    @staticmethod
    def _norm_cdf(x):
        return 0.5 * (
            1.0 + math.erf(x / math.sqrt(2.0))
        )

    @staticmethod
    def _d1(
        spot,
        strike,
        rate,
        volatility,
        time_to_expiry,
    ):
        return (
            math.log(spot / strike)
            + (
                rate
                + (volatility ** 2) / 2.0
            )
            * time_to_expiry
        ) / (
            volatility
            * math.sqrt(time_to_expiry)
        )

    @staticmethod
    def _d2(
        d1,
        volatility,
        time_to_expiry,
    ):
        return (
            d1
            - volatility
            * math.sqrt(time_to_expiry)
        )

    def calculate(
        self,
        spot,
        strike,
        rate,
        volatility,
        time_to_expiry,
        option_type="CE",
    ):
        """
        Black-Scholes Greeks

        Parameters
        ----------
        spot : float
        strike : float
        rate : float
            risk-free rate (0.05 = 5%)
        volatility : float
            annualized volatility (0.20 = 20%)
        time_to_expiry : float
            years
        """

        option_type = str(option_type).upper()

        if (
            spot <= 0
            or strike <= 0
            or volatility <= 0
            or time_to_expiry <= 0
        ):
            return CanonicalGreeks()

        d1 = self._d1(
            spot,
            strike,
            rate,
            volatility,
            time_to_expiry,
        )

        d2 = self._d2(
            d1,
            volatility,
            time_to_expiry,
        )

        nd1 = self._norm_pdf(d1)

        if option_type == "CE":
            delta = self._norm_cdf(d1)

            theta = (
                (
                    -spot
                    * nd1
                    * volatility
                )
                / (
                    2 * math.sqrt(time_to_expiry)
                )
                - (
                    rate
                    * strike
                    * math.exp(
                        -rate * time_to_expiry
                    )
                    * self._norm_cdf(d2)
                )
            ) / 365.0

            rho = (
                strike
                * time_to_expiry
                * math.exp(
                    -rate * time_to_expiry
                )
                * self._norm_cdf(d2)
            ) / 100.0

        else:
            delta = self._norm_cdf(d1) - 1

            theta = (
                (
                    -spot
                    * nd1
                    * volatility
                )
                / (
                    2 * math.sqrt(time_to_expiry)
                )
                + (
                    rate
                    * strike
                    * math.exp(
                        -rate * time_to_expiry
                    )
                    * self._norm_cdf(-d2)
                )
            ) / 365.0

            rho = (
                -strike
                * time_to_expiry
                * math.exp(
                    -rate * time_to_expiry
                )
                * self._norm_cdf(-d2)
            ) / 100.0

        gamma = (
            nd1
            / (
                spot
                * volatility
                * math.sqrt(time_to_expiry)
            )
        )

        vega = (
            spot
            * nd1
            * math.sqrt(time_to_expiry)
        ) / 100.0

        return CanonicalGreeks(
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            rho=rho,
        )


greeks_engine = GreeksEngine()