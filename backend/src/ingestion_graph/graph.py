"""Ingestion graph for processing and indexing PDF documents.

This module implements a LangGraph workflow that:
1. Takes PDF documents as input (or loads from sample file)
2. Processes them through the reduce_docs reducer
3. Stores embeddings in a vector store (Supabase)

Graph structure: START → ingestDocs → END
"""

import json
from inspect import isawaitable

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from src.ingestion_graph.configuration import ensure_index_configuration
from src.ingestion_graph.state import IndexState
from src.shared import retrieval as shared_retrieval
from src.shared.state import reduce_docs


async def make_retriever(config: RunnableConfig):
    """Wrapper to allow tests to patch make_retriever while delegating to shared module."""
    return await shared_retrieval.make_retriever(config)


async def ingest_docs(state: IndexState, config: RunnableConfig) -> dict:
    """
    Process and ingest documents into the vector store.

    This node handles document ingestion by:
    1. Loading documents from state or sample file
    2. Processing them through reduce_docs reducer
    3. Adding them to the vector store via retriever
    4. Returning a delete action to clear docs from state

    Args:
        state: The current IndexState containing documents to ingest.
        config: RunnableConfig dictionary with configuration parameters.

    Returns:
        A dict with {"docs": "delete"} to clear documents from state.

    Raises:
        ValueError: If no documents provided and use_sample_docs is False.
    """
    configuration = ensure_index_configuration(config)
    docs = state.get("docs", [])

    # If no docs provided, try to load from sample file
    if not docs or len(docs) == 0:
        if configuration.use_sample_docs:
            # Load documents from JSON file
            with open(configuration.docs_file, "r", encoding="utf-8") as f:
                serialized_docs = json.load(f)

            # Process through reduce_docs reducer
            docs = reduce_docs([], serialized_docs)
        else:
            raise ValueError("No sample documents to index.")
    else:
        # Process existing docs through reducer to ensure proper format
        docs = reduce_docs([], docs)

    # Get retriever and add documents to the underlying vector store
    retriever = await make_retriever(config)
    # Access the vector store through the retriever's vectorstore property
    result = retriever.vectorstore.add_documents(docs)

    if isawaitable(result):
        await result

    # Return delete action to clear docs from state
    return {"docs": "delete"}


# Define the graph
builder = StateGraph(IndexState)

# Add the single node
builder.add_node("ingestDocs", ingest_docs)

# Define edges: START → ingestDocs → END
builder.add_edge(START, "ingestDocs")
builder.add_edge("ingestDocs", END)

# Compile the graph without checkpointer initially
# The checkpointer will be set during FastAPI startup via compile_with_checkpointer()
graph = builder.compile()


async def compile_with_checkpointer():
    """
    Recompile the graph with PostgresSaver checkpointer.

    This function should be called during FastAPI startup to initialize
    the checkpointer and recompile the graph with persistence enabled.

    Returns:
        The compiled graph with checkpointer.

    Example:
        >>> # In FastAPI startup event
        >>> @app.on_event("startup")
        >>> async def startup():
        >>>     global graph
        >>>     graph = await compile_with_checkpointer()
    """
    from src.shared.checkpointer import get_checkpointer

    checkpointer = await get_checkpointer()
    return builder.compile(checkpointer=checkpointer)
