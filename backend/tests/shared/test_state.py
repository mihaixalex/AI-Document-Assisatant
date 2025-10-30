"""Tests for state module - TDD approach (write tests first).

This is the CRITICAL module for Ticket 2 (PLU-17) - the reduce_docs function
must handle all edge cases correctly for document deduplication.
"""

from uuid import uuid4

from langchain_core.documents import Document

from src.shared.state import reduce_docs


class TestReduceDocs:
    """Test the reduce_docs function - critical for state management."""

    def test_reduce_docs_empty_existing_empty_new(self) -> None:
        """Test with both existing and new docs empty."""
        result = reduce_docs(None, None)
        assert result == []

    def test_reduce_docs_empty_existing_with_new_docs(self) -> None:
        """Test adding new documents to empty list."""
        doc1 = Document(page_content="content1", metadata={"uuid": "id1"})
        doc2 = Document(page_content="content2", metadata={"uuid": "id2"})

        result = reduce_docs(None, [doc1, doc2])

        assert len(result) == 2
        assert result[0].page_content == "content1"
        assert result[0].metadata["uuid"] == "id1"
        assert result[1].page_content == "content2"
        assert result[1].metadata["uuid"] == "id2"

    def test_reduce_docs_delete_action(self) -> None:
        """Test 'delete' action clears all documents."""
        existing = [
            Document(page_content="doc1", metadata={"uuid": "id1"}),
            Document(page_content="doc2", metadata={"uuid": "id2"}),
        ]

        result = reduce_docs(existing, "delete")

        assert result == []

    def test_reduce_docs_delete_with_empty_existing(self) -> None:
        """Test 'delete' action with no existing documents."""
        result = reduce_docs(None, "delete")
        assert result == []

    def test_reduce_docs_append_documents(self) -> None:
        """Test appending new documents to existing list."""
        existing = [Document(page_content="doc1", metadata={"uuid": "id1"})]
        new_docs = [Document(page_content="doc2", metadata={"uuid": "id2"})]

        result = reduce_docs(existing, new_docs)

        assert len(result) == 2
        assert result[0].metadata["uuid"] == "id1"
        assert result[1].metadata["uuid"] == "id2"

    def test_reduce_docs_uuid_deduplication(self) -> None:
        """Test UUID-based deduplication - duplicate UUIDs are not added."""
        existing = [Document(page_content="original", metadata={"uuid": "duplicate-id"})]
        new_docs = [
            Document(page_content="new content", metadata={"uuid": "duplicate-id"}),
            Document(page_content="unique", metadata={"uuid": "unique-id"}),
        ]

        result = reduce_docs(existing, new_docs)

        # Should have original + only the unique doc (duplicate rejected)
        assert len(result) == 2
        assert result[0].page_content == "original"  # Original preserved
        assert result[0].metadata["uuid"] == "duplicate-id"
        assert result[1].page_content == "unique"
        assert result[1].metadata["uuid"] == "unique-id"

    def test_reduce_docs_string_to_document_conversion(self) -> None:
        """Test converting single string to Document with generated UUID."""
        result = reduce_docs(None, "This is a string content")

        assert len(result) == 1
        assert result[0].page_content == "This is a string content"
        assert "uuid" in result[0].metadata
        # UUID should be valid
        assert len(result[0].metadata["uuid"]) == 36  # Standard UUID length

    def test_reduce_docs_string_to_document_appends(self) -> None:
        """Test that string conversion appends to existing documents."""
        existing = [Document(page_content="existing", metadata={"uuid": "id1"})]

        result = reduce_docs(existing, "new string content")

        assert len(result) == 2
        assert result[0].page_content == "existing"
        assert result[1].page_content == "new string content"

    def test_reduce_docs_list_of_strings(self) -> None:
        """Test converting list of strings to Documents with generated UUIDs."""
        result = reduce_docs(None, ["string1", "string2", "string3"])

        assert len(result) == 3
        for i, doc in enumerate(result):
            assert doc.page_content == f"string{i+1}"
            assert "uuid" in doc.metadata
            assert len(doc.metadata["uuid"]) == 36

        # All UUIDs should be unique
        uuids = [doc.metadata["uuid"] for doc in result]
        assert len(uuids) == len(set(uuids))

    def test_reduce_docs_list_of_dicts_without_page_content(self) -> None:
        """Test converting list of dicts (without pageContent) to Documents."""
        dicts = [{"key1": "value1", "key2": "value2"}, {"name": "test", "type": "document"}]

        result = reduce_docs(None, dicts)

        assert len(result) == 2
        # When no pageContent, should create empty content with metadata
        assert result[0].page_content == ""
        assert result[0].metadata["key1"] == "value1"
        assert result[0].metadata["key2"] == "value2"
        assert "uuid" in result[0].metadata

        assert result[1].page_content == ""
        assert result[1].metadata["name"] == "test"
        assert result[1].metadata["type"] == "document"
        assert "uuid" in result[1].metadata

    def test_reduce_docs_list_of_dicts_with_page_content(self) -> None:
        """Test converting list of Document-like dicts to Documents."""
        dicts = [
            {"pageContent": "content1", "metadata": {"source": "doc1"}},
            {"pageContent": "content2", "metadata": {"source": "doc2"}},
        ]

        result = reduce_docs(None, dicts)

        assert len(result) == 2
        assert result[0].page_content == "content1"
        assert result[0].metadata["source"] == "doc1"
        assert "uuid" in result[0].metadata

        assert result[1].page_content == "content2"
        assert result[1].metadata["source"] == "doc2"
        assert "uuid" in result[1].metadata

    def test_reduce_docs_mixed_list(self) -> None:
        """Test list with mixed types (strings and dicts)."""
        mixed = [
            "string content",
            {"pageContent": "dict content", "metadata": {"type": "dict"}},
            "another string",
        ]

        result = reduce_docs(None, mixed)

        assert len(result) == 3
        assert result[0].page_content == "string content"
        assert result[1].page_content == "dict content"
        assert result[1].metadata["type"] == "dict"
        assert result[2].page_content == "another string"

    def test_reduce_docs_preserves_existing_uuid_in_metadata(self) -> None:
        """Test that existing UUIDs in metadata are preserved."""
        doc_id = str(uuid4())
        dicts = [{"pageContent": "content", "metadata": {"uuid": doc_id, "other": "data"}}]

        result = reduce_docs(None, dicts)

        assert len(result) == 1
        assert result[0].metadata["uuid"] == doc_id
        assert result[0].metadata["other"] == "data"

    def test_reduce_docs_generates_uuid_when_missing(self) -> None:
        """Test that UUID is generated when not present in metadata."""
        dicts = [{"pageContent": "content", "metadata": {"other": "data"}}]

        result = reduce_docs(None, dicts)

        assert len(result) == 1
        assert "uuid" in result[0].metadata
        assert result[0].metadata["other"] == "data"

    def test_reduce_docs_deduplication_with_existing_ids(self) -> None:
        """Test that deduplication uses existing IDs correctly."""
        id1 = str(uuid4())
        id2 = str(uuid4())

        existing = [
            Document(page_content="doc1", metadata={"uuid": id1}),
            Document(page_content="doc2", metadata={"uuid": id2}),
        ]

        new_docs = [
            Document(page_content="new1", metadata={"uuid": id1}),  # Duplicate
            Document(page_content="new2", metadata={"uuid": str(uuid4())}),  # Unique
            Document(page_content="new3", metadata={"uuid": id2}),  # Duplicate
        ]

        result = reduce_docs(existing, new_docs)

        # Should have 2 existing + 1 unique new = 3 total
        assert len(result) == 3
        uuids = [doc.metadata["uuid"] for doc in result]
        assert id1 in uuids
        assert id2 in uuids
        # First occurrence should be preserved (original content)
        assert result[0].page_content == "doc1"
        assert result[1].page_content == "doc2"
        assert result[2].page_content == "new2"

    def test_reduce_docs_empty_list_of_docs(self) -> None:
        """Test with empty list of documents."""
        existing = [Document(page_content="existing", metadata={"uuid": "id1"})]

        result = reduce_docs(existing, [])

        # Should return existing docs unchanged
        assert len(result) == 1
        assert result[0].page_content == "existing"

    def test_reduce_docs_none_new_docs(self) -> None:
        """Test with None as new_docs parameter."""
        existing = [Document(page_content="existing", metadata={"uuid": "id1"})]

        result = reduce_docs(existing, None)

        # Should return existing docs unchanged
        assert len(result) == 1
        assert result[0].page_content == "existing"

    def test_reduce_docs_large_batch_deduplication(self) -> None:
        """Test deduplication with large batch of documents."""
        # Create 100 existing documents
        existing = [
            Document(page_content=f"doc{i}", metadata={"uuid": f"id{i}"}) for i in range(100)
        ]

        # Create 100 new documents, half duplicates, half unique
        new_docs = [
            Document(page_content=f"new{i}", metadata={"uuid": f"id{i if i < 50 else 100+i}"})
            for i in range(100)
        ]

        result = reduce_docs(existing, new_docs)

        # Should have 100 existing + 50 unique new = 150 total
        assert len(result) == 150

        # Verify all UUIDs are unique
        uuids = [doc.metadata["uuid"] for doc in result]
        assert len(uuids) == len(set(uuids))

    def test_reduce_docs_metadata_without_uuid(self) -> None:
        """Test documents without UUID in metadata."""
        doc = Document(page_content="content", metadata={"other": "data"})

        result = reduce_docs(None, [doc])

        assert len(result) == 1
        # Should generate UUID if missing
        assert "uuid" in result[0].metadata

    def test_reduce_docs_preserves_document_order(self) -> None:
        """Test that document order is preserved."""
        new_docs = [
            Document(page_content=f"doc{i}", metadata={"uuid": f"id{i}"}) for i in range(10)
        ]

        result = reduce_docs(None, new_docs)

        assert len(result) == 10
        for i, doc in enumerate(result):
            assert doc.page_content == f"doc{i}"
            assert doc.metadata["uuid"] == f"id{i}"

    def test_reduce_docs_complex_metadata(self) -> None:
        """Test with complex nested metadata structures."""
        dicts = [
            {
                "pageContent": "complex",
                "metadata": {
                    "nested": {"level1": {"level2": "value"}},
                    "list": [1, 2, 3],
                    "uuid": "test-id",
                },
            }
        ]

        result = reduce_docs(None, dicts)

        assert len(result) == 1
        assert result[0].metadata["uuid"] == "test-id"
        assert result[0].metadata["nested"]["level1"]["level2"] == "value"
        assert result[0].metadata["list"] == [1, 2, 3]
