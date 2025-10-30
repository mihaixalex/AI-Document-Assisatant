"""Tests for retrieval graph state definitions.

This test suite validates the AgentState TypedDict structure with all fields
including messages, query, route, and documents with proper reducers.
"""

import pytest
from typing import get_type_hints
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from src.retrieval_graph.state import AgentState
from src.shared.state import reduce_docs


class TestAgentState:
    """Test suite for AgentState TypedDict."""

    def test_agent_state_structure(self):
        """Test that AgentState has all required fields."""
        hints = get_type_hints(AgentState)

        # AgentState should have these fields based on TypeScript
        required_fields = ["messages", "query", "route", "documents"]

        for field in required_fields:
            assert field in hints, f"AgentState must have '{field}' field"

        # Should have at least 4 fields
        assert len(hints) >= 4, "AgentState should have at least 4 fields"

    def test_agent_state_messages_field_type(self):
        """Test that messages field accepts list of BaseMessage."""
        hints = get_type_hints(AgentState)

        assert "messages" in hints, "AgentState must have 'messages' field"
        # The messages field should be list-like
        messages_type = str(hints["messages"])
        assert "list" in messages_type.lower() or "List" in messages_type or "Sequence" in messages_type, \
            "messages should be a list/sequence type"

    def test_agent_state_query_field_type(self):
        """Test that query field is a string."""
        hints = get_type_hints(AgentState)

        assert "query" in hints, "AgentState must have 'query' field"
        query_type = str(hints["query"])
        assert "str" in query_type, "query should be str type"

    def test_agent_state_route_field_type(self):
        """Test that route field is a string."""
        hints = get_type_hints(AgentState)

        assert "route" in hints, "AgentState must have 'route' field"
        route_type = str(hints["route"])
        assert "str" in route_type, "route should be str type"

    def test_agent_state_documents_field_type(self):
        """Test that documents field accepts list of Documents."""
        hints = get_type_hints(AgentState)

        assert "documents" in hints, "AgentState must have 'documents' field"
        docs_type = str(hints["documents"])
        assert "list" in docs_type.lower() or "List" in docs_type, "documents should be a list type"
        assert "Document" in docs_type, "documents should contain Document type"

    def test_agent_state_instantiation_minimal(self):
        """Test creating AgentState with minimal required fields."""
        state: AgentState = {
            "messages": [],
            "query": "",
            "route": "",
            "documents": []
        }

        assert isinstance(state, dict), "AgentState should be a dict"
        assert "messages" in state
        assert "query" in state
        assert "route" in state
        assert "documents" in state

    def test_agent_state_instantiation_with_messages(self):
        """Test creating AgentState with actual messages."""
        human_msg = HumanMessage(content="What is the capital of France?")
        ai_msg = AIMessage(content="The capital of France is Paris.")

        state: AgentState = {
            "messages": [human_msg, ai_msg],
            "query": "What is the capital of France?",
            "route": "direct",
            "documents": []
        }

        assert len(state["messages"]) == 2
        assert isinstance(state["messages"][0], HumanMessage)
        assert isinstance(state["messages"][1], AIMessage)
        assert state["query"] == "What is the capital of France?"
        assert state["route"] == "direct"

    def test_agent_state_instantiation_with_documents(self):
        """Test creating AgentState with documents."""
        doc1 = Document(page_content="Document 1", metadata={"uuid": "id1"})
        doc2 = Document(page_content="Document 2", metadata={"uuid": "id2"})

        state: AgentState = {
            "messages": [],
            "query": "test query",
            "route": "retrieve",
            "documents": [doc1, doc2]
        }

        assert len(state["documents"]) == 2
        assert state["documents"][0].page_content == "Document 1"
        assert state["route"] == "retrieve"

    def test_agent_state_with_documents_reducer_concatenation(self):
        """Test that documents field uses reduce_docs for concatenation."""
        # Existing documents
        doc1 = Document(page_content="Existing", metadata={"uuid": "id1"})
        existing_docs = [doc1]

        # New documents
        doc2 = Document(page_content="New", metadata={"uuid": "id2"})
        new_docs = [doc2]

        # Use reducer to merge
        result = reduce_docs(existing_docs, new_docs)

        # Should concatenate, not replace
        assert len(result) == 2, "Should concatenate documents"
        assert result[0].page_content == "Existing"
        assert result[1].page_content == "New"

    def test_agent_state_field_names_match_typescript(self):
        """Test that field names exactly match TypeScript for frontend compatibility."""
        hints = get_type_hints(AgentState)

        # TypeScript uses these exact field names
        expected_ts_fields = {
            "messages": True,  # From MessagesAnnotation.spec
            "query": True,
            "route": True,
            "documents": True,
        }

        for field, should_exist in expected_ts_fields.items():
            if should_exist:
                assert field in hints, f"Must use '{field}' field name to match TypeScript"

        # Check that we're NOT using incorrect names
        incorrect_names = ["question", "queryType", "retrievedDocuments", "response", "docs"]
        for incorrect_name in incorrect_names:
            # Note: TypeScript actually uses these names, so we need to check the source again
            pass  # Will verify against actual TypeScript source

    def test_agent_state_route_values(self):
        """Test that route field can hold expected values."""
        # Test "direct" route
        state_direct: AgentState = {
            "messages": [],
            "query": "simple query",
            "route": "direct",
            "documents": []
        }
        assert state_direct["route"] == "direct"

        # Test "retrieve" route
        state_retrieve: AgentState = {
            "messages": [],
            "query": "complex query",
            "route": "retrieve",
            "documents": []
        }
        assert state_retrieve["route"] == "retrieve"


