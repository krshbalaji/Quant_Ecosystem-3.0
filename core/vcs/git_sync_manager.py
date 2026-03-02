import datetime
import subprocess


class GitSyncManager:

    def __init__(
        self,
        workdir=".",
        auto_commit_message="auto: session sync",
        include_paths=None,
        exclude_paths=None,
    ):
        self.workdir = workdir
        self.auto_commit_message = auto_commit_message
        self.include_paths = include_paths or [
            "broker",
            "config",
            "control",
            "core",
            "execution",
            "intelligence",
            "market",
            "portfolio",
            "reporting",
            "research",
            "risk",
            "strategy_bank",
            "utils",
            "main.py",
            "launcher.py",
            "requests.txt",
            ".gitignore",
        ]
        self.exclude_paths = exclude_paths or [
            "reporting/output",
            "reporting/output/runtime",
            "reporting/output/audit",
        ]

    def pull_on_start(self):
        if not self._is_git_repo():
            print("Git sync skipped: not a git repository.")
            return False

        stashed = False
        stash_name = f"autosync-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        if self._has_uncommitted_changes():
            ok = self._run(["git", "stash", "push", "-u", "-m", stash_name], "Git stash before pull")
            stashed = ok

        pulled = self._run(["git", "pull", "--ff-only"], "Git pull on start")
        if not pulled:
            if stashed:
                self._run(["git", "stash", "pop"], "Git stash pop rollback")
            return False

        if stashed:
            reapplied = self._run(["git", "stash", "pop"], "Git stash reapply after pull")
            if not reapplied:
                print("Git reapply warning: stash pop had conflicts. Resolve manually.")
        return True

    def push_on_end(self, create_eod_tag=True):
        if not self._is_git_repo():
            return False

        self._stage_selected_paths()
        status = self._run_capture(["git", "status", "--porcelain"])
        if status is None or not status.strip():
            print("Git push skipped: no changes in selected paths.")
            if create_eod_tag:
                self.create_eod_tag()
            return True

        self._run(["git", "commit", "-m", self.auto_commit_message], "Git commit")
        pushed = self._run(["git", "push", "origin", "main"], "Git push on end")
        if create_eod_tag:
            self.create_eod_tag()
        return pushed

    def create_eod_tag(self):
        if not self._is_git_repo():
            return False

        day = datetime.datetime.now().strftime("%Y%m%d")
        base = f"eod-{day}"
        tag_name = self._next_available_tag(base)
        msg = f"EOD signed checkpoint {day}"

        signed = self._run(["git", "tag", "-s", tag_name, "-m", msg], f"Git signed tag {tag_name}")
        if not signed:
            # Fallback when GPG signing is unavailable
            self._run(["git", "tag", "-a", tag_name, "-m", msg], f"Git annotated tag {tag_name}")

        return self._run(["git", "push", "origin", tag_name], f"Git push tag {tag_name}")

    def status_check(self):
        if not self._is_git_repo():
            return ""
        out = self._run_capture(["git", "status", "--short"])
        return out or ""

    def _stage_selected_paths(self):
        for path in self.include_paths:
            self._run(["git", "add", "-A", "--", path], f"Git add {path}")
        for path in self.exclude_paths:
            self._run(["git", "reset", "-q", "HEAD", "--", path], f"Git unstage {path}")

    def _next_available_tag(self, base):
        existing = self._run_capture(["git", "tag"]) or ""
        tags = set(item.strip() for item in existing.splitlines() if item.strip())
        if base not in tags:
            return base
        idx = 1
        while f"{base}-{idx}" in tags:
            idx += 1
        return f"{base}-{idx}"

    def _has_uncommitted_changes(self):
        out = self._run_capture(["git", "status", "--porcelain"])
        return bool(out and out.strip())

    def _is_git_repo(self):
        out = self._run_capture(["git", "rev-parse", "--is-inside-work-tree"])
        return bool(out and out.strip() == "true")

    def _run(self, cmd, label):
        try:
            result = subprocess.run(cmd, cwd=self.workdir, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                print(f"{label}: OK")
                return True
            stderr = (result.stderr or result.stdout or "").strip()
            print(f"{label}: {stderr[:300]}")
            return False
        except Exception as exc:
            print(f"{label}: {exc}")
            return False

    def _run_capture(self, cmd):
        try:
            result = subprocess.run(cmd, cwd=self.workdir, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                return None
            return result.stdout
        except Exception:
            return None
