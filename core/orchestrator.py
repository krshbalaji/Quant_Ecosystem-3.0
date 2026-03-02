import asyncio

from core.master_orchestrator import MasterOrchestrator
from core.system_factory import build_router


class Orchestrator:

    def __init__(self):
        self.router = build_router()
        self.master = MasterOrchestrator()

    async def start(self):
        await self.master.start(self.router)

    def start_sync(self):
        asyncio.run(self.start())
