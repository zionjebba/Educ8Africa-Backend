"""Security utilities for hashing and verifying API keys, and handling JWT tokens."""

import hashlib
from typing import Optional
from datetime import datetime, timedelta
import jwt
from .config import settings
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.core.database import aget_db


def hash_key(key: str) -> str:
    """Hash the key using SHA-256."""
    key = key or ""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(api_key: Optional[str] = None) -> bool:
    """
    Verify the API key hashed is the same as the one in the settings.

    Args:
        - api_key (Optional[str]): The API key to verify.
        
    Returns:
        - bool: Whether the API key is valid.
    """
    if hash_key(api_key) == settings.HASHED_API_KEY:
        return True
    return False


def create_jwt_token(data: dict, expires_delta: timedelta = timedelta(hours=1)):
    """
    Creates a JWT (JSON Web Token) with the provided data and expiration time.

    Args:
        data (dict): The payload data to be encoded in the JWT.
        expires_delta (timedelta, optional): The time until the token expires. 
            Defaults to 1 hour.

    Returns:
        str: The encoded JWT string.

    Example:
        >>> data = {"user_id": 123, "role": "admin"}
        >>> token = create_jwt_token(data)
        >>> print(token)
        'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1...'

    Note:
        The token includes standard JWT claims:
        - exp (expiration time)
        - iat (issued at time)
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    print("Created token:", token)
    return token

def decode_jwt_token(token: str):
    """Decodes and validates a JWT token.

    This function attempts to decode a JWT (JSON Web Token) using the application's
    secret key and specified algorithm from settings. If the token is valid, it returns
    the decoded payload. If decoding fails, it logs the error and re-raises the exception.

    Args:
        token (str): The JWT token string to decode.

    Returns:
        dict: The decoded token payload containing the claims.

    Raises:
        jwt.InvalidTokenError: If the token is invalid, expired, or improperly formatted.
        Exception: Any other exceptions that occur during token decoding.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        print("Decoded payload:", payload)  # Debug print
        return payload
    except Exception as e:
        print(f"JWT Decode Error: {str(e)}")
        raise

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(aget_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT cookie
    Raises 401 if not authenticated
    """
    token = request.cookies.get("auth_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        payload = decode_jwt_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        result = await db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )