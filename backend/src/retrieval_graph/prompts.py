"""Prompt templates for the retrieval graph.

This module defines the ChatPromptTemplate objects used for:
1. Router decisions (retrieve vs direct answer)
2. Response generation with retrieved context
"""

from langchain_core.prompts import ChatPromptTemplate

# Router prompt - determines if document retrieval is needed
ROUTER_SYSTEM_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a routing assistant. Your job is to determine if a question needs document retrieval or can be answered directly.\n\n"
            "Respond with either:\n"
            "'retrieve' - if the question requires retrieving documents\n"
            "'direct' - if the question can be answered directly AND your direct answer",
        ),
        ("human", "{query}"),
    ]
)

# Response generation prompt - generates answer using retrieved context
RESPONSE_SYSTEM_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question.
    If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.

    question:
    {question}

    context:
    {context}
    """,
        ),
    ]
)
