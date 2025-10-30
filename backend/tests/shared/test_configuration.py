"""Tests for configuration module - TDD approach (write tests first)."""

from typing import Any

import pytest
from pydantic_core import ValidationError

from src.shared.configuration import BaseConfiguration, ensure_base_configuration


class TestBaseConfiguration:
    """Test the BaseConfiguration dataclass."""

    def test_base_configuration_defaults(self) -> None:
        """Test that BaseConfiguration has correct default values."""
        config = BaseConfiguration()

        assert config.retriever_provider == "supabase"
        assert config.filter_kwargs == {}
        assert config.k == 5

    def test_base_configuration_custom_values(self) -> None:
        """Test creating BaseConfiguration with custom values."""
        config = BaseConfiguration(
            retriever_provider="supabase", filter_kwargs={"user_id": "123"}, k=10
        )

        assert config.retriever_provider == "supabase"
        assert config.filter_kwargs == {"user_id": "123"}
        assert config.k == 10

    def test_base_configuration_empty_filter_kwargs(self) -> None:
        """Test that filter_kwargs defaults to empty dict."""
        config = BaseConfiguration(k=3)

        assert config.filter_kwargs == {}
        assert isinstance(config.filter_kwargs, dict)

    def test_base_configuration_is_immutable(self) -> None:
        """Test that BaseConfiguration is frozen (immutable)."""
        config = BaseConfiguration()

        with pytest.raises((AttributeError, TypeError, ValidationError)):
            config.k = 10  # type: ignore

    def test_base_configuration_type_validation(self) -> None:
        """Test that BaseConfiguration validates types."""
        # Valid types should work
        config = BaseConfiguration(
            retriever_provider="supabase", filter_kwargs={"key": "value"}, k=5
        )
        assert config.k == 5

        # Invalid types should raise an error (Pydantic validation)
        with pytest.raises((TypeError, ValueError)):
            BaseConfiguration(k="not_a_number")  # type: ignore


