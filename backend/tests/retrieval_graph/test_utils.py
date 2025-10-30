"""Tests for retrieval graph utility helpers."""

from langchain_core.documents import Document

from src.retrieval_graph.utils import format_doc, format_docs


def test_format_doc_quotes_metadata_values() -> None:
    """format_doc should quote metadata values and avoid double spacing."""
    doc = Document(
        page_content="Hello world",
        metadata={"source": "file name.pdf", "page": 1},
    )

    formatted = format_doc(doc)

    assert formatted.startswith('<document source="file name.pdf" page="1">')
    assert "  source=" not in formatted  # no double leading spaces
    assert "\nHello world\n</document>" in formatted


def test_format_docs_wraps_documents_tag() -> None:
    """format_docs should wrap multiple docs in a <documents> container."""
    docs = [
        Document(page_content="Doc 1", metadata={"source": "a.pdf"}),
        Document(page_content="Doc 2", metadata={"source": "b.pdf"}),
    ]

    formatted = format_docs(docs)

    assert formatted.startswith("<documents>")
    assert formatted.endswith("</documents>")
    assert 'source="a.pdf"' in formatted
    assert 'source="b.pdf"' in formatted


def test_format_docs_handles_empty_and_none() -> None:
    """format_docs should gracefully handle empty inputs."""
    assert format_docs([]) == "<documents></documents>"
    assert format_docs(None) == "<documents></documents>"
