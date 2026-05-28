from quant_ecosystem.execution.scheduler.autonomous_scheduler import (
    autonomous_scheduler,
)


class RetryGovernor:

    def schedule_retry(
        self,
        payload,
        retry_count,
    ):

        delay = min(
            60,
            max(
                1,
                retry_count * 5,
            ),
        )

        autonomous_scheduler.schedule(
            delay_seconds=delay,
            payload=payload,
        )


retry_governor = (
    RetryGovernor()
)