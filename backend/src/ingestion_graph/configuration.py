"""Configuration management for the ingestion graph."""

from typing import Any

from pydantic import Field

from src.shared.configuration import BaseConfiguration, ensure_base_configuration

# Default path to sample documents file
DEFAULT_DOCS_FILE = "./src/sample_docs.json"


class IndexConfiguration(BaseConfiguration):
    """
    Configuration class for the ingestion/indexing graph.

    Extends BaseConfiguration with ingestion-specific settings like
    the path to sample documents and whether to use them.

    Attributes:
        docs_file: Path to a JSON file containing default documents to index.
        use_sample_docs: Whether to use sample documents when no docs provided.
    """

    docs_file: str = Field(
        default=DEFAULT_DOCS_FILE,
        alias="docsFile",  # Accept camelCase from frontend/JSON
        description="Path to a JSON file containing default documents to index",
    )
    use_sample_docs: bool = Field(
        default=False,
        alias="useSampleDocs",  # Accept camelCase from frontend/JSON
        description="Whether to use sample documents when no docs are provided",
    )


def ensure_index_configuration(config: dict[str, Any] | None) -> IndexConfiguration:
    """
    Create an IndexConfiguration instance from a RunnableConfig object.

    Extracts configuration from the 'configurable' key if present, otherwise
    uses defaults. This matches the TypeScript implementation's behavior.

    Supports both camelCase (from frontend/JSON) and snake_case field names
    thanks to Pydantic aliases.

    Args:
        config: The configuration dictionary (RunnableConfig) to use.
                Can be None or empty dict.

    Returns:
        An IndexConfiguration instance with the specified or default configuration.

    Examples:
        >>> config = ensure_index_configuration({"configurable": {"use_sample_docs": True}})
        >>> assert config.use_sample_docs is True

        >>> config = ensure_index_configuration({})
        >>> assert config.use_sample_docs is False  # default

        >>> # Accepts camelCase from frontend
        >>> config = ensure_index_configuration({"configurable": {"useSampleDocs": True}})
        >>> assert config.use_sample_docs is True
    """
    if config is None:
        config = {}

    # Extract configurable dict
    configurable = config.get("configurable", {})

    # Use Pydantic to parse - it handles both camelCase and snake_case automatically
    return IndexConfiguration.model_validate(configurable)
