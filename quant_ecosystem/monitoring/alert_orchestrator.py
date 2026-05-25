class AlertOrchestrator:

    def route(
        self,
        severity,
    ):
        routing = {
            "NORMAL": "LOG_ONLY",
            "WATCH": "OPS_ALERT",
            "HIGH": "TELEGRAM_ALERT",
            "CRITICAL": "ESCALATE",
        }

        return routing.get(
            severity,
            "LOG_ONLY",
        )

    def payload(
        self,
        title,
        severity,
        details,
    ):
        return {
            "title": title,
            "severity": severity,
            "route": self.route(
                severity
            ),
            "details": details,
        }

    def escalate(
        self,
        payload,
    ):
        if payload["severity"] == (
            "CRITICAL"
        ):
            payload["escalated"] = True
        else:
            payload["escalated"] = False

        return payload


alert_orchestrator = (
    AlertOrchestrator()
)