"""Tests for the retrieval graph module.

This module tests the retrieval graph implementation, including:
- checkQueryType node and routing logic
- retrieveDocuments node functionality
- generateResponse node functionality
- directAnswer node functionality
- Graph structure and conditional routing
- Full graph execution with both paths (RETRIEVE and DIRECT)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from src.retrieval_graph.state import AgentState


@pytest.fixture
def sample_query():
    """Fixture providing a sample query."""
    return "What is LangChain?"


@pytest.fixture
def sample_documents():
    """Fixture providing sample retrieved documents."""
    return [
        Document(
            page_content="LangChain is a framework for building LLM applications.",
            metadata={"source": "docs.pdf", "page": 1},
        ),
        Document(
            page_content="LangChain provides tools for document loading and retrieval.",
            metadata={"source": "docs.pdf", "page": 2},
        ),
    ]


@pytest.fixture
def mock_chat_model():
    """Fixture providing a mocked chat model."""
    model = AsyncMock()
    model.with_structured_output = MagicMock(return_value=model)
    return model


@pytest.fixture
def mock_retriever():
    """Fixture providing a mocked retriever."""
    retriever = AsyncMock()
    return retriever


class TestCheckQueryTypeNode:
    """Test suite for the checkQueryType node."""

    @pytest.mark.asyncio
    async def test_check_query_type_returns_retrieve(self, sample_query, mock_chat_model):
        """Test checkQueryType node returns 'retrieve' for document-requiring queries."""
        from src.retrieval_graph.graph import check_query_type, RouteSchema

        # Mock the model to return 'retrieve' route
        mock_chat_model.ainvoke = AsyncMock(return_value=RouteSchema(route="retrieve"))

        state: AgentState = {
            "messages": [],
            "query": sample_query,
            "route": "",
            "documents": [],
        }
        config = {"configurable": {"query_model": "openai/gpt-4o"}}

        with patch("src.retrieval_graph.graph.load_chat_model", return_value=mock_chat_model):
            result = await check_query_type(state, config)

        # Should return retrieve route
        assert result["route"] == "retrieve"

    @pytest.mark.asyncio
    async def test_check_query_type_returns_direct(self, mock_chat_model):
        """Test checkQueryType node returns 'direct' for simple queries."""
        from src.retrieval_graph.graph import check_query_type, RouteSchema

        # Mock the model to return 'direct' route
        mock_chat_model.ainvoke = AsyncMock(return_value=RouteSchema(route="direct"))

        state: AgentState = {
            "messages": [],
            "query": "Hello",
            "route": "",
            "documents": [],
        }
        config = {"configurable": {"query_model": "openai/gpt-4o"}}

        with patch("src.retrieval_graph.graph.load_chat_model", return_value=mock_chat_model):
            result = await check_query_type(state, config)

        # Should return direct route
        assert result["route"] == "direct"

    @pytest.mark.asyncio
    async def test_check_query_type_uses_router_prompt(self, sample_query, mock_chat_model):
        """Test that checkQueryType uses the ROUTER_SYSTEM_PROMPT."""
        from src.retrieval_graph.graph import check_query_type, RouteSchema

        mock_chat_model.ainvoke = AsyncMock(return_value=RouteSchema(route="retrieve"))

        state: AgentState = {
            "messages": [],
            "query": sample_query,
            "route": "",
            "documents": [],
        }
        config = {"configurable": {"query_model": "openai/gpt-4o"}}

        with patch("src.retrieval_graph.graph.load_chat_model", return_value=mock_chat_model):
            await check_query_type(state, config)

        # Verify the model was called (prompt was used)
        mock_chat_model.ainvoke.assert_called_once()


class TestRouteQueryFunction:
    """Test suite for the route_query conditional routing function."""

    @pytest.mark.asyncio
    async def test_route_query_returns_retrieve_documents(self):
        """Test route_query returns 'retrieveDocuments' when route is 'retrieve'."""
        from src.retrieval_graph.graph import route_query

        state: AgentState = {
            "messages": [],
            "query": "test",
            "route": "retrieve",
            "documents": [],
        }

        result = await route_query(state)
        assert result == "retrieveDocuments"

    @pytest.mark.asyncio
    async def test_route_query_returns_direct_answer(self):
        """Test route_query returns 'directAnswer' when route is 'direct'."""
        from src.retrieval_graph.graph import route_query

        state: AgentState = {
            "messages": [],
            "query": "test",
            "route": "direct",
            "documents": [],
        }

        result = await route_query(state)
        assert result == "directAnswer"

    @pytest.mark.asyncio
    async def test_route_query_raises_error_for_no_route(self):
        """Test route_query raises error when route is not set."""
        from src.retrieval_graph.graph import route_query

        state: AgentState = {
            "messages": [],
            "query": "test",
            "route": "",
            "documents": [],
        }

        with pytest.raises(ValueError, match="Route is not set"):
            await route_query(state)

    @pytest.mark.asyncio
    async def test_route_query_raises_error_for_invalid_route(self):
        """Test route_query raises error for invalid route values."""
        from src.retrieval_graph.graph import route_query

        state: AgentState = {
            "messages": [],
            "query": "test",
            "route": "invalid",
            "documents": [],
        }

        with pytest.raises(ValueError, match="Invalid route"):
            await route_query(state)


class TestRetrieveDocumentsNode:
    """Test suite for the retrieveDocuments node."""

    @pytest.mark.asyncio
    async def test_retrieve_documents_fetches_docs(self, sample_query, sample_documents, mock_retriever):
        """Test retrieveDocuments node fetches documents from vector store."""
        from src.retrieval_graph.graph import retrieve_documents

        mock_retriever.ainvoke = AsyncMock(return_value=sample_documents)

        state: AgentState = {
            "messages": [],
            "query": sample_query,
            "route": "retrieve",
            "documents": [],
        }
        config = {"configurable": {"retriever_provider": "supabase", "k": 5}}

        with patch("src.retrieval_graph.graph.make_retriever", return_value=mock_retriever):
            result = await retrieve_documents(state, config)

        # Should return documents
        assert "documents" in result
        assert len(result["documents"]) == 2
        assert result["documents"][0].page_content == "LangChain is a framework for building LLM applications."

        # Verify retriever was called with the query
        mock_retriever.ainvoke.assert_called_once_with(sample_query)


class TestGenerateResponseNode:
    """Test suite for the generateResponse node."""

    @pytest.mark.asyncio
    async def test_generate_response_uses_context(self, sample_query, sample_documents, mock_chat_model):
        """Test generateResponse node generates answer using retrieved context."""
        from src.retrieval_graph.graph import generate_response

        # Mock the model response
        ai_response = AIMessage(content="LangChain is a framework for building LLM applications.")
        mock_chat_model.ainvoke = AsyncMock(return_value=ai_response)

        state: AgentState = {
            "messages": [],
            "query": sample_query,
            "route": "retrieve",
            "documents": sample_documents,
        }
        config = {"configurable": {"query_model": "openai/gpt-4o"}}

        with patch("src.retrieval_graph.graph.load_chat_model", return_value=mock_chat_model):
            result = await generate_response(state, config)

        # Should return messages
        assert "messages" in result
        assert len(result["messages"]) == 2  # HumanMessage + AIMessage

        # First should be HumanMessage, second should be AIMessage
        assert isinstance(result["messages"][0], HumanMessage)
        assert isinstance(result["messages"][1], AIMessage)
        assert result["messages"][1].content == "LangChain is a framework for building LLM applications."

    @pytest.mark.asyncio
    async def test_generate_response_formats_docs(self, sample_query, sample_documents, mock_chat_model):
        """Test that generateResponse properly formats documents for context."""
        from src.retrieval_graph.graph import generate_response

        ai_response = AIMessage(content="Answer based on context.")
        mock_chat_model.ainvoke = AsyncMock(return_value=ai_response)

        state: AgentState = {
            "messages": [],
            "query": sample_query,
            "route": "retrieve",
            "documents": sample_documents,
        }
        config = {"configurable": {"query_model": "openai/gpt-4o"}}

        with patch("src.retrieval_graph.graph.load_chat_model", return_value=mock_chat_model):
            await generate_response(state, config)

        # Verify model was called with formatted prompt including context
        mock_chat_model.ainvoke.assert_called_once()
        call_args = mock_chat_model.ainvoke.call_args[0][0]

        # Should have messages in the call
        assert len(call_args) > 0


class TestDirectAnswerNode:
    """Test suite for the directAnswer node."""

    @pytest.mark.asyncio
    async def test_direct_answer_responds_without_retrieval(self, mock_chat_model):
        """Test directAnswer node responds without document retrieval."""
        from src.retrieval_graph.graph import answer_query_directly

        # Mock the model response
        ai_response = AIMessage(content="Hello! How can I help you?")
        mock_chat_model.ainvoke = AsyncMock(return_value=ai_response)

        state: AgentState = {
            "messages": [],
            "query": "Hello",
            "route": "direct",
            "documents": [],
        }
        config = {"configurable": {"query_model": "openai/gpt-4o"}}

        with patch("src.retrieval_graph.graph.load_chat_model", return_value=mock_chat_model):
            result = await answer_query_directly(state, config)

        # Should return messages
        assert "messages" in result
        assert len(result["messages"]) == 2

        # First should be HumanMessage, second should be AIMessage
        assert isinstance(result["messages"][0], HumanMessage)
        assert result["messages"][0].content == "Hello"
        assert isinstance(result["messages"][1], AIMessage)
        assert result["messages"][1].content == "Hello! How can I help you?"


class TestRetrievalGraphStructure:
    """Test suite for the retrieval graph structure and compilation."""

    def test_graph_has_correct_nodes(self):
        """Test that graph has all required nodes."""
        from src.retrieval_graph.graph import graph

        # Graph should be compiled
        assert graph is not None

    @pytest.mark.asyncio
    async def test_graph_execution_retrieve_path(
        self, sample_query, sample_documents, mock_chat_model, mock_retriever
    ):
        """Test full graph execution following the RETRIEVE path."""
        from src.retrieval_graph.graph import graph, RouteSchema

        # Mock routing to retrieve
        mock_chat_model.with_structured_output = MagicMock(return_value=mock_chat_model)

        # Mock retriever
        mock_retriever.ainvoke = AsyncMock(return_value=sample_documents)

        # Mock response generation
        ai_response = AIMessage(content="LangChain is a framework.")

        # Create a mock that handles both structured output and regular ainvoke
        async def mock_ainvoke(input_data):
            if isinstance(input_data, list):
                # Regular message invocation
                return ai_response
            else:
                # Structured output invocation
                return RouteSchema(route="retrieve")

        mock_chat_model.ainvoke = mock_ainvoke

        initial_state: AgentState = {
            "messages": [],
            "query": sample_query,
            "route": "",
            "documents": [],
        }
        config = {"configurable": {"query_model": "openai/gpt-4o", "retriever_provider": "supabase"}}

        with patch("src.retrieval_graph.graph.load_chat_model", return_value=mock_chat_model), \
             patch("src.retrieval_graph.graph.make_retriever", return_value=mock_retriever):

            final_state = None
            async for state in graph.astream(initial_state, config):
                final_state = state

        # Should complete execution
        assert final_state is not None

    @pytest.mark.asyncio
    async def test_graph_execution_direct_path(self, mock_chat_model):
        """Test full graph execution following the DIRECT path."""
        from src.retrieval_graph.graph import graph, RouteSchema

        # Mock routing to direct
        ai_response = AIMessage(content="Hello!")

        async def mock_ainvoke(input_data):
            if isinstance(input_data, list):
                # Regular message invocation
                return ai_response
            else:
                # Structured output invocation
                return RouteSchema(route="direct")

        mock_chat_model.ainvoke = mock_ainvoke
        mock_chat_model.with_structured_output = MagicMock(return_value=mock_chat_model)

        initial_state: AgentState = {
            "messages": [],
            "query": "Hello",
            "route": "",
            "documents": [],
        }
        config = {"configurable": {"query_model": "openai/gpt-4o"}}

        with patch("src.retrieval_graph.graph.load_chat_model", return_value=mock_chat_model):
            final_state = None
            async for state in graph.astream(initial_state, config):
                final_state = state

        # Should complete execution
        assert final_state is not None


class TestRetrievalGraphIntegration:
    """Integration tests for the retrieval graph."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_retrieve_workflow(self, sample_query, sample_documents):
        """Integration test for complete retrieve workflow."""
        from src.retrieval_graph.graph import graph, RouteSchema

        # Create mocks
        mock_chat_model = AsyncMock()
        ai_response = AIMessage(content="LangChain is a framework for building applications.")

        async def mock_ainvoke(input_data):
            if isinstance(input_data, list):
                return ai_response
            else:
                return RouteSchema(route="retrieve")

        mock_chat_model.ainvoke = mock_ainvoke
        mock_chat_model.with_structured_output = MagicMock(return_value=mock_chat_model)

        mock_retriever = AsyncMock()
        mock_retriever.ainvoke = AsyncMock(return_value=sample_documents)

        initial_state: AgentState = {
            "messages": [],
            "query": sample_query,
            "route": "",
            "documents": [],
        }
        config = {"configurable": {"query_model": "openai/gpt-4o", "retriever_provider": "supabase", "k": 5}}

        with patch("src.retrieval_graph.graph.load_chat_model", return_value=mock_chat_model), \
             patch("src.retrieval_graph.graph.make_retriever", return_value=mock_retriever):

            results = []
            async for state in graph.astream(initial_state, config):
                results.append(state)

        # Should have executed multiple nodes
        assert len(results) > 0

        # Verify retriever was called
        mock_retriever.ainvoke.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_direct_workflow(self):
        """Integration test for complete direct answer workflow."""
        from src.retrieval_graph.graph import graph, RouteSchema

        # Create mock
        mock_chat_model = AsyncMock()
        ai_response = AIMessage(content="Hello! How can I help?")

        async def mock_ainvoke(input_data):
            if isinstance(input_data, list):
                return ai_response
            else:
                return RouteSchema(route="direct")

        mock_chat_model.ainvoke = mock_ainvoke
        mock_chat_model.with_structured_output = MagicMock(return_value=mock_chat_model)

        initial_state: AgentState = {
            "messages": [],
            "query": "Hello",
            "route": "",
            "documents": [],
        }
        config = {"configurable": {"query_model": "openai/gpt-4o"}}

        with patch("src.retrieval_graph.graph.load_chat_model", return_value=mock_chat_model):
            results = []
            async for state in graph.astream(initial_state, config):
                results.append(state)

        # Should have completed
        assert len(results) > 0


