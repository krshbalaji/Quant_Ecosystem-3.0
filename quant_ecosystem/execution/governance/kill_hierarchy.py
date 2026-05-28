class KillHierarchy:
    """
    Institutional hierarchical kill governance.
    """

    def __init__(self):

        self._global_kill = False

        self._broker_kills = set()

        self._strategy_kills = set()

        self._symbol_kills = set()

        self._account_kills = set()

    def activate_global(self):
        self._global_kill = True

    def clear_global(self):
        self._global_kill = False

    def kill_broker(
        self,
        broker_name,
    ):
        self._broker_kills.add(
            broker_name.upper()
        )

    def clear_broker(
        self,
        broker_name,
    ):
        self._broker_kills.discard(
            broker_name.upper()
        )

    def kill_strategy(
        self,
        strategy,
    ):
        self._strategy_kills.add(
            strategy.upper()
        )

    def clear_strategy(
        self,
        strategy,
    ):
        self._strategy_kills.discard(
            strategy.upper()
        )

    def kill_symbol(
        self,
        symbol,
    ):
        self._symbol_kills.add(
            symbol.upper()
        )

    def clear_symbol(
        self,
        symbol,
    ):
        self._symbol_kills.discard(
            symbol.upper()
        )

    def kill_account(
        self,
        account_id,
    ):
        self._account_kills.add(
            str(account_id)
        )

    def clear_account(
        self,
        account_id,
    ):
        self._account_kills.discard(
            str(account_id)
        )

    def blocked(
        self,
        *,
        broker_name="",
        strategy="",
        symbol="",
        account_id="",
    ):

        if self._global_kill:
            return True

        if (
            broker_name.upper()
            in self._broker_kills
        ):
            return True

        if (
            strategy.upper()
            in self._strategy_kills
        ):
            return True

        if (
            symbol.upper()
            in self._symbol_kills
        ):
            return True

        if (
            str(account_id)
            in self._account_kills
        ):
            return True

        return False