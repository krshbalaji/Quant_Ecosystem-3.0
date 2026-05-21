import hashlib
import json
import time


class ReplayGuard:
    TTL_SEC = 300

    def __init__(self):
        self.seen = {}

    def _fingerprint(self, user_id, command, args):
        raw = json.dumps(
            {
                "u": str(user_id),
                "c": str(command),
                "a": args,
            },
            sort_keys=True,
            default=str
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    def allow(self, user_id, command, args):
        now = time.time()

        expired = [
            key for key, ts in self.seen.items()
            if now - ts > self.TTL_SEC
        ]
        for key in expired:
            del self.seen[key]

        fp = self._fingerprint(user_id, command, args)

        if fp in self.seen:
            return False, "REPLAY_DETECTED"

        self.seen[fp] = now
        return True, "OK"