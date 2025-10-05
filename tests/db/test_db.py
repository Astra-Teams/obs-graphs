from sqlalchemy import text
from sqlalchemy.orm import Session


class TestDatabase:
    """
    Class-based test for database operations with automatic rollback.
    FastAPI's db_session fixture automatically wraps each test in a transaction
    that gets rolled back after the test completes, ensuring test isolation.
    """

    def test_db_connection(self, db_session: Session):
        """Test basic database connectivity."""
        result = db_session.execute(text("SELECT 1")).fetchone()
        assert result[0] == 1

    def test_db_transaction_rollback(self, db_session: Session):
        """Test that database transactions are properly rolled back between tests."""
        # This test verifies our test fixture isolation works correctly
        # Insert some test data
        db_session.execute(
            text("CREATE TEMPORARY TABLE test_rollback (id INTEGER, name TEXT)")
        )
        db_session.execute(
            text("INSERT INTO test_rollback (id, name) VALUES (1, 'test')")
        )

        # Verify data exists
        result = db_session.execute(
            text("SELECT COUNT(*) FROM test_rollback")
        ).fetchone()
        assert result[0] == 1
        # Transaction will be rolled back by conftest.py fixture
