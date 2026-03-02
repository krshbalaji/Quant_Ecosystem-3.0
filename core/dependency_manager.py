import os
import subprocess
import sys


class DependencyManager:

    def __init__(self, req_file="requests.txt"):
        self.req_file = req_file

    def install_from_file(self):
        if not os.path.exists(self.req_file):
            print(f"Dependency file not found: {self.req_file}")
            return False

        cmd = [sys.executable, "-m", "pip", "install", "-r", self.req_file]
        return self._run(cmd, "Dependency install")

    def upgrade_from_file(self):
        if not os.path.exists(self.req_file):
            print(f"Dependency file not found: {self.req_file}")
            return False

        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "-r", self.req_file]
        return self._run(cmd, "Dependency upgrade")

    def _run(self, cmd, title):
        try:
            print(f"{title} started...")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                print(f"{title} completed.")
                return True
            print(f"{title} failed: {result.stderr.strip()[:300]}")
            return False
        except Exception as exc:
            print(f"{title} error: {exc}")
            return False