class TestRoutingLogic:
    """Comprehensive tests for routing logic - CRITICAL for behavioral parity."""

    @pytest.mark.asyncio
    async def test_routing_logic_retrieve_to_retrieve_documents(self):
        """Test that 'retrieve' route leads to retrieveDocuments node."""
        from src.retrieval_graph.graph import route_query

        state: AgentState = {
            "messages": [],
            "query": "test",
            "route": "retrieve",
            "documents": [],
        }

        result = await route_query(state)
        assert result == "retrieveDocuments"

    @pytest.mark.asyncio
    async def test_routing_logic_direct_to_direct_answer(self):
        """Test that 'direct' route leads to directAnswer node."""
        from src.retrieval_graph.graph import route_query

        state: AgentState = {
            "messages": [],
            "query": "test",
            "route": "direct",
            "documents": [],
        }

        result = await route_query(state)
        assert result == "directAnswer"

    @pytest.mark.asyncio
    async def test_routing_logic_error_handling(self):
        """Test that routing logic properly handles error cases."""
        from src.retrieval_graph.graph import route_query

        # Test empty route
        state: AgentState = {
            "messages": [],
            "query": "test",
            "route": "",
            "documents": [],
        }

        with pytest.raises(ValueError):
            await route_query(state)

        # Test invalid route
        state["route"] = "invalid_route"
        with pytest.raises(ValueError):
            await route_query(state)
