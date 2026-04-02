import time
import uuid
import logging

logger = logging.getLogger(__name__)


class ExecutionTokenAuthority:

    def __init__(self, registry=None, governor=None):

        self.registry = registry
        self.governor = governor

        self._tokens = {}
        self._epochs = {}

    def issue_token(self, strategy_id):

        sid = str(strategy_id).strip()

        if not sid:
            return None

        if self.governor and sid not in self.governor.get_active_ids():
            return None

        token = str(uuid.uuid4())

        self._tokens[sid] = token
        self._epochs[sid] = int(time.time())

        return token

    def get_activation_epoch(self, strategy_id):

        return self._epochs.get(strategy_id)

    def validate(self, strategy_id, token):

        sid = str(strategy_id).strip()

        if not sid:
            return False

        if self.governor and sid not in self.governor.get_active_ids():
            return False

        return self._tokens.get(sid) == token

    def invalidate(self, strategy_id):

        sid = str(strategy_id).strip()

        self._tokens.pop(sid, None)
        self._epochs.pop(sid, None)