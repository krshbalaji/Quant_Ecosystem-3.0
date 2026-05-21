import time


class SessionGuard:
    def __init__(self, ttl_seconds=86400):
        self.bound_chat_id = None
        self.bound_username = None
        self.bound_at = None
        self.ttl_seconds = ttl_seconds

    def bind(self, chat_id, username=None):
        self.bound_chat_id = str(chat_id)
        self.bound_username = (username or "").strip().lower()
        self.bound_at = time.time()
        return True

    def is_expired(self):
        if self.bound_at is None:
            return False
        return (time.time() - self.bound_at) > self.ttl_seconds

    def validate(self, chat_id, username=None):
        if self.bound_chat_id is None:
            self.bind(chat_id, username)
            return True

        if self.is_expired():
            self.bind(chat_id, username)
            return True

        if str(chat_id) != self.bound_chat_id:
            return False

        if self.bound_username:
            if (username or "").strip().lower() != self.bound_username:
                return False

        return True

    def reset(self):
        self.bound_chat_id = None
        self.bound_username = None
        self.bound_at = None