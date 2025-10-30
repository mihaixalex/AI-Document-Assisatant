"""State definitions for the retrieval graph.

This module defines the AgentState TypedDict which represents the state
structure for the question-answering agent with document retrieval.
"""

from typing import Annotated, Sequence, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from src.shared.state import reduce_docs


class AgentState(TypedDict):
    """
    Represents the state of the retrieval graph / agent.

    This TypedDict defines the structure of the agent state for the question-answering
    graph. It includes conversation messages, query information, routing decisions,
    and retrieved documents.

    The state is designed to match the TypeScript AgentStateAnnotation structure
    for frontend compatibility.

    Attributes:
        messages: Conversation history as a sequence of messages.
                 Uses add_messages reducer in LangGraph for proper message handling.
        query: The user's query/question string.
        route: The routing decision ("retrieve" or "direct").
              Determines if document retrieval is needed.
        documents: List of documents retrieved from vector store.
                  Uses reduce_docs reducer for concatenation and deduplication.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    query: str
    route: str
    documents: Annotated[list[Document], reduce_docs]
