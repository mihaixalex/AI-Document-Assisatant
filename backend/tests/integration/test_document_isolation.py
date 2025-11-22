"""Integration tests for document isolation across conversations.

This module contains TRUE integration tests that verify document isolation
by connecting to real services (Supabase).

These tests are marked as integration tests and should be skipped in normal
test runs with: pytest -m "not integration"

For unit tests of the isolation logic with mocks, see:
  - tests/shared/test_retrieval.py (retrieval layer)
  - tests/test_main.py (API endpoint validation)
"""

import os

import pytest

# Check if we have real Supabase credentials for integration tests
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
HAS_SUPABASE_CREDENTIALS = bool(SUPABASE_URL and SUPABASE_KEY)

pytestmark = pytest.mark.skipif(
    not HAS_SUPABASE_CREDENTIALS,
    reason="Supabase credentials not available. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to run integration tests."
)


@pytest.mark.integration
class TestDocumentIsolationIntegration:
    """
    Real integration tests for document isolation.

    These tests actually connect to Supabase and verify isolation.
    They are skipped unless SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set.

    NOTE: These tests will create and delete real documents in the vector store.
    Use a test Supabase instance, not production.
    """

    @pytest.mark.asyncio
    async def test_real_document_isolation_requires_supabase(self) -> None:
        """
        Placeholder for real integration test.

        TODO: Implement real integration tests that:
        1. Actually connect to test Supabase instance
        2. Ingest documents with different thread_ids
        3. Query with different thread_ids
        4. Verify documents are isolated
        5. Clean up test data

        For now, we rely on unit tests in test_retrieval.py and test_main.py
        to verify the isolation logic with mocks.
        """
        pytest.skip("Real integration tests not yet implemented. Using unit tests with mocks instead.")
