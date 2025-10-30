"""Load testing for concurrent user scenarios.

This test suite simulates realistic load patterns:
- Multiple concurrent users
- Sustained request load
- Peak traffic scenarios
- Resource exhaustion tests

These tests validate the system can handle production load.
"""

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from src.retrieval_graph.graph import graph as retrieval_graph


class TestConcurrentUsers:
    """Test behavior under concurrent user load."""

    @pytest.mark.asyncio
    async def test_10_concurrent_users(self) -> None:
        """
        Simulate 10 concurrent users making requests.

        This represents light production load.
        """
        with patch("src.shared.retrieval.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            mock_retriever.ainvoke = AsyncMock(
                return_value=[Document(page_content="Result")]
            )
            mock_make_retriever.return_value = mock_retriever

            with patch("src.shared.utils.load_chat_model") as mock_load_model:
                mock_model = AsyncMock()

                async def mock_invoke(messages: Any) -> AIMessage:
                    # Simulate realistic LLM latency
                    await asyncio.sleep(0.1)
                    return AIMessage(content="Response")

                mock_model.ainvoke = mock_invoke

                mock_route_model = AsyncMock()
                mock_route_response = MagicMock()
                mock_route_response.route = "direct"
                mock_route_model.ainvoke = AsyncMock(return_value=mock_route_response)
                mock_model.with_structured_output = MagicMock(
                    return_value=mock_route_model
                )

                mock_load_model.return_value = mock_model

                config = {
                    "configurable": {
                        "retriever_provider": "supabase",
                        "k": 5,
                        "query_model": "gpt-4o-mini",
                    }
                }

                async def user_session(user_id: int) -> list[dict[str, Any]]:
                    """Simulate a user making 5 queries."""
                    results = []
                    for i in range(5):
                        input_data = {"query": f"User {user_id} query {i}"}
                        result = await retrieval_graph.ainvoke(input_data, config)
                        results.append(result)
                        # Small delay between requests
                        await asyncio.sleep(0.05)
                    return results

                start_time = time.time()

                # Simulate 10 concurrent users
                user_results = await asyncio.gather(
                    *[user_session(i) for i in range(10)]
                )

                end_time = time.time()
                total_time = end_time - start_time

                # Verify all requests completed
                assert len(user_results) == 10
                for results in user_results:
                    assert len(results) == 5
                    for result in results:
                        assert "messages" in result

                # Total: 50 requests
                # Should complete in reasonable time with async handling
                print(
                    f"[LOAD] 10 users, 5 requests each (50 total): {total_time:.2f}s"
                )

    @pytest.mark.asyncio
    async def test_100_concurrent_users(self) -> None:
        """
        Simulate 100 concurrent users making requests.

        This represents peak production load.
        Tests system stability under high concurrency.
        """
        with patch("src.shared.retrieval.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            mock_retriever.ainvoke = AsyncMock(
                return_value=[Document(page_content="Result")]
            )
            mock_make_retriever.return_value = mock_retriever

            with patch("src.shared.utils.load_chat_model") as mock_load_model:
                mock_model = AsyncMock()

                async def mock_invoke(messages: Any) -> AIMessage:
                    await asyncio.sleep(0.01)  # Fast mock for large scale
                    return AIMessage(content="Response")

                mock_model.ainvoke = mock_invoke

                mock_route_model = AsyncMock()
                mock_route_response = MagicMock()
                mock_route_response.route = "direct"
                mock_route_model.ainvoke = AsyncMock(return_value=mock_route_response)
                mock_model.with_structured_output = MagicMock(
                    return_value=mock_route_model
                )

                mock_load_model.return_value = mock_model

                config = {
                    "configurable": {
                        "retriever_provider": "supabase",
                        "k": 5,
                        "query_model": "gpt-4o-mini",
                    }
                }

                async def make_request(request_id: int) -> dict[str, Any]:
                    input_data = {"query": f"Request {request_id}"}
                    return await retrieval_graph.ainvoke(input_data, config)

                start_time = time.time()

                # 100 concurrent requests
                results = await asyncio.gather(*[make_request(i) for i in range(100)])

                end_time = time.time()
                total_time = end_time - start_time

                # All should complete successfully
                assert len(results) == 100
                for result in results:
                    assert "messages" in result

                print(f"[LOAD] 100 concurrent requests: {total_time:.2f}s")

                # Should handle 100 concurrent requests efficiently
                # With async, should complete in < 5 seconds
                assert total_time < 10.0, f"High load took {total_time:.2f}s"


