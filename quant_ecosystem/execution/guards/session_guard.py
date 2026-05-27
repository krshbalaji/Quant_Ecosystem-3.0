class SessionGuard:
    """
    Institutional broker session governance.
    """

    def ensure_live_session(
        self,
        broker,
        broker_name,
    ):
        if not hasattr(
            broker,
            "is_authenticated",
        ):
            return

        if broker.is_authenticated():
            return

        try:
            broker.authenticate()

            if broker.is_authenticated():
                return

        except Exception:
            pass

        try:
            broker.refresh_session()

            if broker.is_authenticated():
                return

        except Exception:
            pass

        try:
            broker.invalidate_session()
        except Exception:
            pass

        raise RuntimeError(
            f"BROKER SESSION INVALID: {broker_name}"
        )