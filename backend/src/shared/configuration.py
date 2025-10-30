"""Configuration management for indexing and retrieval operations."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BaseConfiguration(BaseModel):
    """
    Configuration class for indexing and retrieval operations.

    This defines the parameters needed for configuring the indexing and
    retrieval processes, including retriever provider choice and search parameters.

    Attributes:
        retriever_provider: The vector store provider to use for retrieval.
            Currently supports 'supabase', but can be extended with more providers.
        filter_kwargs: Additional keyword arguments to pass to the search function
            of the retriever for filtering. Defaults to empty dict.
        k: The number of documents to retrieve. Defaults to 5.
    """

    retriever_provider: Literal["supabase"] = Field(
        default="supabase",
        alias="retrieverProvider",  # Accept camelCase from frontend/JSON
        description="The vector store provider to use for retrieval"
    )
    filter_kwargs: dict[str, Any] = Field(
        default_factory=dict,
        alias="filterKwargs",  # Accept camelCase from frontend/JSON
        description="Additional keyword arguments for filtering search results",
    )
    k: int = Field(default=5, description="The number of documents to retrieve")

    model_config = ConfigDict(
        frozen=True,  # Make the config immutable
        extra="ignore",  # Ignore extra fields
        populate_by_name=True  # Allow both camelCase aliases and snake_case field names
    )


def ensure_base_configuration(config: dict[str, Any] | None) -> BaseConfiguration:
    """
    Create a BaseConfiguration instance from a RunnableConfig object.

    Extracts configuration from the 'configurable' key if present, otherwise
    uses defaults. This matches the TypeScript implementation's behavior.

    Supports both camelCase (from frontend/JSON) and snake_case field names
    thanks to Pydantic aliases.

    Args:
        config: The configuration dictionary (RunnableConfig) to use.
                Can be None or empty dict.

    Returns:
        A BaseConfiguration instance with the specified or default configuration.

    Examples:
        >>> config = ensure_base_configuration({"configurable": {"k": 10}})
        >>> assert config.k == 10
        >>> assert config.retriever_provider == "supabase"

        >>> config = ensure_base_configuration({})
        >>> assert config.k == 5  # default

        >>> # Accepts camelCase from frontend
        >>> config = ensure_base_configuration({"configurable": {"retrieverProvider": "supabase"}})
        >>> assert config.retriever_provider == "supabase"
    """
    if config is None:
        config = {}

    # Extract configurable dict, matching TypeScript: config?.configurable || {}
    configurable = config.get("configurable", {})

    # Use Pydantic to parse - it handles both camelCase and snake_case automatically
    return BaseConfiguration.model_validate(configurable)
