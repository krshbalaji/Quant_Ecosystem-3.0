class CivilizationArchive:

    def __init__(self):

        self._records = []

    def preserve(
        self,
        record,
    ):

        self._records.append(
            record
        )

        self._records = (
            self._records[-10000:]
        )

    def latest(self):

        if not self._records:
            return None

        return (
            self._records[-1]
        )

    def history(self):

        return list(
            self._records
        )


civilization_archive = (
    CivilizationArchive()
)