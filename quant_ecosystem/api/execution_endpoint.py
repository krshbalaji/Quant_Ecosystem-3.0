class ExecutionEndpoint:

    def submit(
        self,
        order_payload,
    ):
        return {
            "accepted": True,
            "payload": order_payload,
        }


execution_endpoint = (
    ExecutionEndpoint()
)