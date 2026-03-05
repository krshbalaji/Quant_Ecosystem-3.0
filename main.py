import asyncio
import os
import sys
import subprocess
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))

DEPS_MARKER = ".deps_installed"


# ---------------------------------------------------------
# Dependency bootstrap (silent + only once)
# ---------------------------------------------------------
def ensure_dependencies():

    if os.path.exists(DEPS_MARKER):
        return

    req = "requirements.txt"

    if not os.path.exists(req):
        return

    print("Installing dependencies (first run only)...")

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", req],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    open(DEPS_MARKER, "w").close()

    print("Dependencies installed.")


ensure_dependencies()


# ---------------------------------------------------------
# Imports AFTER dependency install
# ---------------------------------------------------------
from quant_ecosystem.core.config_loader import Config
from quant_ecosystem.core.master_orchestrator import MasterOrchestrator
from quant_ecosystem.core.scheduler import Scheduler
from quant_ecosystem.core.system_factory import build_router
from quant_ecosystem.core.vcs.git_sync_manager import GitSyncManager
from quant_ecosystem.core.maintenance_manager import MaintenanceManager
from quant_ecosystem.core.onboarding import FirstTimeOnboarding


# ---------------------------------------------------------
# MAIN SYSTEM LOOP
# ---------------------------------------------------------
async def main():

    config = Config()

    git_sync = GitSyncManager(
        workdir=".",
        auto_commit_message=config.git_auto_commit_message,
        include_paths=config.git_sync_paths,
        exclude_paths=config.git_exclude_paths,
    )

    maintenance = MaintenanceManager(
        dependency_manager=None,
        git_manager=git_sync,
        update_probability=config.auto_update_probability,
    )

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


# ---------------------------------------------------------
# START
# ---------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())