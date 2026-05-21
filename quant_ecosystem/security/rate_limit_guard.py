import time
from collections import defaultdict, deque


class RateLimitGuard:
    WINDOW_SEC = 60
    COOLDOWN_SEC = 300

    LIMITS = {
        "VIEWER": 10,
        "OPERATOR": 20,
        "ADMIN": 30,
        "BREAK_GLASS": 100,
    }

    def __init__(self):
        self.events = defaultdict(deque)
        self.lockouts = {}

    def allow(self, user_id, role):
        now = time.time()
        uid = str(user_id)

        locked_until = self.lockouts.get(uid)
        if locked_until and now < locked_until:
            return False, "LOCKED_OUT"

        q = self.events[uid]

        while q and now - q[0] > self.WINDOW_SEC:
            q.popleft()

        limit = self.LIMITS.get(role, 5)

        if len(q) >= limit:
            self.lockouts[uid] = now + self.COOLDOWN_SEC
            return False, "RATE_LIMIT"

        q.append(now)
        return True, "OK"