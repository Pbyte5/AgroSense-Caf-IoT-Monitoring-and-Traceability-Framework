from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from fastapi.security.oauth2 import SecurityScopes

from agrosense_api.core.config import get_settings
from agrosense_api.core.security import decode_access_token, decode_buyer_access_token
from agrosense_api.schemas.auth import AuthenticatedUser

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    scopes={
        "lots:read": "Read lot traceability and origin composition",
        "farms:read": "Read farm details and export contribution history",
        "lots:certify": "Certify export lots",
    },
)
buyer_jwt = HTTPBearer(
    scheme_name="BuyerJWT",
    description=(
        "JWT for a buyer. It must contain a buyer_id UUID claim and the traceability:read scope."
    ),
    bearerFormat="JWT",
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    security_scopes: SecurityScopes,
) -> AuthenticatedUser:
    settings = get_settings()
    if not settings.auth_username or not settings.jwt_secret_key.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )
    try:
        claims = decode_access_token(token)
    except (jwt.InvalidTokenError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    username = claims.get("sub")
    if not isinstance(username, str) or username != settings.auth_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scope_claim = claims.get("scope", "")
    if not isinstance(scope_claim, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_scopes = scope_claim.split()
    if not set(security_scopes.scopes).issubset(token_scopes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return AuthenticatedUser(username=username, scopes=token_scopes)


async def get_current_buyer_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(buyer_jwt)],
) -> UUID:
    settings = get_settings()
    if not settings.buyer_jwt_secret_key.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Buyer authentication is not configured",
        )
    try:
        claims = decode_buyer_access_token(credentials.credentials)
    except (jwt.InvalidTokenError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    buyer_id_claim = claims.get("buyer_id")
    if not isinstance(buyer_id_claim, str):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A buyer identity is required",
        )
    try:
        buyer_id = UUID(buyer_id_claim)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid buyer identity in access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    scope_claim = claims.get("scope", "")
    if not isinstance(scope_claim, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_scopes = set(scope_claim.split())
    if "traceability:read" not in token_scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return buyer_id
