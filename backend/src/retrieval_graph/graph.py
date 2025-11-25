"""Retrieval graph for question-answering with document retrieval.

This module implements a LangGraph workflow that:
1. Analyzes user queries to determine if document retrieval is needed
2. Either retrieves relevant documents and generates contextual answers,
   or provides direct answers for simple queries
3. Supports streaming responses for frontend SSE integration

Graph structure:
START → checkQueryType → [RETRIEVE path OR DIRECT path] → END

RETRIEVE path: checkQueryType → retrieveDocuments → generateResponse → END
DIRECT path: checkQueryType → directAnswer → END
"""

from inspect import isawaitable
from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from src.retrieval_graph.configuration import ensure_agent_configuration
from src.retrieval_graph.prompts import (
    NO_DOCUMENTS_REFUSAL,
    RESPONSE_SYSTEM_PROMPT,
    ROUTER_SYSTEM_PROMPT,
)
from src.retrieval_graph.state import AgentState
from src.retrieval_graph.utils import format_docs
from src.shared import retrieval as shared_retrieval
from src.shared import utils as shared_utils


async def make_retriever(config: RunnableConfig):
    """Wrapper around shared retriever factory to aid patching in tests."""
    return await shared_retrieval.make_retriever(config)


async def load_chat_model(name: str, *, temperature: float = 0.2):
    """Wrapper to allow tests to patch shared.utils.load_chat_model."""
    result = shared_utils.load_chat_model(name, temperature=temperature)

    if isawaitable(result):
        return await result

    return result


# Routing schema for structured output
class RouteSchema(BaseModel):
    """Schema for routing decisions."""
    route: Literal["retrieve", "direct"]
    direct_answer: str | None = None


async def check_query_type(state: AgentState, config: RunnableConfig) -> dict[str, str]:
    """
    Analyze query to determine if document retrieval is needed.

    This node uses an LLM with structured output to classify the query as either:
    - "retrieve": Requires document retrieval to answer
    - "direct": Can be answered directly without retrieval

    Args:
        state: The current AgentState containing the user query.
        config: RunnableConfig dictionary with configuration parameters.

    Returns:
        A dict with {"route": "retrieve" | "direct"}.

    Example:
        >>> state = {"query": "What is LangChain?", "messages": [], "route": "", "documents": []}
        >>> result = await check_query_type(state, config)
        >>> assert result["route"] in ["retrieve", "direct"]
    """
    configuration = ensure_agent_configuration(config)
    model = await load_chat_model(configuration.query_model)

    # Format the routing prompt with the query
    formatted_prompt = await ROUTER_SYSTEM_PROMPT.ainvoke({"query": state["query"]})

    # Use structured output to get routing decision
    response = await model.with_structured_output(RouteSchema).ainvoke(formatted_prompt)

    return {"route": response.route}


async def route_query(state: AgentState) -> Literal["retrieveDocuments", "directAnswer"]:
    """
    Conditional routing function based on query type.

    This function determines which node to execute next based on the
    routing decision made by check_query_type.

    Args:
        state: The current AgentState containing the route decision.

    Returns:
        The name of the next node: "retrieveDocuments" or "directAnswer".

    Raises:
        ValueError: If route is not set or is invalid.

    Example:
        >>> state = {"route": "retrieve", ...}
        >>> next_node = await route_query(state)
        >>> assert next_node == "retrieveDocuments"
    """
    route = state.get("route")

    if not route:
        raise ValueError("Route is not set")

    if route == "retrieve":
        return "retrieveDocuments"
    elif route == "direct":
        return "directAnswer"
    else:
        raise ValueError(f"Invalid route: {route}")


async def retrieve_documents(state: AgentState, config: RunnableConfig) -> dict:
    """
    Retrieve relevant documents from the vector store.

    This node uses the configured retriever to fetch documents relevant
    to the user's query from the vector store. If no documents are found,
    sets force_refusal=True to prevent hallucination in generateResponse.

    Args:
        state: The current AgentState containing the user query.
        config: RunnableConfig dictionary with configuration parameters.

    Returns:
        A dict with {"documents": [...], "force_refusal": bool} containing
        retrieved documents and refusal flag.

    Example:
        >>> state = {"query": "What is LangChain?", ...}
        >>> result = await retrieve_documents(state, config)
        >>> assert "documents" in result
        >>> assert "force_refusal" in result
    """
    retriever = await make_retriever(config)
    documents = await retriever.ainvoke(state["query"])

    # ANTI-HALLUCINATION: Set force_refusal when no documents found
    if not documents or len(documents) == 0:
        return {"documents": [], "force_refusal": True}

    return {"documents": documents, "force_refusal": False}


