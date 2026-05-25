from quant_ecosystem.persistence.sqlite_repository import (
    sqlite_repository,
)

from quant_ecosystem.persistence.file_repository import (
    file_repository,
)


class PersistenceFactory:

    def create(
        self,
        backend,
    ):
        mapping = {
            "sqlite": sqlite_repository,
            "file": file_repository,
        }

        if backend not in mapping:
            raise ValueError(
                f"Unknown backend: {backend}"
            )

        return mapping[backend]


persistence_factory = (
    PersistenceFactory()
)