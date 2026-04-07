import logging
import os
from typing import Literal

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# --- REDUCED IMPORTS ---
from agent.state import AgentState
from agent.prompts import SYSTEM_PROMPT
from agent.tools.stock_tools import retrieve_realtime_stock_price, retrieve_historical_stock_price
from agent.tools.knowledge_base import search_knowledge_base

logger = logging.getLogger(__name__)

def create_agent_graph():
    """
    Creates the Full AI Stock Agent (Version 48)
    """
    # -----------------------------------------------------------------------
    # 1. Tools
    # -----------------------------------------------------------------------
    tools = [
        retrieve_realtime_stock_price, 
        retrieve_historical_stock_price,
        search_knowledge_base
    ]
    tool_node = ToolNode(tools)

    # -----------------------------------------------------------------------
    # 2. LLM
    # -----------------------------------------------------------------------
    model_id = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
    logger.info(f"Using model: {model_id}")

    llm = ChatBedrockConverse(
        model_id=model_id,
        region_name="us-east-1",
        temperature=0,
        max_tokens=2048,
    )
    
    # Bind tools to the LLM
    llm_with_tools = llm.bind_tools(tools)

    # -----------------------------------------------------------------------
    # 3. Nodes
    # -----------------------------------------------------------------------
    def call_model(state: AgentState):
        messages = state["messages"]
        system_message = SystemMessage(content=SYSTEM_PROMPT)
        
        # Ensure messages are converted to LangChain message objects properly
        response = llm_with_tools.invoke([system_message] + list(messages))
        return {"messages": [response]}

    def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools"
        return "__end__"

    # -----------------------------------------------------------------------
    # 4. Building
    # -----------------------------------------------------------------------
    builder = StateGraph(AgentState)
    
    builder.add_node("agent", call_model)
    builder.add_node("tools", tool_node)
    
    builder.set_entry_point("agent")
    
    # Conditional logic
    builder.add_conditional_edges(
        "agent",
        should_continue,
    )
    
    builder.add_edge("tools", "agent")

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)
