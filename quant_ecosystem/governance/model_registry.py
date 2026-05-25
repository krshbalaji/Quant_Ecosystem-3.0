class ModelRegistry:

    def __init__(self):
        self._models = {}

    def register(
        self,
        model_name,
        version,
        model_type,
        metadata=None,
    ):
        payload = {
            "model_name": model_name,
            "version": version,
            "model_type": model_type,
            "metadata": metadata or {},
            "active": True,
        }

        self._models[
            f"{model_name}:{version}"
        ] = payload

        return payload

    def get(
        self,
        model_name,
        version,
    ):
        return self._models.get(
            f"{model_name}:{version}"
        )

    def active_models(self):
        return [
            x
            for x in self._models.values()
            if x["active"]
        ]

    def deactivate(
        self,
        model_name,
        version,
    ):
        key = f"{model_name}:{version}"

        if key in self._models:
            self._models[key][
                "active"
            ] = False


model_registry = ModelRegistry()