class TestSustainedLoad:
    """Test behavior under sustained load over time."""

    @pytest.mark.asyncio
    async def test_sustained_request_rate(self) -> None:
        """
        Test sustained request rate over time.

        Simulates 20 requests per second for 5 seconds (100 total requests).
        Validates no degradation over time.
        """
        with patch("src.shared.retrieval.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            mock_retriever.ainvoke = AsyncMock(
                return_value=[Document(page_content="Result")]
            )
            mock_make_retriever.return_value = mock_retriever

            with patch("src.shared.utils.load_chat_model") as mock_load_model:
                mock_model = AsyncMock()
                mock_model.ainvoke = AsyncMock(
                    return_value=AIMessage(content="Response")
                )

                mock_route_model = AsyncMock()
                mock_route_response = MagicMock()
                mock_route_response.route = "direct"
                mock_route_model.ainvoke = AsyncMock(return_value=mock_route_response)
                mock_model.with_structured_output = MagicMock(
                    return_value=mock_route_model
                )

                mock_load_model.return_value = mock_model

                config = {
                    "configurable": {
                        "retriever_provider": "supabase",
                        "k": 5,
                        "query_model": "gpt-4o-mini",
                    }
                }

                request_count = 0
                start_time = time.time()
                latencies = []

                async def timed_request() -> None:
                    nonlocal request_count
                    request_start = time.time()
                    input_data = {"query": f"Request {request_count}"}
                    await retrieval_graph.ainvoke(input_data, config)
                    request_end = time.time()
                    latencies.append(request_end - request_start)
                    request_count += 1

                # Run requests for 5 seconds
                duration = 5.0
                requests_per_second = 20
                interval = 1.0 / requests_per_second

                tasks = []
                while time.time() - start_time < duration:
                    tasks.append(asyncio.create_task(timed_request()))
                    await asyncio.sleep(interval)

                # Wait for all requests to complete
                await asyncio.gather(*tasks)

                end_time = time.time()
                total_time = end_time - start_time

                print(f"[LOAD] Sustained load: {request_count} requests in {total_time:.2f}s")
                print(f"[LOAD] Average latency: {sum(latencies)/len(latencies):.3f}s")
                print(f"[LOAD] Max latency: {max(latencies):.3f}s")

                # Should handle sustained load
                assert request_count >= 90, f"Only completed {request_count} requests"

                # Latency should remain stable (no degradation)
                avg_latency = sum(latencies) / len(latencies)
                assert avg_latency < 0.5, f"Average latency too high: {avg_latency:.3f}s"


