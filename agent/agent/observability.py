"""
Langfuse observability integration for the stock agent.
"""

import json
import logging
import os
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_langfuse_credentials() -> dict:
    """Load Langfuse credentials from Secrets Manager or environment variables."""
    # SHIELDED IMPORT
    import boto3
    
    secret_arn = os.environ.get("LANGFUSE_SECRET_ARN")

    if secret_arn:
        logger.info("Loading Langfuse credentials from Secrets Manager")
        try:
            client = boto3.client(
                "secretsmanager",
                region_name=os.environ.get("AWS_REGION", "us-east-1"),
            )
            response = client.get_secret_value(SecretId=secret_arn)
            return json.loads(response["SecretString"])
        except Exception as e:
            logger.warning(f"Failed to load from Secrets Manager: {e}, falling back to env vars")

    # Fallback to environment variables
    return {
        "LANGFUSE_PUBLIC_KEY": os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
        "LANGFUSE_SECRET_KEY": os.environ.get("LANGFUSE_SECRET_KEY", ""),
        "LANGFUSE_BASE_URL": os.environ.get("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com"),
    }


def get_langfuse_handler(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    trace_name: str = "stock-agent",
) -> Optional[object]:
    """Create a Langfuse callback handler for tracing an agent invocation."""
    try:
        # SHIELDED IMPORT - Handle Langfuse V3+ breaking change
        try:
            from langfuse.langchain import CallbackHandler
        except ImportError:
            # Fallback for Langfuse < v3.0
            from langfuse.callback import CallbackHandler
        
        creds = _load_langfuse_credentials()
        public_key = creds.get("LANGFUSE_PUBLIC_KEY", "")
        secret_key = creds.get("LANGFUSE_SECRET_KEY", "")
        base_url = creds.get("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")

        if not public_key or not secret_key:
            logger.warning("Langfuse credentials not configured — tracing disabled")
            return None

        # Set environment variables so the new V4 LangchainCallbackHandler picks them up
        os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
        os.environ["LANGFUSE_SECRET_KEY"] = secret_key
        os.environ["LANGFUSE_HOST"] = base_url

        try:
            from langfuse.langchain import CallbackHandler
            # V4 initialization takes no kwargs (relies on env vars for auth, metadata config for user/session)
            handler = CallbackHandler()
        except ImportError:
            # Fallback for Langfuse < v3.0
            from langfuse.callback import CallbackHandler
            handler = CallbackHandler(
                public_key=public_key,
                secret_key=secret_key,
                host=base_url,
                user_id=user_id,
                session_id=session_id,
                trace_name=trace_name,
                tags=["stock-agent", "agentcore"],
            )

        logger.debug(f"Langfuse handler created (trace={trace_name}, user={user_id})")
        return handler

    except Exception as e:
        logger.warning(f"Failed to create Langfuse handler: {e}")
        return None
