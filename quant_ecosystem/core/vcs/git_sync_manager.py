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

        if not self._has_head_commit():
            print("Git pull on start: skipped (repository has no commits yet).")
            return False

        upstream_ok = self._has_upstream()
        if not upstream_ok:
            branch = self._current_branch() or "main"
            if not self._run(["git", "branch", "--set-upstream-to", f"origin/{branch}", branch], "Git set upstream"):
                print("Git pull on start: skipped (upstream not configured).")
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

        if not self._run(["git", "commit", "-m", self.auto_commit_message], "Git commit"):
            return False

        branch = self._current_branch() or "main"
        if self._has_upstream():
            pushed = self._run(["git", "push"], "Git push on end")
        else:
            pushed = self._run(["git", "push", "-u", "origin", branch], "Git push on end")

        if create_eod_tag:
            self.create_eod_tag()
        return pushed

    def create_eod_tag(self):
        if not self._is_git_repo():
            return False
        if not self._has_head_commit():
            print("Git tag skipped: repository has no commits yet.")
            return False

        day = datetime.datetime.now().strftime("%Y%m%d")
        base = f"eod-{day}"
        tag_name = self._next_available_tag(base)
        msg = f"EOD signed checkpoint {day}"

        signed = False
        if self._has_gpg_signing_key():
            signed = self._run(["git", "tag", "-s", tag_name, "-m", msg], f"Git signed tag {tag_name}")
        else:
            print("Git signed tag skipped: no GPG secret key configured.")
        if not signed:
            # Fallback when GPG signing is unavailable
            self._run(["git", "tag", "-a", tag_name, "-m", msg], f"Git annotated tag {tag_name}")

        return self._run(["git", "push", "origin", tag_name], f"Git push tag {tag_name}")

    def status_check(self):
        if not self._is_git_repo():
            return ""
        out = self._run_capture(["git", "status", "--short"])
        if not out:
            return ""
        ignored_tokens = ["__pycache__", ".pyc", "reporting/output/", "fyersApi.log", "fyersRequests.log"]
        lines = []
        for line in out.splitlines():
            if any(token in line for token in ignored_tokens):
                continue
            lines.append(line)
        return "\n".join(lines)

    def _stage_selected_paths(self):
        for path in self.include_paths:
            self._run(["git", "add", "-A", "--", path], f"Git add {path}")
        self._run(["git", "reset", "-q", "HEAD", "--", ":(glob)**/__pycache__/**"], "Git unstage __pycache__")
        self._run(["git", "reset", "-q", "HEAD", "--", ":(glob)**/*.pyc"], "Git unstage .pyc")
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

    def _has_head_commit(self):
        out = self._run_capture(["git", "rev-parse", "--verify", "HEAD"])
        return bool(out and out.strip())

    def _has_upstream(self):
        out = self._run_capture(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
        return bool(out and out.strip())

    def _current_branch(self):
        out = self._run_capture(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        if not out:
            return None
        return out.strip()

    def _has_gpg_signing_key(self):
        key = self._run_capture(["git", "config", "--get", "user.signingkey"])
        if not key:
            return False
        key_value = key.strip()
        if not key_value:
            return False
        listed = self._run_capture(["gpg", "--list-secret-keys", key_value])
        return bool(listed and listed.strip())

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
