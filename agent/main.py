import json
import logging
import os
import sys
import uuid
import traceback
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, Depends
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field

# --- OBS IMPORTS ---
from agent.observability import get_langfuse_handler

# --- LOGGING CONFIG ---
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL, 
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# --- GRAPH INIT ---
agent_graph = None
init_error = None

try:
    from agent.graph import create_agent_graph
    agent_graph = create_agent_graph()
    logger.info(">>> [BOOT] Stock Agent Core components initialized. Version 73 (Signal Enabled).")
    import sys
    sys.stdout.flush()
except Exception as e:
    init_error = f"Import Error: {str(e)}\n{traceback.format_exc()}"
    logger.error(f">>> [BOOT FAIL] Component Initialization Failed: {init_error}")
    import sys
    sys.stdout.flush()

# ---------------------------------------------------------------------------
# App Definition
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Stock Agent Signal API",
    description="Official Signal Release (Version 73)",
    version="1.0.73",
)

# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@app.get("/ping")
async def ping():
    return {
        "status": "healthy" if init_error is None else "degraded",
        "version": "1.0.73"
    }

# ---------------------------------------------------------------------------
# Agent Invocation (SSE streaming)
# ---------------------------------------------------------------------------
@app.post("/invocations")
async def invocations(
    request: Request
):
    # STABLE PRODUCTION AUTH
    headers_dict = dict(request.headers)
    user_email = headers_dict.get("x-amz-bedrock-agentcore-auth-user", "authenticated@agentcore.internal")
    user_sub = headers_dict.get("x-amz-bedrock-agentcore-auth-sub", str(uuid.uuid4()))
    
    if init_error:
        raise HTTPException(status_code=500, detail={"message": "System starting or degraded"})

    try:
        body = await request.json()
        query = body.get("query") or body.get("prompt", "Analyze stock data")
        thread_id = body.get("thread_id") or body.get("session_id", str(uuid.uuid4()))
        
        logger.info(f"Execution Request: query={query!r} thread_id={thread_id} user={user_email}")

        # --- DIAGNOSTIC OBS INIT ---
        langfuse_handler = get_langfuse_handler(
            user_id=user_sub,
            session_id=thread_id,
            trace_name="stock-agent-call-diag-71",
        )
        
        if langfuse_handler:
            logger.info(f">>> [OBS] Langfuse handler created successfully (Host: {getattr(langfuse_handler, 'host', 'Default')})")
        else:
            logger.warning(">>> [OBS] Langfuse DISABLED: Missing credentials or initialization error.")

        async def event_stream() -> AsyncGenerator[dict, None]:
            config = {
                "configurable": {"thread_id": thread_id},
                "callbacks": [langfuse_handler] if langfuse_handler else []
            }
            input_messages = {"messages": [("user", query)]}
            
            is_thinking = False

            try:
                async for event in agent_graph.astream_events(
                    input_messages,
                    config=config,
                    version="v2",
                ):
                    kind = event["event"]
                    if kind == "on_chat_model_stream":
                        content = event["data"]["chunk"].content
                        if not content: continue
                        
                        if "<thinking" in content:
                            is_thinking = True
                        
                        if not is_thinking:
                            yield {
                                "event": "message",
                                "data": json.dumps({"type": "token", "content": content})
                            }
                        
                        if "/thinking>" in content or "thinking>" in content:
                            is_thinking = False
                    
                    elif kind == "on_tool_start":
                        yield {
                            "event": "message",
                            "data": json.dumps({"type": "status", "node": "tools", "status": "Accessing financial documentation..."})
                        }

                yield {"event": "message", "data": json.dumps({"type": "done", "content": ""})}
            except Exception as e:
                logger.error(f"Stream Error: {traceback.format_exc()}")
                yield {"event": "message", "data": json.dumps({"type": "error", "content": "\n[SYSTEM ERROR] Stream interrupted."})}

        return EventSourceResponse(event_stream())

    except Exception as e:
        logger.error(f"Request Failure: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail={"message": "Failed to process request"})
