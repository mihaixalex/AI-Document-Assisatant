"""Configuration management for the retrieval graph."""

from typing import Any

from pydantic import Field

from src.shared.configuration import BaseConfiguration, ensure_base_configuration

# Default query model
DEFAULT_QUERY_MODEL = "openai/gpt-4o"


class AgentConfiguration(BaseConfiguration):
    """
    Configuration class for the retrieval/agent graph.

    Extends BaseConfiguration with agent-specific settings like
    the language model to use for query processing and response generation.

    Attributes:
        query_model: The language model used for processing and refining queries.
                    Should be in the form: provider/model-name.
    """

    query_model: str = Field(
        default=DEFAULT_QUERY_MODEL,
        alias="queryModel",  # Accept camelCase from frontend/JSON
        description="The language model used for query processing (format: provider/model-name)",
    )


def ensure_agent_configuration(config: dict[str, Any] | None) -> AgentConfiguration:
    """
    Create an AgentConfiguration instance from a RunnableConfig object.

    Extracts configuration from the 'configurable' key if present, otherwise
    uses defaults. This matches the TypeScript implementation's behavior.

    Supports both camelCase (from frontend/JSON) and snake_case field names
    thanks to Pydantic aliases.

    Args:
        config: The configuration dictionary (RunnableConfig) to use.
                Can be None or empty dict.

    Returns:
        An AgentConfiguration instance with the specified or default configuration.

    Examples:
        >>> config = ensure_agent_configuration({"configurable": {"query_model": "openai/gpt-4"}})
        >>> assert config.query_model == "openai/gpt-4"

        >>> config = ensure_agent_configuration({})
        >>> assert config.query_model == "openai/gpt-4o"  # default

        >>> # Accepts camelCase from frontend
        >>> config = ensure_agent_configuration({"configurable": {"queryModel": "openai/gpt-3.5-turbo"}})
        >>> assert config.query_model == "openai/gpt-3.5-turbo"
    """
    if config is None:
        config = {}

    # Extract configurable dict
    configurable = config.get("configurable", {})

    # Use Pydantic to parse - it handles both camelCase and snake_case automatically
    return AgentConfiguration.model_validate(configurable)
