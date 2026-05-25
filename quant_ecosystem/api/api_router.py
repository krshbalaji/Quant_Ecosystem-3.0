from quant_ecosystem.api.health_endpoint import (
    health_endpoint,
)

from quant_ecosystem.api.runtime_endpoint import (
    runtime_endpoint,
)

from quant_ecosystem.api.execution_endpoint import (
    execution_endpoint,
)

from quant_ecosystem.api.governance_endpoint import (
    governance_endpoint,
)

from quant_ecosystem.api.orchestration_endpoint import (
    orchestration_endpoint,
)


class ApiRouter:

    def route(
        self,
        endpoint,
        action=None,
        payload=None,
    ):
        if endpoint == "health":
            return health_endpoint.status()

        if endpoint == "runtime":
            return getattr(
                runtime_endpoint,
                action,
            )()

        if endpoint == "execution":
            return execution_endpoint.submit(
                payload
            )

        if endpoint == "governance":
            return governance_endpoint.authorize(
                payload["token"],
                payload["role"],
                payload["action"],
            )

        if endpoint == "orchestration":
            return orchestration_endpoint.execute(
                payload["steps"]
            )

        raise ValueError(
            f"Unknown endpoint: {endpoint}"
        )


api_router = ApiRouter()