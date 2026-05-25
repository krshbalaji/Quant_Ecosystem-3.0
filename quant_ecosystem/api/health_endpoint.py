class HealthEndpoint:

    def status(self):
        return {
            "status": "HEALTHY",
        }


health_endpoint = HealthEndpoint()