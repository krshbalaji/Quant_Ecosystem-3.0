class StepRunner:

    def run(
        self,
        step,
    ):
        return step()


step_runner = StepRunner()