async def generate_response(state: AgentState, config: RunnableConfig) -> dict:
    """
    Generate an answer using retrieved document context.

    This node formats the retrieved documents as context and uses an LLM
    to generate a comprehensive answer based on that context.

    ANTI-HALLUCINATION: If force_refusal is True or no documents exist,
    returns a refusal message instead of calling the LLM. This prevents
    the LLM from hallucinating answers from its training data.

    Args:
        state: The current AgentState containing query and retrieved documents.
        config: RunnableConfig dictionary with configuration parameters.

    Returns:
        A dict with {"messages": [HumanMessage, AIMessage]} containing
        the conversation update.

    Example:
        >>> state = {"query": "What is LangChain?", "documents": [...], ...}
        >>> result = await generate_response(state, config)
        >>> assert "messages" in result
        >>> assert len(result["messages"]) == 2
    """
    from langchain_core.messages import AIMessage

    # Create human message with the query
    user_human_message = HumanMessage(content=state["query"])

    # ANTI-HALLUCINATION CHECK: Refuse if no documents or force_refusal is set
    documents = state.get("documents", [])
    force_refusal = state.get("force_refusal", False)

    if force_refusal or not documents or len(documents) == 0:
        # Return refusal message - DO NOT call LLM with empty context
        refusal_message = AIMessage(content=NO_DOCUMENTS_REFUSAL)
        return {"messages": [user_human_message, refusal_message]}

    configuration = ensure_agent_configuration(config)
    model = await load_chat_model(configuration.query_model)

    # Format documents as context
    context = format_docs(documents)

    # Format the response prompt with query and context
    formatted_prompt = await RESPONSE_SYSTEM_PROMPT.ainvoke({
        "question": state["query"],
        "context": context,
    })

    # Create formatted prompt message with context
    formatted_prompt_message = HumanMessage(content=str(formatted_prompt))

    # Build message history including the formatted prompt
    message_history = [*state.get("messages", []), formatted_prompt_message]

    # Generate response
    response = await model.ainvoke(message_history)

    # Return both the user query and AI response
    return {"messages": [user_human_message, response]}


async def answer_query_directly(state: AgentState, config: RunnableConfig) -> dict:
    """
    Answer simple greetings directly without document retrieval.

    RESTRICTED: This node ONLY handles simple greetings like "hello", "hi",
    "how are you", "thanks", etc. All other queries should go through
    the retrieve path.

    The LLM is explicitly instructed to only respond to greetings and
    redirect any actual questions to the document retrieval path.

    Args:
        state: The current AgentState containing the user query.
        config: RunnableConfig dictionary with configuration parameters.

    Returns:
        A dict with {"messages": [HumanMessage, AIMessage]} containing
        the conversation update.

    Example:
        >>> state = {"query": "Hello", ...}
        >>> result = await answer_query_directly(state, config)
        >>> assert "messages" in result
        >>> assert len(result["messages"]) == 2
    """
    from langchain_core.messages import AIMessage, SystemMessage

    configuration = ensure_agent_configuration(config)
    model = await load_chat_model(configuration.query_model)

    # Create human message with the query
    user_human_message = HumanMessage(content=state["query"])

    # RESTRICTED PROMPT: Only respond to greetings, refuse everything else
    greeting_system_prompt = SystemMessage(
        content="""You are a friendly document assistant. You can ONLY respond to simple greetings.

ALLOWED responses:
- Greetings like "hello", "hi", "hey" → Respond with a friendly greeting
- "how are you" → Respond briefly and ask how you can help with their documents
- "thanks", "thank you" → Respond with "You're welcome!"
- "bye", "goodbye" → Respond with a friendly goodbye

For ANY other query (questions, requests for information, etc.):
Respond: "I'd be happy to help! Please ask me a question about your uploaded documents."

Keep responses brief and friendly."""
    )

    # Get direct response from model with restricted prompt
    response = await model.ainvoke([greeting_system_prompt, user_human_message])

    return {"messages": [user_human_message, response]}


# Define the graph
builder = StateGraph(AgentState)

# Add all nodes
builder.add_node("checkQueryType", check_query_type)
builder.add_node("retrieveDocuments", retrieve_documents)
builder.add_node("generateResponse", generate_response)
builder.add_node("directAnswer", answer_query_directly)

# Define edges
builder.add_edge(START, "checkQueryType")

# Add conditional routing from checkQueryType
builder.add_conditional_edges(
    "checkQueryType",
    route_query,
    ["retrieveDocuments", "directAnswer"],
)

# Add edges for the RETRIEVE path
builder.add_edge("retrieveDocuments", "generateResponse")
builder.add_edge("generateResponse", END)

# Add edge for the DIRECT path
builder.add_edge("directAnswer", END)

# Compile the graph without checkpointer initially
# The checkpointer will be set during FastAPI startup via compile_with_checkpointer()
graph = builder.compile()


async def compile_with_checkpointer():
    """
    Recompile the graph with PostgresSaver checkpointer.

    This function should be called during FastAPI startup to initialize
    the checkpointer and recompile the graph with persistence enabled.

    IMPORTANT: This updates the module-level `graph` variable so that
    other modules importing it will get the checkpointer-enabled version.

    Returns:
        The compiled graph with checkpointer.

    Example:
        >>> # In FastAPI startup event
        >>> @app.on_event("startup")
        >>> async def startup():
        >>>     await compile_with_checkpointer()
    """
    global graph
    from src.shared.checkpointer import get_checkpointer

    checkpointer = await get_checkpointer()
    graph = builder.compile(checkpointer=checkpointer)
    return graph
