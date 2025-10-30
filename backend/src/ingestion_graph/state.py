"""State definitions for the ingestion graph.

This module defines the IndexState TypedDict which represents the state
structure for document indexing operations in the ingestion graph.
"""

from typing import Annotated, TypedDict

from langchain_core.documents import Document

from src.shared.state import reduce_docs


class IndexState(TypedDict):
    """
    Represents the state for document indexing and retrieval.

    This TypedDict defines the structure of the index state, which includes
    the documents to be indexed. The docs field uses the reduce_docs reducer
    to handle concatenation, deduplication, and type conversion.

    Attributes:
        docs: A list of documents that the agent can index.
              Uses reduce_docs reducer for state management:
              - Concatenates new documents with existing ones (doesn't replace)
              - Deduplicates by UUID to prevent duplicates
              - Converts strings/dicts to Document objects
              - Supports 'delete' action to clear all docs
    """

    docs: Annotated[list[Document], reduce_docs]
