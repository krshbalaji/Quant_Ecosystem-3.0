class CorrelationRegistry:

    def __init__(self):

        self._groups = {
            "BANKING": {
                "NSE:HDFCBANK-EQ",
                "NSE:ICICIBANK-EQ",
                "NSE:SBIN-EQ",
                "NSE:AXISBANK-EQ",
                "BANKNIFTY",
            },

            "IT": {
                "NSE:TCS-EQ",
                "NSE:INFY-EQ",
                "NSE:WIPRO-EQ",
                "NSE:HCLTECH-EQ",
            },

            "ENERGY": {
                "NSE:RELIANCE-EQ",
                "NSE:ONGC-EQ",
                "NSE:IOC-EQ",
            },
        }

    def group_for(
        self,
        symbol,
    ):

        symbol = str(
            symbol
        ).upper()

        for (
            group_name,
            members,
        ) in self._groups.items():

            if symbol in members:
                return group_name

        return "UNGROUPED"


correlation_registry = (
    CorrelationRegistry()
)