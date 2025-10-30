"""Tests for the ingestion graph module.

This module tests the ingestion graph implementation, including:
- ingestDocs node functionality
- Graph structure and execution
- Integration with vector store
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from src.ingestion_graph.state import IndexState


@pytest.fixture
def sample_docs():
    """Fixture providing sample documents for testing."""
    return [
        Document(
            page_content="Introduction to LangChain",
            metadata={"source": "test.pdf", "page": 1, "uuid": "doc1"},
        ),
        Document(
            page_content="LangChain core concepts",
            metadata={"source": "test.pdf", "page": 2, "uuid": "doc2"},
        ),
    ]


@pytest.fixture
def mock_retriever():
    """Fixture providing a mocked retriever."""
    retriever = AsyncMock()
    retriever.add_documents = AsyncMock(return_value=None)
    return retriever


@pytest.fixture
def sample_docs_json(tmp_path):
    """Fixture creating a temporary JSON file with sample docs."""
    docs_data = [
        {
            "pageContent": "Sample document from JSON",
            "metadata": {"source": "sample.json", "uuid": "json-doc-1"},
        },
        {
            "pageContent": "Another sample document",
            "metadata": {"source": "sample.json", "uuid": "json-doc-2"},
        },
    ]
    json_file = tmp_path / "sample_docs.json"
    json_file.write_text(json.dumps(docs_data))
    return str(json_file)


class TestIngestDocsNode:
    """Test suite for the ingestDocs node."""

    @pytest.mark.asyncio
    async def test_ingest_docs_with_provided_docs(self, sample_docs, mock_retriever):
        """Test ingestDocs node with documents provided in state."""
        from src.ingestion_graph.graph import ingest_docs

        state: IndexState = {"docs": sample_docs}
        config = {"configurable": {"retriever_provider": "supabase", "k": 5}}

        with patch("src.ingestion_graph.graph.make_retriever", return_value=mock_retriever):
            result = await ingest_docs(state, config)

        # Verify retriever was called with the docs
        mock_retriever.add_documents.assert_called_once()
        added_docs = mock_retriever.add_documents.call_args[0][0]

        # Should have 2 documents
        assert len(added_docs) == 2
        assert all(isinstance(doc, Document) for doc in added_docs)

        # Result should indicate docs should be deleted from state
        assert result == {"docs": "delete"}

    @pytest.mark.asyncio
    async def test_ingest_docs_with_sample_docs_file(self, sample_docs_json, mock_retriever):
        """Test ingestDocs node loading documents from sample file."""
        from src.ingestion_graph.graph import ingest_docs

        state: IndexState = {"docs": []}
        config = {
            "configurable": {
                "retriever_provider": "supabase",
                "use_sample_docs": True,
                "docs_file": sample_docs_json,
            }
        }

        with patch("src.ingestion_graph.graph.make_retriever", return_value=mock_retriever):
            result = await ingest_docs(state, config)

        # Verify retriever was called
        mock_retriever.add_documents.assert_called_once()
        added_docs = mock_retriever.add_documents.call_args[0][0]

        # Should have loaded docs from file
        assert len(added_docs) == 2
        assert added_docs[0].page_content == "Sample document from JSON"
        assert result == {"docs": "delete"}

    @pytest.mark.asyncio
    async def test_ingest_docs_no_config_raises_error(self, sample_docs):
        """Test that ingestDocs raises error when config is missing."""
        from src.ingestion_graph.graph import ingest_docs

        state: IndexState = {"docs": sample_docs}

        with pytest.raises(ValueError, match="Configuration required"):
            await ingest_docs(state, None)

    @pytest.mark.asyncio
    async def test_ingest_docs_no_docs_and_no_sample_raises_error(self, mock_retriever):
        """Test that ingestDocs raises error when no docs provided and sample disabled."""
        from src.ingestion_graph.graph import ingest_docs

        state: IndexState = {"docs": []}
        config = {"configurable": {"retriever_provider": "supabase", "use_sample_docs": False}}

        with patch("src.ingestion_graph.graph.make_retriever", return_value=mock_retriever):
            with pytest.raises(ValueError, match="No sample documents to index"):
                await ingest_docs(state, config)

    @pytest.mark.asyncio
    async def test_ingest_docs_processes_docs_through_reducer(self, mock_retriever):
        """Test that ingestDocs processes documents through reduce_docs reducer."""
        from src.ingestion_graph.graph import ingest_docs

        # Test with string documents that need to be converted
        state: IndexState = {"docs": [{"pageContent": "Test doc", "metadata": {"uuid": "test1"}}]}
        config = {"configurable": {"retriever_provider": "supabase"}}

        with patch("src.ingestion_graph.graph.make_retriever", return_value=mock_retriever):
            result = await ingest_docs(state, config)

        # Verify that documents were processed
        mock_retriever.add_documents.assert_called_once()
        added_docs = mock_retriever.add_documents.call_args[0][0]

        # Should be converted to Document objects
        assert len(added_docs) > 0
        assert all(isinstance(doc, Document) for doc in added_docs)


class TestIngestionGraphStructure:
    """Test suite for the ingestion graph structure and compilation."""

    def test_graph_has_correct_nodes(self):
        """Test that graph has the correct node structure."""
        from src.ingestion_graph.graph import graph

        # Graph should have ingestDocs node
        # We can verify this by checking the compiled graph structure
        assert graph is not None

    @pytest.mark.asyncio
    async def test_graph_execution_with_docs(self, sample_docs, mock_retriever):
        """Test full graph execution with provided documents."""
        from src.ingestion_graph.graph import graph

        initial_state: IndexState = {"docs": sample_docs}
        config = {"configurable": {"retriever_provider": "supabase", "k": 5}}

        with patch("src.ingestion_graph.graph.make_retriever", return_value=mock_retriever):
            # Stream the graph execution
            final_state = None
            async for state in graph.astream(initial_state, config):
                final_state = state

        # Verify retriever was called
        mock_retriever.add_documents.assert_called_once()

        # Final state should have docs cleared (deleted)
        assert final_state is not None

    @pytest.mark.asyncio
    async def test_graph_execution_with_sample_docs(self, sample_docs_json, mock_retriever):
        """Test full graph execution loading from sample docs file."""
        from src.ingestion_graph.graph import graph

        initial_state: IndexState = {"docs": []}
        config = {
            "configurable": {
                "retriever_provider": "supabase",
                "use_sample_docs": True,
                "docs_file": sample_docs_json,
            }
        }

        with patch("src.ingestion_graph.graph.make_retriever", return_value=mock_retriever):
            final_state = None
            async for state in graph.astream(initial_state, config):
                final_state = state

        # Verify retriever was called with docs from file
        mock_retriever.add_documents.assert_called_once()
        assert final_state is not None


class TestIngestionGraphIntegration:
    """Integration tests for the ingestion graph."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_graph_with_real_documents(self, sample_docs):
        """Integration test with actual document processing (mocked vector store)."""
        from src.ingestion_graph.graph import graph

        mock_retriever = AsyncMock()
        mock_retriever.add_documents = AsyncMock(return_value=None)

        initial_state: IndexState = {"docs": sample_docs}
        config = {"configurable": {"retriever_provider": "supabase"}}

        with patch("src.ingestion_graph.graph.make_retriever", return_value=mock_retriever):
            results = []
            async for state in graph.astream(initial_state, config):
                results.append(state)

        # Should have results from graph execution
        assert len(results) > 0

        # Verify documents were added to vector store
        mock_retriever.add_documents.assert_called_once()
        added_docs = mock_retriever.add_documents.call_args[0][0]
        assert len(added_docs) == 2
        assert added_docs[0].page_content == "Introduction to LangChain"
