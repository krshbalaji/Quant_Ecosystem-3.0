class ReflectionArchive:

    def __init__(self):

        self._records = []

    def remember(
        self,
        record,
    ):

        self._records.append(
            record
        )

        self._records = (
            self._records[-10000:]
        )

    def history(self):

        return list(
            self._records
        )


reflection_archive = (
    ReflectionArchive()
)