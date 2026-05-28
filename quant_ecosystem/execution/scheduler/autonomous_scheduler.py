import time

from quant_ecosystem.execution.scheduler.execution_queue import (
    execution_queue,
)


class AutonomousScheduler:

    def schedule(
        self,
        delay_seconds,
        payload,
    ):

        execute_at = (
            time.time()
            + delay_seconds
        )

        execution_queue.schedule(
            execute_at,
            payload,
        )

    def poll(self):

        return (
            execution_queue.ready()
        )


autonomous_scheduler = (
    AutonomousScheduler()
)