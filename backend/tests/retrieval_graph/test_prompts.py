"""Tests for retrieval graph prompt templates.

This test suite validates the prompt templates used for routing and response generation,
ensuring they match the TypeScript implementation exactly.
"""

import pytest
from langchain_core.prompts import ChatPromptTemplate

from src.retrieval_graph.prompts import ROUTER_SYSTEM_PROMPT, RESPONSE_SYSTEM_PROMPT


class TestRouterPrompt:
    """Test suite for ROUTER_SYSTEM_PROMPT."""

    def test_router_prompt_exists(self):
        """Test that ROUTER_SYSTEM_PROMPT is defined."""
        assert ROUTER_SYSTEM_PROMPT is not None, "ROUTER_SYSTEM_PROMPT must be defined"

    def test_router_prompt_type(self):
        """Test that ROUTER_SYSTEM_PROMPT is a ChatPromptTemplate."""
        assert isinstance(ROUTER_SYSTEM_PROMPT, ChatPromptTemplate), \
            "ROUTER_SYSTEM_PROMPT must be a ChatPromptTemplate"

    def test_router_prompt_has_messages(self):
        """Test that router prompt has system and human messages."""
        # ChatPromptTemplate should have at least 2 messages (system, human)
        assert len(ROUTER_SYSTEM_PROMPT.messages) >= 2, \
            "Router prompt should have at least system and human messages"

    def test_router_prompt_first_message_is_system(self):
        """Test that first message is a system message."""
        first_msg = ROUTER_SYSTEM_PROMPT.messages[0]
        # Check if it's a system message
        assert hasattr(first_msg, 'prompt'), "First message should have prompt attribute"
        # In LangChain, system messages have type 'system'
        msg_type = getattr(first_msg, 'type', None) or first_msg.__class__.__name__.lower()
        assert 'system' in msg_type.lower(), "First message should be a system message"

    def test_router_prompt_second_message_is_human(self):
        """Test that second message is a human message."""
        second_msg = ROUTER_SYSTEM_PROMPT.messages[1]
        # Check if it's a human message
        msg_type = getattr(second_msg, 'type', None) or second_msg.__class__.__name__.lower()
        assert 'human' in msg_type.lower(), "Second message should be a human message"

    def test_router_prompt_contains_query_variable(self):
        """Test that router prompt expects 'query' input variable."""
        input_vars = ROUTER_SYSTEM_PROMPT.input_variables
        assert 'query' in input_vars, "Router prompt must have 'query' as input variable"

    def test_router_prompt_system_content_mentions_routing(self):
        """Test that system message mentions routing functionality."""
        first_msg = ROUTER_SYSTEM_PROMPT.messages[0]
        system_content = str(first_msg.prompt.template).lower()

        # Should mention key routing concepts
        assert 'routing' in system_content or 'route' in system_content or 'determine' in system_content, \
            "System prompt should mention routing"
        assert 'retrieve' in system_content, "System prompt should mention 'retrieve' option"
        assert 'direct' in system_content, "System prompt should mention 'direct' option"

    def test_router_prompt_can_format(self):
        """Test that router prompt can be formatted with query input."""
        try:
            result = ROUTER_SYSTEM_PROMPT.format_messages(query="What is AI?")
            assert len(result) >= 2, "Should produce at least 2 messages"
            assert any("What is AI?" in str(msg.content) for msg in result), \
                "Query should appear in formatted messages"
        except Exception as e:
            pytest.fail(f"Router prompt formatting failed: {e}")

    def test_router_prompt_matches_typescript_structure(self):
        """Test that prompt structure matches TypeScript implementation."""
        # TypeScript uses: ChatPromptTemplate.fromMessages([['system', ...], ['human', '{query}']])
        assert len(ROUTER_SYSTEM_PROMPT.messages) == 2, \
            "Should have exactly 2 messages like TypeScript"

        # Human message should contain {query} placeholder
        human_msg = ROUTER_SYSTEM_PROMPT.messages[1]
        human_template = str(human_msg.prompt.template)
        assert '{query}' in human_template or 'query' in ROUTER_SYSTEM_PROMPT.input_variables, \
            "Human message should use {query} placeholder"

    def test_router_prompt_instructions_clarity(self):
        """Test that routing instructions are clear in system message."""
        first_msg = ROUTER_SYSTEM_PROMPT.messages[0]
        system_content = str(first_msg.prompt.template).lower()

        # Should explain what to respond with
        assert 'respond' in system_content or 'answer' in system_content, \
            "Should explain response format"


