import asyncio

from core.config_loader import Config
from core.dependency_manager import DependencyManager
from core.maintenance_manager import MaintenanceManager
from core.master_orchestrator import MasterOrchestrator
from core.onboarding import FirstTimeOnboarding
from core.scheduler import Scheduler
from core.system_factory import build_router
from core.vcs.git_sync_manager import GitSyncManager


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

    router = build_router()

    orchestrator = MasterOrchestrator()
    await orchestrator.start(
        router,
        git_sync=git_sync,
        auto_push_end=config.auto_git_push_end,
        auto_tag_end=config.auto_git_tag_end,
    )


if __name__ == "__main__":

    asyncio.run(main())