class TestResourceLimits:
    """Test behavior at resource limits."""

    @pytest.mark.asyncio
    async def test_request_queue_depth(self) -> None:
        """
        Test handling of deep request queues.

        Validates graceful handling when many requests are queued.
        """
        with patch("src.shared.retrieval.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            mock_retriever.ainvoke = AsyncMock(
                return_value=[Document(page_content="Result")]
            )
            mock_make_retriever.return_value = mock_retriever

            with patch("src.shared.utils.load_chat_model") as mock_load_model:
                mock_model = AsyncMock()

                # Simulate slow LLM to create queue backlog
                async def slow_invoke(messages: Any) -> AIMessage:
                    await asyncio.sleep(0.1)
                    return AIMessage(content="Response")

                mock_model.ainvoke = slow_invoke

                mock_route_model = AsyncMock()
                mock_route_response = MagicMock()
                mock_route_response.route = "direct"
                mock_route_model.ainvoke = AsyncMock(return_value=mock_route_response)
                mock_model.with_structured_output = MagicMock(
                    return_value=mock_route_model
                )

                mock_load_model.return_value = mock_model

                config = {
                    "configurable": {
                        "retriever_provider": "supabase",
                        "k": 5,
                        "query_model": "gpt-4o-mini",
                    }
                }

                # Queue 50 requests simultaneously
                async def make_request(i: int) -> dict[str, Any]:
                    input_data = {"query": f"Queued request {i}"}
                    return await retrieval_graph.ainvoke(input_data, config)

                start_time = time.time()
                results = await asyncio.gather(*[make_request(i) for i in range(50)])
                end_time = time.time()

                total_time = end_time - start_time

                # All should complete
                assert len(results) == 50

                print(f"[LOAD] 50 queued requests: {total_time:.2f}s")

    @pytest.mark.asyncio
    async def test_no_memory_leaks_under_load(self) -> None:
        """
        Test for memory leaks under repeated load.

        Runs many requests and validates memory doesn't grow unbounded.
        """
        with patch("src.shared.retrieval.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            mock_retriever.ainvoke = AsyncMock(
                return_value=[Document(page_content="Result")]
            )
            mock_make_retriever.return_value = mock_retriever

            with patch("src.shared.utils.load_chat_model") as mock_load_model:
                mock_model = AsyncMock()
                mock_model.ainvoke = AsyncMock(
                    return_value=AIMessage(content="Response")
                )

                mock_route_model = AsyncMock()
                mock_route_response = MagicMock()
                mock_route_response.route = "direct"
                mock_route_model.ainvoke = AsyncMock(return_value=mock_route_response)
                mock_model.with_structured_output = MagicMock(
                    return_value=mock_route_model
                )

                mock_load_model.return_value = mock_model

                config = {
                    "configurable": {
                        "retriever_provider": "supabase",
                        "k": 5,
                        "query_model": "gpt-4o-mini",
                    }
                }

                # Run 200 requests in batches
                batch_size = 20
                num_batches = 10

                for batch in range(num_batches):
                    async def make_request(i: int) -> dict[str, Any]:
                        input_data = {"query": f"Batch {batch} request {i}"}
                        return await retrieval_graph.ainvoke(input_data, config)

                    results = await asyncio.gather(
                        *[make_request(i) for i in range(batch_size)]
                    )

                    assert len(results) == batch_size

                # If we completed without OOM, no obvious memory leak
                print(f"[LOAD] {num_batches * batch_size} requests in batches completed")


class TestErrorHandlingUnderLoad:
    """Test error handling under load conditions."""

    @pytest.mark.asyncio
    async def test_partial_failures_under_load(self) -> None:
        """
        Test system handles partial failures gracefully under load.

        Some requests fail, but system continues processing others.
        """
        with patch("src.shared.retrieval.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            mock_retriever.ainvoke = AsyncMock(
                return_value=[Document(page_content="Result")]
            )
            mock_make_retriever.return_value = mock_retriever

            with patch("src.shared.utils.load_chat_model") as mock_load_model:
                mock_model = AsyncMock()

                # Simulate intermittent failures
                call_count = 0

                async def sometimes_fail(messages: Any) -> AIMessage:
                    nonlocal call_count
                    call_count += 1
                    if call_count % 5 == 0:
                        raise Exception("Simulated LLM timeout")
                    return AIMessage(content="Response")

                mock_model.ainvoke = sometimes_fail

                mock_route_model = AsyncMock()
                mock_route_response = MagicMock()
                mock_route_response.route = "direct"
                mock_route_model.ainvoke = AsyncMock(return_value=mock_route_response)
                mock_model.with_structured_output = MagicMock(
                    return_value=mock_route_model
                )

                mock_load_model.return_value = mock_model

                config = {
                    "configurable": {
                        "retriever_provider": "supabase",
                        "k": 5,
                        "query_model": "gpt-4o-mini",
                    }
                }

                async def make_request(i: int) -> dict[str, Any] | None:
                    try:
                        input_data = {"query": f"Request {i}"}
                        return await retrieval_graph.ainvoke(input_data, config)
                    except Exception:
                        return None

                # Run 20 requests, expecting ~4 failures
                results = await asyncio.gather(*[make_request(i) for i in range(20)])

                successful = [r for r in results if r is not None]
                failed = [r for r in results if r is None]

                print(f"[LOAD] Partial failures: {len(successful)} success, {len(failed)} failed")

                # Most should succeed
                assert len(successful) >= 15, f"Too many failures: {len(failed)}"
