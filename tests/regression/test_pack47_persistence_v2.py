from quant_ecosystem.persistence import (
    sqlite_repository,
    file_repository,
    persistence_factory,
)


def setup_function():
    sqlite_repository.clear()
    file_repository.clear()


def test_sqlite_save_load():
    sqlite_repository.save(
        "risk",
        "HIGH",
    )

    assert (
        sqlite_repository.load(
            "risk"
        )
        == "HIGH"
    )


def test_file_save_load():
    file_repository.save(
        "state.json",
        "ACTIVE",
    )

    assert (
        file_repository.load(
            "state.json"
        )
        == "ACTIVE"
    )


def test_factory_sqlite():
    repo = persistence_factory.create(
        "sqlite"
    )

    assert repo is sqlite_repository


def test_factory_file():
    repo = persistence_factory.create(
        "file"
    )

    assert repo is file_repository


def test_invalid_backend():
    try:
        persistence_factory.create(
            "broken"
        )
        assert False
    except ValueError:
        assert True