from quant_ecosystem.civilization.civilization_archive import (
    civilization_archive,
)


class HeritageAnalyzer:

    def eras(self):

        return [
            r.era_name
            for r in (
                civilization_archive
                .history()
            )
        ]


heritage_analyzer = (
    HeritageAnalyzer()
)