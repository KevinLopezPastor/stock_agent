import json
import logging
import os
import sys
import uuid
import traceback
import asyncio
from typing import AsyncGenerator

import httpx  # For connectivity checks
from fastapi import FastAPI, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

# --- OBS IMPORTS ---
from agent.observability import get_langfuse_handler, _load_langfuse_credentials

# --- LOGGING CONFIG ---
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL, 
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# --- DIAGNOSTIC: Force critical logs to stdout ---
def log_signal(msg: str):
    print(f">>> [SIGNAL] {msg}", file=sys.stdout)
    sys.stdout.flush()
    logger.info(f"[SIGNAL] {msg}")

# --- NETWORK TEST ---
async def test_langfuse_connectivity():
    creds = _load_langfuse_credentials()
    base_url = creds.get("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")
    pk = creds.get("LANGFUSE_PUBLIC_KEY", "")
    
    masked_pk = f"{pk[:8]}...{pk[-4:]}" if len(pk) > 12 else "INVALID"
    log_signal(f"Testing connectivity to Langfuse Host: {base_url} (PK Status: {masked_pk})")
    
    try:
        import socket
        host_to_resolve = base_url.replace("https://", "").replace("http://", "").split("/")[0]
        ip_addr = socket.gethostbyname(host_to_resolve)
        log_signal(f"DNS Resolve: {host_to_resolve} -> {ip_addr}")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/api/public/health")
            log_signal(f"Langfuse Net Test: Status={response.status_code} Response={response.text}")
    except Exception as e:
        log_signal(f"Langfuse Net Test FAILURE: {str(e)}")

# --- GRAPH INIT ---
agent_graph = None
init_error = None

try:
    from agent.graph import create_agent_graph
    agent_graph = create_agent_graph()
    log_signal(">>> [BOOT] Stock Agent Core initialized. Version 81 (OTEL Logging + Safe Flush).")
except Exception as e:
    init_error = f"Import Error: {str(e)}\n{traceback.format_exc()}"
    log_signal(f">>> [BOOT FAIL] Component Initialization Failed: {init_error}")

# App Definition
app = FastAPI(
    title="Stock Agent Sensor API",
    description="Diagnostic Sensor Release (Version 81)",
    version="1.0.81",
)

# Health Check
@app.get("/ping")
async def ping():
    return {
        "status": "healthy" if init_error is None else "degraded",
        "version": "1.0.80"
    }

# Agent Invocation (SSE streaming)
@app.post("/invocations")
async def invocations(
    request: Request
):
    # RUN SYNC NETWORK TEST ON FIRST CALL OR Startup
    await test_langfuse_connectivity()

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
            trace_name="stock-agent-v80",
        )
        
        if langfuse_handler:
            log_signal(f">>> [OBS] Langfuse handler created successfully (Host: {getattr(langfuse_handler, 'host', 'Default')})")
        else:
            log_signal(">>> [OBS] Langfuse DISABLED: Missing credentials or initialization error.")

        async def event_stream() -> AsyncGenerator[dict, None]:
            config = {
                "configurable": {"thread_id": thread_id},
                "callbacks": [langfuse_handler] if langfuse_handler else [],
                "run_name": "stock-agent-v84",
                "metadata": {
                    "user_id": user_sub,
                    "session_id": thread_id
                }
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
            finally:
                if langfuse_handler:
                    try:
                        # Flush the background thread explicitly!
                        log_signal("Flushing Langfuse traces to network...")
                        # We use asyncio.to_thread to prevent blocking the async generator shutdown
                        await asyncio.to_thread(langfuse_handler.flush)
                        log_signal("Langfuse flush complete.")
                    except Exception as fe:
                        log_signal(f"Error flushing traces: {fe}")

        return EventSourceResponse(event_stream())

    except Exception as e:
        logger.error(f"Request Failure: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail={"message": "Failed to process request"})
