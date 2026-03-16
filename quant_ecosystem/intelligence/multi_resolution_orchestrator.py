import threading
import time

from quant_ecosystem.intelligence.resolution_registry import ResolutionRegistry
from quant_ecosystem.autonomous_research.autonomous_research_loop import AutonomousResearchLoop


class MultiResolutionResearchOrchestrator:

    def __init__(self, system_factory):
        self.system_factory = system_factory
        self.registry = ResolutionRegistry()
        self.loops = {}

    def start(self):

        for res in self.registry.all():

            print(f"🧠 Spawning Research Loop → {res.timeframe}")

            loop = AutonomousResearchLoop(
                system_factory=self.system_factory,
                cycle_seconds=120
            )

            thread = threading.Thread(
                target=loop.start,
                daemon=True
            )

            thread.start()

            self.loops[res.timeframe] = {
                "loop": loop,
                "thread": thread
            }

            time.sleep(2)

        print("✅ Multi-Resolution Research Fabric ONLINE")

    def status(self):

        return {
            tf: l["thread"].is_alive()
            for tf, l in self.loops.items()
        }