import random


class MaintenanceManager:

    def __init__(self, dependency_manager, git_manager, update_probability=0.25, **kwargs):
        self.dependency_manager = dependency_manager
        self.git_manager = git_manager
        self.update_probability = max(0.0, min(update_probability, 1.0))

    def run_random_checks(self, phase="OFF_HOURS"):
        git_status = self.git_manager.status_check()
        if git_status:
            print("Git status snapshot:\n" + git_status)

        if str(phase).upper() != "HEALTH_CHECK":
            print(f"Maintenance: dependency upgrade skipped outside HEALTH_CHECK window (phase={phase}).")
            return

        if random.random() <= self.update_probability:
            print("Maintenance: running randomized dependency upgrade check.")
            self.dependency_manager.upgrade_from_file()
