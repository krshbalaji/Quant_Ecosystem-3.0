class CapabilityRegistry:

    def capabilities(self):
        return [
            "research",
            "portfolio",
            "backtest",
            "monitoring",
            "governance",
            "security",
            "persistence",
            "runtime",
            "workflow",
            "api",
            "deployment",
        ]


capability_registry = (
    CapabilityRegistry()
)