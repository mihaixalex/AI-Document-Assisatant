"""Tests for utils module - TDD approach (write tests first)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.shared.utils import SUPPORTED_PROVIDERS, load_chat_model


class TestSupportedProviders:
    """Test the SUPPORTED_PROVIDERS constant."""

    def test_supported_providers_is_tuple(self) -> None:
        """Verify SUPPORTED_PROVIDERS is a tuple."""
        assert isinstance(SUPPORTED_PROVIDERS, tuple)

    def test_supported_providers_contains_expected_providers(self) -> None:
        """Verify SUPPORTED_PROVIDERS contains all expected providers."""
        expected = (
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
        assert SUPPORTED_PROVIDERS == expected

    def test_supported_providers_is_immutable(self) -> None:
        """Verify SUPPORTED_PROVIDERS cannot be modified."""
        with pytest.raises((TypeError, AttributeError)):
            SUPPORTED_PROVIDERS.append("new_provider")  # type: ignore


class TestLoadChatModel:
    """Test the load_chat_model function."""

    @pytest.mark.asyncio
    async def test_load_chat_model_with_provider_and_model(self) -> None:
        """Test loading a chat model with provider/model format."""
        mock_model = MagicMock()

        with patch("src.shared.utils.init_chat_model", new_callable=AsyncMock) as mock_init:
            mock_init.return_value = mock_model

            result = await load_chat_model("openai/gpt-4o-mini")

            # Verify init_chat_model was called with correct params
            mock_init.assert_called_once_with(
                "gpt-4o-mini", model_provider="openai", temperature=0.2
            )
            assert result == mock_model

    @pytest.mark.asyncio
    async def test_load_chat_model_with_custom_temperature(self) -> None:
        """Test loading a chat model with custom temperature."""
        mock_model = MagicMock()

        with patch("src.shared.utils.init_chat_model", new_callable=AsyncMock) as mock_init:
            mock_init.return_value = mock_model

            result = await load_chat_model("anthropic/claude-3-sonnet", temperature=0.7)

            mock_init.assert_called_once_with(
                "claude-3-sonnet", model_provider="anthropic", temperature=0.7
            )
            assert result == mock_model

    @pytest.mark.asyncio
    async def test_load_chat_model_with_model_only_supported_provider(self) -> None:
        """Test loading with just model name when it's a supported provider."""
        mock_model = MagicMock()

        with patch("src.shared.utils.init_chat_model", new_callable=AsyncMock) as mock_init:
            mock_init.return_value = mock_model

            result = await load_chat_model("openai")

            # When no "/" found and it's a supported provider, use as model
            mock_init.assert_called_once_with("openai", temperature=0.2)
            assert result == mock_model

    @pytest.mark.asyncio
    async def test_load_chat_model_with_model_only_unsupported(self) -> None:
        """Test error when model-only format uses unsupported provider."""
        with pytest.raises(ValueError, match="Unsupported model: unsupported_model"):
            await load_chat_model("unsupported_model")

    @pytest.mark.asyncio
    async def test_load_chat_model_with_unsupported_provider(self) -> None:
        """Test error when provider is not supported."""
        with pytest.raises(ValueError, match="Unsupported provider: invalid_provider"):
            await load_chat_model("invalid_provider/some-model")

    @pytest.mark.asyncio
    async def test_load_chat_model_with_all_supported_providers(self) -> None:
        """Test that all supported providers work correctly."""
        mock_model = MagicMock()

        for provider in SUPPORTED_PROVIDERS:
            with patch("src.shared.utils.init_chat_model", new_callable=AsyncMock) as mock_init:
                mock_init.return_value = mock_model

                result = await load_chat_model(f"{provider}/test-model")

                mock_init.assert_called_once_with(
                    "test-model", model_provider=provider, temperature=0.2
                )
                assert result == mock_model

    @pytest.mark.asyncio
    async def test_load_chat_model_with_complex_model_path(self) -> None:
        """Test loading with complex model path (account/provider/model)."""
        mock_model = MagicMock()

        with patch("src.shared.utils.init_chat_model", new_callable=AsyncMock) as mock_init:
            mock_init.return_value = mock_model

            # Should extract provider from first segment before "/"
            result = await load_chat_model("azure_openai/account/deployment/model")

            mock_init.assert_called_once_with(
                "account/deployment/model", model_provider="azure_openai", temperature=0.2
            )
            assert result == mock_model

    @pytest.mark.asyncio
    async def test_load_chat_model_default_temperature(self) -> None:
        """Test that default temperature is 0.2."""
        mock_model = MagicMock()

        with patch("src.shared.utils.init_chat_model", new_callable=AsyncMock) as mock_init:
            mock_init.return_value = mock_model

            await load_chat_model("openai/gpt-4")

            # Verify temperature defaults to 0.2
            call_kwargs = mock_init.call_args.kwargs
            assert call_kwargs["temperature"] == 0.2

    @pytest.mark.asyncio
    async def test_load_chat_model_zero_temperature(self) -> None:
        """Test that temperature can be set to 0."""
        mock_model = MagicMock()

        with patch("src.shared.utils.init_chat_model", new_callable=AsyncMock) as mock_init:
            mock_init.return_value = mock_model

            await load_chat_model("openai/gpt-4", temperature=0.0)

            call_kwargs = mock_init.call_args.kwargs
            assert call_kwargs["temperature"] == 0.0
