import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))

sys.path.append(str(Path(__file__).parent))

from quant_ecosystem.core.config_loader import Config
from quant_ecosystem.core.dependency_manager import DependencyManager
from quant_ecosystem.core.maintenance_manager import MaintenanceManager
from quant_ecosystem.core.master_orchestrator import MasterOrchestrator
from quant_ecosystem.core.onboarding import FirstTimeOnboarding
from quant_ecosystem.core.scheduler import Scheduler
from quant_ecosystem.core.system_factory import build_router
from quant_ecosystem.core.vcs.git_sync_manager import GitSyncManager



async def main():
    config = Config()
    deps = DependencyManager(req_file="requests.txt")
    git_sync = GitSyncManager(
        workdir=".",
        auto_commit_message=config.git_auto_commit_message,
        include_paths=config.git_sync_paths,
        exclude_paths=config.git_exclude_paths,
    )
    maintenance = MaintenanceManager(
        dependency_manager=deps,
        git_manager=git_sync,
        update_probability=config.auto_update_probability,
    )

    if config.auto_dependency_install:
        deps.install_from_file()
    if config.auto_git_sync:
        git_sync.pull_on_start()
    phase = Scheduler().current_phase()
    maintenance.run_random_checks(phase=phase)

    FirstTimeOnboarding().ensure()

    router = build_router(config)

    orchestrator = MasterOrchestrator(router)
    await orchestrator.start(
        router,
        git_sync=git_sync,
        auto_push_end=config.auto_git_push_end,
        auto_tag_end=config.auto_git_tag_end,
    )

    if config.telegram_always_on and getattr(router, "telegram", None):
        print("Telegram standby listener active (idle mode). Press Ctrl+C to stop.")
        poll_sec = max(0.2, float(config.telegram_idle_poll_sec))
        while True:
            commands = router.telegram.consume_webhook_events()
            for command, result in commands:
                response = f"Command {command}: {result}"
                print(response)
                if not str(command).startswith("button:"):
                    router.telegram.send_message(response)
            await asyncio.sleep(poll_sec)


if __name__ == "__main__":

    asyncio.run(main())
