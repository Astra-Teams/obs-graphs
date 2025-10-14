"""Mock Redis client for offline development and testing."""

import fakeredis


class MockRedisClient:
    """
    Mock implementation of Redis client using fakeredis.

    This mock client provides an in-memory Redis-compatible interface
    using the fakeredis library, allowing development without a Redis server.
    """

    @staticmethod
    def get_client():
        """
        Get a fake Redis client that operates in memory.

        Returns:
            FakeRedis client instance compatible with redis.Redis interface.
        """
        print("[MockRedisClient] get_client() called - returning FakeRedis instance")
        return fakeredis.FakeRedis(decode_responses=True)
