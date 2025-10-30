"""Tests for ingestion graph state definitions.

This test suite validates the IndexState TypedDict structure and its integration
with the reduce_docs reducer function.
"""

import pytest
from typing import get_type_hints
from langchain_core.documents import Document

from src.ingestion_graph.state import IndexState
from src.shared.state import reduce_docs


class TestIndexState:
    """Test suite for IndexState TypedDict."""

    def test_index_state_structure(self):
        """Test that IndexState has the correct field structure."""
        # Get type hints from IndexState
        hints = get_type_hints(IndexState)

        # IndexState should have exactly one field: docs
        assert "docs" in hints, "IndexState must have 'docs' field"
        assert len(hints) == 1, "IndexState should have exactly 1 field"

    def test_index_state_docs_type(self):
        """Test that docs field accepts list of Documents."""
        # Get type hints
        hints = get_type_hints(IndexState)

        # Check that docs is typed as list[Document]
        docs_type = str(hints["docs"])
        assert "list" in docs_type.lower() or "List" in docs_type, "docs should be a list type"
        assert "Document" in docs_type, "docs should contain Document type"

    def test_index_state_instantiation_empty(self):
        """Test creating an IndexState with empty docs."""
        state: IndexState = {"docs": []}

        assert isinstance(state, dict), "IndexState should be a dict"
        assert "docs" in state, "IndexState must have 'docs' key"
        assert state["docs"] == [], "docs should be empty list"

    def test_index_state_instantiation_with_documents(self):
        """Test creating an IndexState with actual documents."""
        doc1 = Document(page_content="Test content 1", metadata={"uuid": "id1"})
        doc2 = Document(page_content="Test content 2", metadata={"uuid": "id2"})

        state: IndexState = {"docs": [doc1, doc2]}

        assert len(state["docs"]) == 2, "Should have 2 documents"
        assert state["docs"][0].page_content == "Test content 1"
        assert state["docs"][1].page_content == "Test content 2"

    def test_index_state_with_reducer_concatenation(self):
        """Test that IndexState works with reduce_docs reducer for concatenation."""
        # Initial state
        doc1 = Document(page_content="Existing doc", metadata={"uuid": "id1"})
        existing_docs = [doc1]

        # New docs to add
        doc2 = Document(page_content="New doc", metadata={"uuid": "id2"})
        new_docs = [doc2]

        # Use reducer to merge
        result = reduce_docs(existing_docs, new_docs)

        # Verify concatenation (not replacement)
        assert len(result) == 2, "Should concatenate, not replace"
        assert result[0].page_content == "Existing doc"
        assert result[1].page_content == "New doc"

    def test_index_state_with_reducer_deduplication(self):
        """Test that reducer prevents duplicate UUIDs."""
        # Existing doc with UUID
        doc1 = Document(page_content="First", metadata={"uuid": "same-id"})
        existing_docs = [doc1]

        # Try to add doc with same UUID
        doc2 = Document(page_content="Duplicate", metadata={"uuid": "same-id"})
        new_docs = [doc2]

        result = reduce_docs(existing_docs, new_docs)

        # Should NOT add duplicate UUID
        assert len(result) == 1, "Should deduplicate by UUID"
        assert result[0].page_content == "First", "Should keep original doc"

    def test_index_state_with_reducer_string_conversion(self):
        """Test that reducer converts strings to Documents."""
        existing_docs = []
        new_docs = "Simple text content"

        result = reduce_docs(existing_docs, new_docs)

        assert len(result) == 1, "Should create one document from string"
        assert isinstance(result[0], Document), "Should convert to Document"
        assert result[0].page_content == "Simple text content"
        assert "uuid" in result[0].metadata, "Should generate UUID"

    def test_index_state_with_reducer_delete_action(self):
        """Test that reducer handles 'delete' action."""
        doc1 = Document(page_content="To be deleted", metadata={"uuid": "id1"})
        existing_docs = [doc1]

        result = reduce_docs(existing_docs, "delete")

        assert len(result) == 0, "Delete action should clear all docs"

    def test_index_state_field_name_matches_typescript(self):
        """Test that field names match TypeScript exactly for frontend compatibility."""
        # TypeScript uses 'docs', not 'documents'
        hints = get_type_hints(IndexState)
        assert "docs" in hints, "Must use 'docs' field name to match TypeScript"
        assert "documents" not in hints, "Should not use 'documents' field name"

    def test_index_state_immutability_pattern(self):
        """Test that state updates follow immutability patterns."""
        # Initial state
        state: IndexState = {"docs": []}

        # Add documents using reducer (simulating graph update)
        doc = Document(page_content="Test", metadata={"uuid": "id1"})
        new_docs = reduce_docs(state["docs"], [doc])

        # Original state should be unchanged
        assert len(state["docs"]) == 0, "Original state should not be mutated"
        assert len(new_docs) == 1, "New state should have the document"


class TestIndexStateIntegration:
    """Integration tests for IndexState with LangGraph patterns."""

    def test_index_state_multiple_updates(self):
        """Test multiple sequential updates to docs field."""
        state: IndexState = {"docs": []}

        # First update
        doc1 = Document(page_content="Doc 1", metadata={"uuid": "id1"})
        state_docs = reduce_docs(state["docs"], [doc1])

        # Second update (simulating next graph node)
        doc2 = Document(page_content="Doc 2", metadata={"uuid": "id2"})
        state_docs = reduce_docs(state_docs, [doc2])

        # Third update
        doc3 = Document(page_content="Doc 3", metadata={"uuid": "id3"})
        state_docs = reduce_docs(state_docs, [doc3])

        assert len(state_docs) == 3, "Should accumulate all documents"
        assert [d.metadata["uuid"] for d in state_docs] == ["id1", "id2", "id3"]

    def test_index_state_with_dict_conversion(self):
        """Test that reducer converts dict objects to Documents."""
        existing_docs = []
        new_docs = [
            {"pageContent": "Content from dict", "metadata": {"uuid": "id1", "source": "test"}}
        ]

        result = reduce_docs(existing_docs, new_docs)

        assert len(result) == 1, "Should convert dict to Document"
        assert result[0].page_content == "Content from dict"
        assert result[0].metadata["source"] == "test"

    def test_index_state_preserves_metadata(self):
        """Test that document metadata is preserved during state updates."""
        doc = Document(
            page_content="Test content",
            metadata={"uuid": "id1", "source": "test.pdf", "page": 1}
        )

        result = reduce_docs([], [doc])

        assert result[0].metadata["source"] == "test.pdf"
        assert result[0].metadata["page"] == 1
        assert result[0].metadata["uuid"] == "id1"
