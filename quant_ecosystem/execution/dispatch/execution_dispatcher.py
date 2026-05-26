class ExecutionDispatcher:

    def __init__(
        self,
        live_execution_orchestrator,
        paper_execution_orchestrator,
    ):
        self._live = live_execution_orchestrator
        self._paper = paper_execution_orchestrator

    def dispatch(
        self,
        mode,
        broker,
        broker_name,
        normalized_symbol,
        symbol,
        side,
        qty,
        price,
        fee,
        meta,
        asset_class,
        caps,
    ):
        if str(mode).upper() != "LIVE":
            return self._paper.execute(
                paper_broker=broker,
                normalized_symbol=normalized_symbol,
                side=side,
                qty=qty,
                price=price,
            )

        if caps.supports_retry:
            return self._live.execute(
                broker=broker,
                broker_name=broker_name,
                normalized_symbol=normalized_symbol,
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                asset_class=asset_class,
                execution_fn=lambda: broker.place_order(
                    symbol=normalized_symbol,
                    side=side,
                    qty=qty,
                    price=price,
                ),
            )

        return broker.place_order(
            symbol=normalized_symbol,
            side=side,
            qty=qty,
            price=price,
            fee=fee,
            meta=meta,
        )