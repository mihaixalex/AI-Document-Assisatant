"""State management for document processing - CRITICAL for LangGraph state graphs.

This module provides the reduce_docs function which is essential for managing
document state in LangGraph graphs. It handles concatenation, deduplication,
and type conversion for documents.
"""

from typing import Any, Literal
from uuid import uuid4

from langchain_core.documents import Document


def reduce_docs(
    existing: list[Document] | None = None,
    new_docs: list[Document] | list[dict[str, Any]] | list[str] | str | Literal["delete"] | None = None,
) -> list[Document]:
    """
    Reduces the document array based on the provided new documents or actions.

    This is a reducer function for LangGraph state management. It handles:
    - Concatenating document lists
    - UUID-based deduplication (prevents duplicate UUIDs)
    - Type conversion (strings, dicts -> Documents)
    - "delete" action to clear all documents
    - Automatic UUID generation when missing

    Args:
        existing: The existing array of documents.
        new_docs: The new documents or actions to apply. Can be:
            - List[Document]: Documents to append (with deduplication)
            - List[Dict]: Dicts to convert to Documents
            - List[str]: Strings to convert to Documents
            - str: Single string to convert to Document
            - "delete": Clears all documents
            - None: Returns existing docs unchanged

    Returns:
        The updated array of documents after applying the operation.

    Examples:
        >>> # Append documents with deduplication
        >>> existing = [Document(page_content="doc1", metadata={"uuid": "id1"})]
        >>> new = [Document(page_content="doc2", metadata={"uuid": "id2"})]
        >>> result = reduce_docs(existing, new)
        >>> len(result)
        2

        >>> # Delete all documents
        >>> result = reduce_docs(existing, "delete")
        >>> len(result)
        0

        >>> # Convert string to Document
        >>> result = reduce_docs(None, "Hello world")
        >>> result[0].page_content
        'Hello world'
    """
    # Handle "delete" action
    if new_docs == "delete":
        return []

    # Initialize existing list
    existing_list = existing or []

    # Build set of existing UUIDs for O(1) lookup during deduplication
    existing_ids = set(
        doc.metadata.get("uuid")
        for doc in existing_list
        if doc.metadata and doc.metadata.get("uuid")
    )

    # Handle None or no new docs
    if new_docs is None:
        return existing_list

    # Handle single string
    if isinstance(new_docs, str):
        doc_id = str(uuid4())
        return [*existing_list, Document(page_content=new_docs, metadata={"uuid": doc_id})]

    # Handle list of items (Documents, dicts, strings)
    new_list: list[Document] = []

    if isinstance(new_docs, list):
        for item in new_docs:
            if isinstance(item, str):
                # Convert string to Document with generated UUID
                item_id = str(uuid4())
                new_list.append(Document(page_content=item, metadata={"uuid": item_id}))
                existing_ids.add(item_id)

            elif isinstance(item, dict):
                # Handle dict (either Document-like or generic object)
                metadata = item.get("metadata", {})
                item_id = metadata.get("uuid", str(uuid4()))

                # Skip if UUID already exists (deduplication)
                if item_id not in existing_ids:
                    if "pageContent" in item:
                        # It's a Document-like dict
                        new_list.append(
                            Document(
                                page_content=item["pageContent"],
                                metadata={**metadata, "uuid": item_id},
                            )
                        )
                    else:
                        # It's a generic object - treat all fields as metadata
                        new_list.append(
                            Document(page_content="", metadata={**item, "uuid": item_id})
                        )
                    existing_ids.add(item_id)

            elif isinstance(item, Document):
                # Handle Document objects
                metadata = item.metadata or {}
                item_id = metadata.get("uuid")

                # Generate UUID if missing
                if not item_id:
                    item_id = str(uuid4())
                    metadata = {**metadata, "uuid": item_id}

                # Skip if UUID already exists (deduplication)
                if item_id not in existing_ids:
                    new_list.append(Document(page_content=item.page_content, metadata=metadata))
                    existing_ids.add(item_id)

    return [*existing_list, *new_list]
