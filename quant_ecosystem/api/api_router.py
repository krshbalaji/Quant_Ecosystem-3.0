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
        payload_dict = payload or {}

        if endpoint == "health":
            return health_endpoint.status()

        if endpoint == "runtime":
            action_name = str(action or "")
            return getattr(
                runtime_endpoint,
                action_name,
            )()

        if endpoint == "execution":
            return execution_endpoint.submit(
                payload_dict
            )

        if endpoint == "governance":
            return governance_endpoint.authorize(
                payload_dict["token"],
                payload_dict["role"],
                payload_dict["action"],
            )

        if endpoint == "orchestration":
            return orchestration_endpoint.execute(
                payload_dict["steps"]
            )


api_router = ApiRouter()