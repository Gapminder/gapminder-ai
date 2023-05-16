def test_lib_import_statement() -> None:
    import lib  # noqa: F401, I2000

    assert "Empty assert to ensure pytest passes as long as the above import succeeds."
