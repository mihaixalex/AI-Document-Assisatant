"""Utility functions for the retrieval graph.

This module provides helper functions for formatting documents for LLM context.
"""

from langchain_core.documents import Document


def format_doc(doc: Document) -> str:
    """
    Format a single document as XML with metadata attributes.

    Args:
        doc: The document to format.

    Returns:
        A string representation of the document in XML format.

    Example:
        >>> doc = Document(page_content="Hello", metadata={"source": "test.pdf", "page": 1})
        >>> result = format_doc(doc)
        >>> assert "<document" in result
        >>> assert "source=test.pdf" in result
        >>> assert "Hello" in result
    """
    metadata = doc.metadata or {}

    # Format metadata as XML attributes with quoting for safety
    meta_attrs = "".join(f' {k}="{v}"' for k, v in metadata.items())

    return f"<document{meta_attrs}>\n{doc.page_content}\n</document>"


def format_docs(docs: list[Document] | None = None) -> str:
    """
    Format a list of documents as XML.

    Args:
        docs: List of documents to format. Can be None or empty.

    Returns:
        A string representation of all documents wrapped in <documents> tags.

    Examples:
        >>> docs = [Document(page_content="Doc 1"), Document(page_content="Doc 2")]
        >>> result = format_docs(docs)
        >>> assert "<documents>" in result
        >>> assert "Doc 1" in result

        >>> # Handle empty list
        >>> result = format_docs([])
        >>> assert result == "<documents></documents>"

        >>> # Handle None
        >>> result = format_docs(None)
        >>> assert result == "<documents></documents>"
    """
    if not docs or len(docs) == 0:
        return "<documents></documents>"

    formatted = "\n".join(format_doc(doc) for doc in docs)
    return f"<documents>\n{formatted}\n</documents>"
