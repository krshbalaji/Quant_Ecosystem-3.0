"""Execution micro-layer adapter."""


class ExecutionRouterLayer:
    """Facade for manual/assisted/autonomous execution calls."""

    def __init__(self, router=None, **kwargs):
        self.router = router

    async def execute(self, signal=None, market_bias="NEUTRAL", regime="RANGING"):
        if not self.router:
            return {"status": "SKIP", "reason": "NO_ROUTER"}
        return await self.router.execute(signal=signal, market_bias=market_bias, regime=regime)