class TestResponsePrompt:
    """Test suite for RESPONSE_SYSTEM_PROMPT."""

    def test_response_prompt_exists(self):
        """Test that RESPONSE_SYSTEM_PROMPT is defined."""
        assert RESPONSE_SYSTEM_PROMPT is not None, "RESPONSE_SYSTEM_PROMPT must be defined"

    def test_response_prompt_type(self):
        """Test that RESPONSE_SYSTEM_PROMPT is a ChatPromptTemplate."""
        assert isinstance(RESPONSE_SYSTEM_PROMPT, ChatPromptTemplate), \
            "RESPONSE_SYSTEM_PROMPT must be a ChatPromptTemplate"

    def test_response_prompt_has_system_message(self):
        """Test that response prompt has at least a system message."""
        assert len(RESPONSE_SYSTEM_PROMPT.messages) >= 1, \
            "Response prompt should have at least one system message"

    def test_response_prompt_first_message_is_system(self):
        """Test that first message is a system message."""
        first_msg = RESPONSE_SYSTEM_PROMPT.messages[0]
        msg_type = getattr(first_msg, 'type', None) or first_msg.__class__.__name__.lower()
        assert 'system' in msg_type.lower(), "First message should be a system message"

    def test_response_prompt_contains_question_variable(self):
        """Test that response prompt expects 'question' input variable."""
        input_vars = RESPONSE_SYSTEM_PROMPT.input_variables
        assert 'question' in input_vars, "Response prompt must have 'question' as input variable"

    def test_response_prompt_contains_context_variable(self):
        """Test that response prompt expects 'context' input variable."""
        input_vars = RESPONSE_SYSTEM_PROMPT.input_variables
        assert 'context' in input_vars, "Response prompt must have 'context' as input variable"

    def test_response_prompt_system_content_mentions_qa(self):
        """Test that system message mentions question-answering."""
        first_msg = RESPONSE_SYSTEM_PROMPT.messages[0]
        system_content = str(first_msg.prompt.template).lower()

        # Should mention QA concepts
        assert 'question' in system_content or 'answer' in system_content, \
            "System prompt should mention question-answering"
        assert 'context' in system_content or 'retrieved' in system_content, \
            "System prompt should mention using context/retrieved documents"

    def test_response_prompt_mentions_conciseness(self):
        """Test that prompt instructs to be concise."""
        first_msg = RESPONSE_SYSTEM_PROMPT.messages[0]
        system_content = str(first_msg.prompt.template).lower()

        # Should instruct conciseness
        assert 'concise' in system_content or 'sentence' in system_content, \
            "Should instruct to be concise"

    def test_response_prompt_mentions_dont_know_handling(self):
        """Test that prompt mentions saying 'don't know' when appropriate."""
        first_msg = RESPONSE_SYSTEM_PROMPT.messages[0]
        system_content = str(first_msg.prompt.template).lower()

        # Should mention handling unknown answers
        assert "don't know" in system_content or "do not know" in system_content, \
            "Should instruct to say 'don't know' when answer is unknown"

    def test_response_prompt_can_format(self):
        """Test that response prompt can be formatted with required inputs."""
        try:
            result = RESPONSE_SYSTEM_PROMPT.format_messages(
                question="What is AI?",
                context="AI stands for Artificial Intelligence."
            )
            assert len(result) >= 1, "Should produce at least 1 message"

            # Check that both inputs appear in formatted message
            message_content = str(result[0].content)
            assert "What is AI?" in message_content, "Question should appear in formatted message"
            assert "Artificial Intelligence" in message_content, \
                "Context should appear in formatted message"
        except Exception as e:
            pytest.fail(f"Response prompt formatting failed: {e}")

    def test_response_prompt_matches_typescript_structure(self):
        """Test that prompt structure matches TypeScript implementation."""
        # TypeScript uses: ChatPromptTemplate.fromMessages([['system', ...]])
        assert len(RESPONSE_SYSTEM_PROMPT.messages) >= 1, \
            "Should have at least one system message like TypeScript"

        # System message should contain {question} and {context} placeholders
        system_msg = RESPONSE_SYSTEM_PROMPT.messages[0]
        system_template = str(system_msg.prompt.template)

        input_vars = RESPONSE_SYSTEM_PROMPT.input_variables
        assert 'question' in input_vars or '{question}' in system_template, \
            "Should use {question} placeholder"
        assert 'context' in input_vars or '{context}' in system_template, \
            "Should use {context} placeholder"

    def test_response_prompt_instructions_complete(self):
        """Test that response prompt has complete QA instructions."""
        first_msg = RESPONSE_SYSTEM_PROMPT.messages[0]
        system_content = str(first_msg.prompt.template).lower()

        # Should be for question-answering tasks
        assert 'question-answering' in system_content or 'answering' in system_content, \
            "Should identify as QA task"

        # Should mention using retrieved context
        assert 'context' in system_content, "Should mention using context"


