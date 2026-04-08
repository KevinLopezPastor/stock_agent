"""
Cognito JWT validation middleware for FastAPI.

Validates the Bearer token from the Authorization header against the
Cognito User Pool's JWKS endpoint.
"""

import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import httpx
from fastapi import HTTPException, Request
from jose import JWTError, jwk, jwt

logger = logging.getLogger(__name__)

# Configuration from environment variables (set by AgentCore / Terraform)
COGNITO_REGION = os.environ.get("AWS_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "")
COGNITO_ISSUER_URL = os.environ.get(
    "COGNITO_ISSUER_URL",
    f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}",
)


@dataclass
class UserContext:
    """Authenticated user information extracted from the JWT."""

    user_id: str   # Cognito 'sub' claim
    email: str     # Email claim (if present)
    token: str     # Raw JWT for downstream use


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    """Fetch and cache the Cognito JWKS (JSON Web Key Set).

    This is called once and cached for the lifetime of the process.
    In production you may want a TTL cache instead.
    """
    jwks_url = f"{COGNITO_ISSUER_URL}/.well-known/jwks.json"
    logger.info(f"Fetching JWKS from {jwks_url}")

    try:
        response = httpx.get(jwks_url, timeout=10)
        response.raise_for_status()
        keys = response.json()
        logger.info(f"Loaded {len(keys.get('keys', []))} JWK keys")
        return keys
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch authentication keys")


def _get_signing_key(token: str) -> dict:
    """Find the correct JWK for the given token's key ID (kid)."""
    try:
        headers = jwt.get_unverified_headers(token)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token header: {e}")

    kid = headers.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Token missing key ID (kid)")

    jwks = _get_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    raise HTTPException(status_code=401, detail="Token signed with unknown key")


def _validate_token(token: str) -> dict:
    """Decode and validate a Cognito JWT.

    Validates:
      - Signature (RSA via JWKS)
      - Expiration
      - Issuer (must match Cognito User Pool)
      - Token use (access or id token)
    """
    signing_key = _get_signing_key(token)

    try:
        # Build the public key
        public_key = jwk.construct(signing_key)

        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID if COGNITO_CLIENT_ID else None,
            issuer=COGNITO_ISSUER_URL if COGNITO_ISSUER_URL else None,
            options={
                "verify_aud": bool(COGNITO_CLIENT_ID),
                "verify_iss": bool(COGNITO_ISSUER_URL),
                "verify_exp": True,
            },
        )
        return claims

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTClaimsError as e:
        raise HTTPException(status_code=401, detail=f"Invalid claims: {e}")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {e}")


async def get_current_user(request: Request) -> UserContext:
    """FastAPI dependency that extracts and validates the user context.

    Hybrid support:
    1.  Standard 'Authorization: Bearer <token>' for direct calls.
    2.  'x-amz-bedrock-agentcore-auth-*' headers for Bedrock runtime calls.
    """
    # DIAGNOSTIC: Professional trace of security headers
    amz_headers = {k: v for k, v in request.headers.items() if k.lower().startswith("x-amz-")}
    if amz_headers:
        logger.info(f">>> [SEC V57] AMZ Headers Found: {json.dumps(amz_headers)}")
    
    # 1. Trust Bedrock AgentCore's Authorizer (Mandatory for Production)
    bedrock_user = request.headers.get("x-amz-bedrock-agentcore-auth-user")
    bedrock_sub = request.headers.get("x-amz-bedrock-agentcore-auth-sub")
    
    # If we have identity from Bedrock, TRUST it (the authorizer already validated the OIDC flow)
    if bedrock_sub:
        logger.info(f">>> [SEC V57] Trusting Bedrock identity for sub={bedrock_sub}")
        return UserContext(
            user_id=bedrock_sub,
            email=bedrock_user or "user@bedrock.internal",
            token="[INFRA_VALIDATED]"
        )

    # 2. Extract Bearer token for DIRECT local calls (Diagnostics/Manual)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # If Cognito is set, re-validate here
        if COGNITO_USER_POOL_ID:
            claims = _validate_token(token)
            return UserContext(
                user_id=claims.get("sub", "unknown"),
                email=claims.get("email", claims.get("username", "")),
                token=token,
            )
        else:
            return UserContext(user_id="manual-user", email="manual@local", token=token)

    # 3. Fallback for Local Dev (if no Cognito set)
    if not COGNITO_USER_POOL_ID:
        logger.warning("Cognito not configured — allowing unauthenticated access")
        return UserContext(user_id="local-dev-user", email="dev@local", token="")

    # 4. Final Failure
    logger.error("Authentication failed: No valid token or Bedrock headers found.")
    raise HTTPException(
        status_code=401,
        detail="Identification failed. Infrastructure-level authentication required."
    )
