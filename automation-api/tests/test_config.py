from lib.config import read_config


def test_config() -> None:
    config = read_config()

    assert len(config) > 0
