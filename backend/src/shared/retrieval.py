"""Retrieval utilities for creating vector store retrievers.

This module provides factory functions for creating retrievers from different
vector store providers (currently Supabase, but extensible to others).
"""

import os

from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.runnables import RunnableConfig
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_openai import OpenAIEmbeddings
from postgrest._sync.request_builder import SyncRPCFilterRequestBuilder
from supabase import create_client

from src.shared.configuration import BaseConfiguration, ensure_base_configuration


def _ensure_params_property_on_sync_rpc_builder() -> None:
    """Provide backwards-compatible access to `.params` on Supabase RPC builders."""

    if hasattr(SyncRPCFilterRequestBuilder, "params"):
        return

    def _get_params(self):
        return self.request.params

    def _set_params(self, value):
        self.request.params = value

    SyncRPCFilterRequestBuilder.params = property(_get_params, _set_params)  # type: ignore[attr-defined]


_ensure_params_property_on_sync_rpc_builder()


async def make_supabase_retriever(
    configuration: BaseConfiguration,
) -> VectorStoreRetriever:
    """
    Create a Supabase vector store retriever.

    Args:
        configuration: The base configuration containing retrieval parameters.

    Returns:
        A VectorStoreRetriever configured for Supabase.

    Raises:
        ValueError: If required environment variables are not set.

    Example:
        >>> config = BaseConfiguration(k=10, filter_kwargs={"user_id": "123"})
        >>> retriever = await make_supabase_retriever(config)
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables are not defined"
        )

    # Initialize OpenAI embeddings
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    # Create Supabase client
    supabase_client = create_client(supabase_url, supabase_key)

    # Create vector store
    vector_store = SupabaseVectorStore(
        client=supabase_client,
        embedding=embeddings,
        table_name="documents",
        query_name="match_documents"
    )

    # Build search kwargs
    search_kwargs: dict[str, object] = {}
    if configuration.filter_kwargs:
        search_kwargs["filter"] = configuration.filter_kwargs

    return vector_store.as_retriever(
        k=configuration.k,
        search_kwargs=search_kwargs,
    )


async def make_retriever(config: RunnableConfig) -> VectorStoreRetriever:
    """
    Factory function to create a retriever based on configuration.

    This function extracts configuration from a RunnableConfig
    and dispatches to the appropriate retriever creation function based
    on the retriever_provider setting.

    Args:
        config: The RunnableConfig containing retrieval settings.

    Returns:
        A VectorStoreRetriever instance.

    Raises:
        ValueError: If an unsupported retriever provider is specified.

    Example:
        >>> config = {
        ...     "configurable": {
        ...         "retriever_provider": "supabase",
        ...         "k": 10,
        ...         "filter_kwargs": {"source": "pdf"},
        ...         "thread_id": "abc-123"
        ...     }
        ... }
        >>> retriever = await make_retriever(config)
    """
    # Extract and ensure configuration
    configuration = ensure_base_configuration(config)

    # Extract thread_id from config for document isolation
    configurable = config.get("configurable", {}) if config else {}
    thread_id = configurable.get("thread_id")

    # Add thread_id filter to configuration if present and valid
    # Must explicitly check for None and empty string to prevent bypassing isolation
    if thread_id is not None and thread_id != "":
        # Create a new configuration with thread_id filter merged
        updated_filter_kwargs = {**configuration.filter_kwargs, "thread_id": thread_id}
        configuration = BaseConfiguration(
            retriever_provider=configuration.retriever_provider,
            filter_kwargs=updated_filter_kwargs,
            k=configuration.k
        )

    # Dispatch to appropriate retriever based on provider
    if configuration.retriever_provider == "supabase":
        return await make_supabase_retriever(configuration)
    else:
        # This should never happen due to Literal type constraint,
        # but we include it for robustness and future extensibility
        raise ValueError(f"Unsupported retriever provider: {configuration.retriever_provider}")