class TestEnsureBaseConfiguration:
    """Test the ensure_base_configuration function."""

    def test_ensure_base_configuration_with_empty_config(self) -> None:
        """Test with empty RunnableConfig - should return defaults."""
        config = ensure_base_configuration({})

        assert config.retriever_provider == "supabase"
        assert config.filter_kwargs == {}
        assert config.k == 5

    def test_ensure_base_configuration_with_none(self) -> None:
        """Test with None as config - should return defaults."""
        config = ensure_base_configuration(None)

        assert config.retriever_provider == "supabase"
        assert config.filter_kwargs == {}
        assert config.k == 5

    def test_ensure_base_configuration_with_configurable(self) -> None:
        """Test extracting configuration from configurable dict."""
        runnable_config: dict[str, Any] = {
            "configurable": {
                "retriever_provider": "supabase",
                "filter_kwargs": {"user_id": "abc123"},
                "k": 10,
            }
        }

        config = ensure_base_configuration(runnable_config)

        assert config.retriever_provider == "supabase"
        assert config.filter_kwargs == {"user_id": "abc123"}
        assert config.k == 10

    def test_ensure_base_configuration_with_partial_configurable(self) -> None:
        """Test with partial configurable - should use defaults for missing values."""
        runnable_config: dict[str, Any] = {"configurable": {"k": 20}}

        config = ensure_base_configuration(runnable_config)

        assert config.retriever_provider == "supabase"  # default
        assert config.filter_kwargs == {}  # default
        assert config.k == 20  # provided

    def test_ensure_base_configuration_with_extra_keys(self) -> None:
        """Test that extra keys in configurable are ignored."""
        runnable_config: dict[str, Any] = {
            "configurable": {
                "retriever_provider": "supabase",
                "k": 7,
                "extra_key": "should_be_ignored",
                "another_extra": 123,
            }
        }

        config = ensure_base_configuration(runnable_config)

        assert config.retriever_provider == "supabase"
        assert config.k == 7
        assert not hasattr(config, "extra_key")

    def test_ensure_base_configuration_with_nested_filter_kwargs(self) -> None:
        """Test with complex nested filter_kwargs."""
        runnable_config: dict[str, Any] = {
            "configurable": {
                "filter_kwargs": {
                    "user_id": "user123",
                    "metadata": {"source": "pdf", "tags": ["important", "urgent"]},
                }
            }
        }

        config = ensure_base_configuration(runnable_config)

        assert config.filter_kwargs["user_id"] == "user123"
        assert config.filter_kwargs["metadata"]["source"] == "pdf"
        assert config.filter_kwargs["metadata"]["tags"] == ["important", "urgent"]

    def test_ensure_base_configuration_preserves_zero_k(self) -> None:
        """Test that k=0 is preserved and not replaced with default."""
        runnable_config: dict[str, Any] = {"configurable": {"k": 0}}

        config = ensure_base_configuration(runnable_config)

        # k=0 should be preserved, not replaced with default
        assert config.k == 0

    def test_ensure_base_configuration_with_top_level_keys(self) -> None:
        """Test that top-level keys (not in configurable) are ignored."""
        runnable_config: dict[str, Any] = {
            "retriever_provider": "should_be_ignored",
            "k": 999,
            "configurable": {"k": 3},
        }

        config = ensure_base_configuration(runnable_config)

        # Should only use values from 'configurable', not top-level
        assert config.k == 3
        assert config.retriever_provider == "supabase"  # default, since not in configurable

    def test_ensure_base_configuration_idempotent(self) -> None:
        """Test that calling ensure_base_configuration multiple times is idempotent."""
        runnable_config: dict[str, Any] = {
            "configurable": {"k": 15, "filter_kwargs": {"test": "value"}}
        }

        config1 = ensure_base_configuration(runnable_config)
        config2 = ensure_base_configuration(runnable_config)

        assert config1.k == config2.k
        assert config1.filter_kwargs == config2.filter_kwargs
        assert config1.retriever_provider == config2.retriever_provider

    def test_ensure_base_configuration_empty_configurable(self) -> None:
        """Test with configurable key present but empty."""
        runnable_config: dict[str, Any] = {"configurable": {}}

        config = ensure_base_configuration(runnable_config)

        # Should return all defaults
        assert config.retriever_provider == "supabase"
        assert config.filter_kwargs == {}
        assert config.k == 5

    def test_ensure_base_configuration_accepts_camelcase_from_frontend(self) -> None:
        """Test that configuration accepts camelCase field names from JSON (frontend compatibility).

        This is CRITICAL for frontend integration. The frontend sends camelCase
        (retrieverProvider, filterKwargs) but Python uses snake_case internally.
        Pydantic aliases enable this compatibility.
        """
        # Simulate JSON from frontend with camelCase field names
        runnable_config: dict[str, Any] = {
            "configurable": {
                "retrieverProvider": "supabase",  # camelCase from frontend
                "filterKwargs": {"user_id": "123"},  # camelCase from frontend
                "k": 10
            }
        }

        config = ensure_base_configuration(runnable_config)

        # Should correctly parse camelCase and map to snake_case attributes
        assert config.retriever_provider == "supabase"
        assert config.filter_kwargs == {"user_id": "123"}
        assert config.k == 10

    def test_ensure_base_configuration_accepts_both_naming_conventions(self) -> None:
        """Test that both camelCase and snake_case work (backward compatibility)."""
        # Test with snake_case (Python convention)
        snake_case_config = ensure_base_configuration({
            "configurable": {
                "retriever_provider": "supabase",
                "filter_kwargs": {"test": "value"},
                "k": 7
            }
        })

        assert snake_case_config.retriever_provider == "supabase"
        assert snake_case_config.filter_kwargs == {"test": "value"}
        assert snake_case_config.k == 7

        # Test with camelCase (frontend convention)
        camel_case_config = ensure_base_configuration({
            "configurable": {
                "retrieverProvider": "supabase",
                "filterKwargs": {"test": "value"},
                "k": 7
            }
        })

        assert camel_case_config.retriever_provider == "supabase"
        assert camel_case_config.filter_kwargs == {"test": "value"}
        assert camel_case_config.k == 7

        # Both should produce identical configurations
        assert snake_case_config.retriever_provider == camel_case_config.retriever_provider
        assert snake_case_config.filter_kwargs == camel_case_config.filter_kwargs
        assert snake_case_config.k == camel_case_config.k
