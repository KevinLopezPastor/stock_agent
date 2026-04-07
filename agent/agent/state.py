"""
Agent state schema for the LangGraph ReAct agent.
"""

from typing import Annotated, Sequence
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State passed between nodes in the LangGraph agent.

    Attributes:
        messages: Conversation history. The `add_messages` reducer appends
                  new messages and handles deduplication by ID.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
