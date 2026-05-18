def pytest_configure(config) -> None:
    config.addinivalue_line(
        "markers",
        "real_provider: tests that make real AI provider calls and may spend money",
    )