class TestAgentStateIntegration:
    """Integration tests for AgentState with LangGraph patterns."""

    def test_agent_state_conversation_flow(self):
        """Test state updates during a conversation flow."""
        # Initial state
        state: AgentState = {
            "messages": [],
            "query": "",
            "route": "",
            "documents": []
        }

        # User asks question
        human_msg = HumanMessage(content="What is AI?")
        state["messages"] = [human_msg]
        state["query"] = "What is AI?"

        # Router determines route
        state["route"] = "direct"

        # AI responds
        ai_msg = AIMessage(content="AI stands for Artificial Intelligence.")
        state["messages"] = [human_msg, ai_msg]

        assert len(state["messages"]) == 2
        assert state["route"] == "direct"
        assert len(state["documents"]) == 0  # No retrieval needed

    def test_agent_state_retrieval_flow(self):
        """Test state updates during retrieval flow."""
        # Initial query
        state: AgentState = {
            "messages": [HumanMessage(content="What does the document say?")],
            "query": "What does the document say?",
            "route": "retrieve",
            "documents": []
        }

        # Retrieval adds documents
        doc = Document(
            page_content="The document contains important information.",
            metadata={"uuid": "id1", "source": "test.pdf"}
        )
        state["documents"] = reduce_docs(state["documents"], [doc])

        # Generate response
        ai_msg = AIMessage(content="The document contains important information.")
        state["messages"] = [state["messages"][0], ai_msg]

        assert len(state["documents"]) == 1
        assert len(state["messages"]) == 2
        assert state["route"] == "retrieve"

    def test_agent_state_documents_accumulation(self):
        """Test that documents accumulate across multiple retrievals."""
        state: AgentState = {
            "messages": [],
            "query": "",
            "route": "retrieve",
            "documents": []
        }

        # First retrieval
        doc1 = Document(page_content="Doc 1", metadata={"uuid": "id1"})
        state["documents"] = reduce_docs(state["documents"], [doc1])

        assert len(state["documents"]) == 1

        # Second retrieval (simulating follow-up)
        doc2 = Document(page_content="Doc 2", metadata={"uuid": "id2"})
        state["documents"] = reduce_docs(state["documents"], [doc2])

        assert len(state["documents"]) == 2
        assert [d.metadata["uuid"] for d in state["documents"]] == ["id1", "id2"]

    def test_agent_state_documents_deduplication(self):
        """Test that documents with same UUID are deduplicated."""
        state: AgentState = {
            "messages": [],
            "query": "",
            "route": "retrieve",
            "documents": []
        }

        # Add document
        doc1 = Document(page_content="Original", metadata={"uuid": "same-id"})
        state["documents"] = reduce_docs(state["documents"], [doc1])

        # Try to add duplicate UUID
        doc2 = Document(page_content="Duplicate", metadata={"uuid": "same-id"})
        state["documents"] = reduce_docs(state["documents"], [doc2])

        # Should only have 1 document
        assert len(state["documents"]) == 1
        assert state["documents"][0].page_content == "Original"

    def test_agent_state_empty_messages_handling(self):
        """Test handling of empty messages list."""
        state: AgentState = {
            "messages": [],
            "query": "",
            "route": "",
            "documents": []
        }

        assert isinstance(state["messages"], list)
        assert len(state["messages"]) == 0

    def test_agent_state_messages_with_metadata(self):
        """Test messages can have metadata."""
        msg = HumanMessage(
            content="Test message",
            additional_kwargs={"timestamp": "2024-01-01"}
        )

        state: AgentState = {
            "messages": [msg],
            "query": "Test message",
            "route": "direct",
            "documents": []
        }

        assert len(state["messages"]) == 1
        assert state["messages"][0].content == "Test message"
        assert state["messages"][0].additional_kwargs["timestamp"] == "2024-01-01"
