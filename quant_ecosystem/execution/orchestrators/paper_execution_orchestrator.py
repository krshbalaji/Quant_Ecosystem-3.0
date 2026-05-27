class PaperExecutionOrchestrator:

    def execute(
        self,
        paper_broker,
        normalized_symbol,
        side,
        qty,
        price,
    ):
        result = paper_broker.place_order(
            symbol=normalized_symbol,
            side=side,
            qty=qty,
            price=price,
        )

        result = result or {}

        result.setdefault(
            "order_id",
            result.get("id", ""),
        )

        result.setdefault(
            "broker",
            getattr(
                paper_broker,
                "account_source",
                type(paper_broker).__name__.upper(),
            ),
        )

        result.setdefault(
            "execution_state",
            "CONFIRMED",
        )

        result.setdefault(
            "lifecycle_state",
            "FILLED",
        )

        return result