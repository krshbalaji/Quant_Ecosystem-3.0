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

        raise last_error


retry_controller = RetryController()