class TestPromptsIntegration:
    """Integration tests for prompt usage patterns."""

    def test_router_prompt_with_simple_query(self):
        """Test router prompt with a simple query."""
        messages = ROUTER_SYSTEM_PROMPT.format_messages(query="Hello")

        assert len(messages) >= 2, "Should format into multiple messages"
        # Human message should contain the query
        assert any("Hello" in str(msg.content) for msg in messages)

    def test_router_prompt_with_complex_query(self):
        """Test router prompt with a complex document-related query."""
        query = "What does the document say about AI ethics?"
        messages = ROUTER_SYSTEM_PROMPT.format_messages(query=query)

        assert len(messages) >= 2
        assert any("AI ethics" in str(msg.content) for msg in messages)

    def test_response_prompt_with_context(self):
        """Test response prompt with question and context."""
        question = "What is machine learning?"
        context = "Machine learning is a subset of AI that enables systems to learn from data."

        messages = RESPONSE_SYSTEM_PROMPT.format_messages(
            question=question,
            context=context
        )

        assert len(messages) >= 1
        content = str(messages[0].content)
        assert "machine learning" in content.lower()
        assert "subset of AI" in content or "learn from data" in content

    def test_response_prompt_with_empty_context(self):
        """Test response prompt with empty context."""
        messages = RESPONSE_SYSTEM_PROMPT.format_messages(
            question="What is AI?",
            context=""
        )

        assert len(messages) >= 1
        # Should still format successfully
        assert "What is AI?" in str(messages[0].content)

    def test_prompts_are_distinct(self):
        """Test that router and response prompts are different objects."""
        assert ROUTER_SYSTEM_PROMPT is not RESPONSE_SYSTEM_PROMPT, \
            "Router and response prompts should be distinct objects"

        # They should have different input variables
        router_vars = set(ROUTER_SYSTEM_PROMPT.input_variables)
        response_vars = set(RESPONSE_SYSTEM_PROMPT.input_variables)

        assert router_vars != response_vars, \
            "Router and response prompts should have different input variables"

    def test_prompts_exported_correctly(self):
        """Test that both prompts are exported from module."""
        from src.retrieval_graph.prompts import ROUTER_SYSTEM_PROMPT, RESPONSE_SYSTEM_PROMPT

        assert ROUTER_SYSTEM_PROMPT is not None
        assert RESPONSE_SYSTEM_PROMPT is not None
