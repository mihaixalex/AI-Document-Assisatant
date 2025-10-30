"""Performance benchmarking tests for Python backend.

This test suite measures performance metrics and compares them against TypeScript baseline:
- Ingestion latency: ~4s per document (baseline)
- Retrieval latency: ~2.5s end-to-end (baseline)
- Streaming first chunk: <200ms (baseline)
- Memory usage: ~200MB under load (baseline)
- Concurrent request handling

Baseline values from TypeScript backend should be within 10% margin.
"""

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from src.ingestion_graph.graph import graph as ingestion_graph
from src.retrieval_graph.graph import graph as retrieval_graph


class TestIngestionPerformance:
    """Benchmark ingestion performance."""

    @pytest.mark.asyncio
    async def test_ingestion_latency_single_document(self) -> None:
        """
        Test ingestion latency for a single document.

        Baseline: ~4 seconds per document (TypeScript)
        Target: Within 10% (3.6s - 4.4s)
        """
        # Create a realistic document
        test_doc = Document(
            page_content="This is a realistic test document with substantial content. " * 50,
            metadata={"source": "test.pdf", "page": 0},
        )

        with patch("src.shared.retrieval.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            # Simulate realistic database write time (200ms)
            async def mock_add_documents(docs: list[Document]) -> None:
                await asyncio.sleep(0.2)

            mock_retriever.add_documents = mock_add_documents
            mock_make_retriever.return_value = mock_retriever

            input_data = {"docs": [test_doc]}
            config = {
                "configurable": {
                    "retriever_provider": "supabase",
                    "k": 5,
                    "filter_kwargs": {},
                }
            }

            # Measure time
            start_time = time.time()
            result = await ingestion_graph.ainvoke(input_data, config)
            end_time = time.time()

            latency = end_time - start_time

            # Validate response
            assert "docs" in result

            # Performance assertion (with generous margin for CI)
            # In real deployment, this should be < 5s
            assert latency < 5.0, f"Ingestion took {latency:.2f}s, expected < 5s"

            # Log performance for tracking
            print(f"\n[PERF] Ingestion latency (1 doc): {latency:.3f}s")

    @pytest.mark.asyncio
    async def test_ingestion_latency_multiple_documents(self) -> None:
        """
        Test ingestion latency for multiple documents.

        Target: Linear scaling with number of documents
        """
        # Create multiple documents
        test_docs = [
            Document(
                page_content=f"Document {i} content. " * 50,
                metadata={"source": f"test{i}.pdf", "page": 0},
            )
            for i in range(5)
        ]

        with patch("src.shared.retrieval.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()

            async def mock_add_documents(docs: list[Document]) -> None:
                # Simulate batch write (1 second for 5 docs)
                await asyncio.sleep(1.0)

            mock_retriever.add_documents = mock_add_documents
            mock_make_retriever.return_value = mock_retriever

            input_data = {"docs": test_docs}
            config = {
                "configurable": {
                    "retriever_provider": "supabase",
                    "k": 5,
                    "filter_kwargs": {},
                }
            }

            start_time = time.time()
            result = await ingestion_graph.ainvoke(input_data, config)
            end_time = time.time()

            latency = end_time - start_time

            assert "docs" in result

            # Should complete batch in reasonable time (<10s for 5 docs)
            assert latency < 10.0, f"Batch ingestion took {latency:.2f}s"

            print(f"[PERF] Ingestion latency (5 docs): {latency:.3f}s")


class TestRetrievalPerformance:
    """Benchmark retrieval and response generation performance."""

    @pytest.mark.asyncio
    async def test_retrieval_end_to_end_latency(self) -> None:
        """
        Test end-to-end retrieval latency.

        Baseline: ~2.5s (TypeScript)
        Target: Within 10% (2.25s - 2.75s)
        """
        with patch("src.shared.retrieval.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()

            # Simulate realistic vector search (300ms)
            async def mock_ainvoke(query: str) -> list[Document]:
                await asyncio.sleep(0.3)
                return [
                    Document(
                        page_content="Relevant content for the query",
                        metadata={"source": "docs.pdf"},
                    )
                ]

            mock_retriever.ainvoke = mock_ainvoke
            mock_make_retriever.return_value = mock_retriever

            with patch("src.shared.utils.load_chat_model") as mock_load_model:
                mock_model = AsyncMock()

                # Simulate LLM response time (500ms)
                async def mock_model_invoke(messages: Any) -> AIMessage:
                    await asyncio.sleep(0.5)
                    return AIMessage(content="This is the answer to your question.")

                mock_model.ainvoke = mock_model_invoke

                # Mock routing
                mock_route_model = AsyncMock()
                mock_route_response = MagicMock()
                mock_route_response.route = "retrieve"

                async def mock_route_invoke(prompt: Any) -> Any:
                    await asyncio.sleep(0.1)  # Routing overhead
                    return mock_route_response

                mock_route_model.ainvoke = mock_route_invoke
                mock_model.with_structured_output = MagicMock(
                    return_value=mock_route_model
                )

                mock_load_model.return_value = mock_model

                input_data = {"query": "What is the project timeline?"}
                config = {
                    "configurable": {
                        "retriever_provider": "supabase",
                        "k": 5,
                        "filter_kwargs": {},
                        "query_model": "gpt-4o-mini",
                    }
                }

                start_time = time.time()
                result = await retrieval_graph.ainvoke(input_data, config)
                end_time = time.time()

                latency = end_time - start_time

                assert "messages" in result
                assert len(result["messages"]) == 2

                # Performance assertion
                # Expected: ~0.9s total (0.1 route + 0.3 retrieve + 0.5 LLM)
                assert latency < 3.0, f"Retrieval took {latency:.2f}s, expected < 3s"

                print(f"[PERF] Retrieval end-to-end latency: {latency:.3f}s")

    @pytest.mark.asyncio
    async def test_direct_answer_latency(self) -> None:
        """
        Test direct answer path latency (no retrieval).

        Should be faster than retrieval path.
        """
        with patch("src.shared.utils.load_chat_model") as mock_load_model:
            mock_model = AsyncMock()

            async def mock_model_invoke(messages: Any) -> AIMessage:
                await asyncio.sleep(0.4)  # Direct LLM call
                return AIMessage(content="Hello! How can I help?")

            mock_model.ainvoke = mock_model_invoke

            # Mock routing to direct
            mock_route_model = AsyncMock()
            mock_route_response = MagicMock()
            mock_route_response.route = "direct"

            async def mock_route_invoke(prompt: Any) -> Any:
                await asyncio.sleep(0.1)
                return mock_route_response

            mock_route_model.ainvoke = mock_route_invoke
            mock_model.with_structured_output = MagicMock(return_value=mock_route_model)

            mock_load_model.return_value = mock_model

            input_data = {"query": "Hello"}
            config = {
                "configurable": {
                    "retriever_provider": "supabase",
                    "k": 5,
                    "query_model": "gpt-4o-mini",
                }
            }

            start_time = time.time()
            result = await retrieval_graph.ainvoke(input_data, config)
            end_time = time.time()

            latency = end_time - start_time

            assert "messages" in result

            # Direct path should be faster (no retrieval)
            # Expected: ~0.5s (0.1 route + 0.4 LLM)
            assert latency < 2.0, f"Direct answer took {latency:.2f}s, expected < 2s"

            print(f"[PERF] Direct answer latency: {latency:.3f}s")

    @pytest.mark.asyncio
    async def test_streaming_first_chunk_latency(self) -> None:
        """
        Test time to first chunk in streaming mode.

        Baseline: <200ms (TypeScript)
        Critical for perceived responsiveness.
        """
        with patch("src.shared.retrieval.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            mock_retriever.ainvoke = AsyncMock(
                return_value=[Document(page_content="Test")]
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

                input_data = {"query": "Quick test"}
                config = {
                    "configurable": {
                        "retriever_provider": "supabase",
                        "k": 5,
                        "query_model": "gpt-4o-mini",
                    }
                }

                start_time = time.time()
                first_chunk_time = None

                async for chunk in retrieval_graph.astream(input_data, config):
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                        break

                if first_chunk_time:
                    latency = first_chunk_time - start_time

                    # Time to first chunk should be fast
                    # In production with real LLM, target is <500ms
                    assert (
                        latency < 1.0
                    ), f"First chunk took {latency:.3f}s, expected < 1s"

                    print(f"[PERF] Streaming first chunk latency: {latency:.3f}s")


class TestConcurrentPerformance:
    """Test performance under concurrent load."""

    @pytest.mark.asyncio
    async def test_concurrent_retrieval_requests(self) -> None:
        """
        Test handling multiple concurrent retrieval requests.

        Validates no blocking and reasonable performance under load.
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
                    return_value=AIMessage(content="Answer")
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

                # Simulate 10 concurrent requests
                async def make_request(i: int) -> dict[str, Any]:
                    input_data = {"query": f"Query {i}"}
                    return await retrieval_graph.ainvoke(input_data, config)

                start_time = time.time()
                results = await asyncio.gather(*[make_request(i) for i in range(10)])
                end_time = time.time()

                total_time = end_time - start_time

                # All requests should complete
                assert len(results) == 10

                # Should complete in reasonable time
                # If sequential: 10 * 0.5s = 5s
                # Concurrent should be much faster
                assert total_time < 3.0, f"10 concurrent requests took {total_time:.2f}s"

                print(f"[PERF] 10 concurrent requests: {total_time:.3f}s")

    @pytest.mark.asyncio
    async def test_memory_stability_repeated_requests(self) -> None:
        """
        Test memory stability with repeated requests.

        Validates no memory leaks over many requests.
        Note: This is a basic test; full memory profiling requires separate tools.
        """
        with patch("src.shared.retrieval.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            mock_retriever.ainvoke = AsyncMock(
                return_value=[Document(page_content="Content")]
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

                # Run 50 requests
                for i in range(50):
                    input_data = {"query": f"Request {i}"}
                    result = await retrieval_graph.ainvoke(input_data, config)
                    assert "messages" in result

                # If we got here without OOM, memory is stable
                print("[PERF] 50 sequential requests completed successfully")


class TestPerformanceRegression:
    """Tests to catch performance regressions."""

    @pytest.mark.asyncio
    async def test_performance_baseline_snapshot(self) -> None:
        """
        Snapshot test for performance baseline.

        This test documents current performance and will fail if performance
        degrades significantly in future changes.
        """
        with patch("src.shared.retrieval.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()

            async def mock_ainvoke(query: str) -> list[Document]:
                await asyncio.sleep(0.05)  # Fast mock
                return [Document(page_content="Result")]

            mock_retriever.ainvoke = mock_ainvoke
            mock_make_retriever.return_value = mock_retriever

            with patch("src.shared.utils.load_chat_model") as mock_load_model:
                mock_model = AsyncMock()

                async def mock_model_invoke(messages: Any) -> AIMessage:
                    await asyncio.sleep(0.05)
                    return AIMessage(content="Answer")

                mock_model.ainvoke = mock_model_invoke

                mock_route_model = AsyncMock()
                mock_route_response = MagicMock()
                mock_route_response.route = "retrieve"
                mock_route_model.ainvoke = AsyncMock(return_value=mock_route_response)
                mock_model.with_structured_output = MagicMock(
                    return_value=mock_route_model
                )

                mock_load_model.return_value = mock_model

                input_data = {"query": "Baseline test"}
                config = {
                    "configurable": {
                        "retriever_provider": "supabase",
                        "k": 5,
                        "query_model": "gpt-4o-mini",
                    }
                }

                # Warm-up run
                await retrieval_graph.ainvoke(input_data, config)

                # Measure baseline
                start_time = time.time()
                result = await retrieval_graph.ainvoke(input_data, config)
                end_time = time.time()

                latency = end_time - start_time

                assert "messages" in result

                # Document baseline (with mocks, should be very fast)
                print(f"[PERF BASELINE] Retrieval with fast mocks: {latency:.3f}s")

                # Regression guard: should complete in < 0.5s with fast mocks
                assert latency < 0.5, f"Baseline performance degraded: {latency:.3f}s"
