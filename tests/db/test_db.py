class TestDatabase:
    """
    Class-based test for database operations with automatic rollback.
    FastAPI's db_session fixture automatically wraps each test in a transaction
    that gets rolled back after the test completes, ensuring test isolation.
    """

    pass
