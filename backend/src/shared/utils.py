"""Utility functions for loading chat models and other shared operations."""

import asyncio
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

# Supported model providers - matches TypeScript implementation
SUPPORTED_PROVIDERS = (
    "openai",
    "anthropic",
    "azure_openai",
    "cohere",
    "google-vertexai",
    "google-vertexai-web",
    "google-genai",
    "ollama",
    "together",
    "fireworks",
    "mistralai",
    "groq",
    "bedrock",
    "cerebras",
    "deepseek",
    "xai",
)

SupportedProvider = Literal[
    "openai",
    "anthropic",
    "azure_openai",
    "cohere",
    "google-vertexai",
    "google-vertexai-web",
    "google-genai",
    "ollama",
    "together",
    "fireworks",
    "mistralai",
    "groq",
    "bedrock",
    "cerebras",
    "deepseek",
    "xai",
]


async def load_chat_model(
    fully_specified_name: str,
    temperature: float = 0.2,
) -> BaseChatModel:
    """
    Load a chat model from a fully specified name.

    Args:
        fully_specified_name: String in the format 'provider/model' or 'provider/account/model'.
                              Can also be just the provider name if it's a supported provider.
        temperature: Temperature setting for the model (default: 0.2).

    Returns:
        A BaseChatModel instance.

    Raises:
        ValueError: If the provider or model is not supported.

    Examples:
        >>> model = await load_chat_model("openai/gpt-4o-mini")
        >>> model = await load_chat_model("anthropic/claude-3-sonnet", temperature=0.7)
        >>> model = await load_chat_model("openai")  # Just provider name
    """
    index = fully_specified_name.find("/")

    if index == -1:
        # No "/" found - treat as model name only
        if fully_specified_name not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported model: {fully_specified_name}")

        model_instance = init_chat_model(fully_specified_name, temperature=temperature)
        if asyncio.iscoroutine(model_instance):
            return await model_instance
        return model_instance
    else:
        # Extract provider and model from the string
        provider = fully_specified_name[:index]
        model = fully_specified_name[index + 1 :]

        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")

        model_instance = init_chat_model(
            model,
            model_provider=provider,
            temperature=temperature,
        )

        if asyncio.iscoroutine(model_instance):
            return await model_instance

        return model_instance
