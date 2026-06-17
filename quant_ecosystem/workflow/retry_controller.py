class RetryController:

    def execute(
        self,
        func,
        retries=3,
    ):
        last_error = None

        for _ in range(retries):
            try:
                return func()
            except Exception as e:
                last_error = e

        if last_error is not None:
            raise last_error

        raise RuntimeError("retry controller exhausted")


retry_controller = RetryController()