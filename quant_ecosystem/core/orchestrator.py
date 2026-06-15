import asyncio

from quant_ecosystem.core.master_orchestrator import MasterOrchestrator
from quant_ecosystem.core.system_factory import build_router


class Orchestrator:

    def __init__(self, config=None, **kwargs):
        self.router = build_router(config)
        self.master = MasterOrchestrator(self.router)

    async def start(self):
        await self.master.start(self.router)

    def start_sync(self):
        asyncio.run(self.start())
