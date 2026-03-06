"""
Security Module
===============

Authentication and authorization logic including JWT token management,
password hashing, and user verification.
"""

from datetime import datetime, timedelta
from typing import Optional, Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session, load_only

from backend.app.core.config import settings
from backend.app.db.base import get_db

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hash.
    
    Args:
        plain_password: The plain text password.
        hashed_password: The bcrypt hashed password.
        
    Returns:
        bool: True if password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The plain text password.
        
    Returns:
        str: The bcrypt hashed password.
    """
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: The payload data to encode in the token.
        expires_delta: Optional expiration time delta.
        
    Returns:
        str: The encoded JWT token.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token with longer expiration.
    
    Args:
        data: The payload data to encode in the token.
        
    Returns:
        str: The encoded JWT refresh token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token to decode.
        
    Returns:
        dict: The decoded token payload.
        
    Raises:
        JWTError: If token is invalid or expired.
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db)
):
    """
    Get the current authenticated user from JWT token.
    
    This is a FastAPI dependency that extracts and validates the JWT token,
    then retrieves the corresponding user from the database.
    
    Args:
        token: The JWT token from the Authorization header.
        db: Database session.
        
    Returns:
        User: The authenticated user object.
        
    Raises:
        HTTPException: If token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
        
        # Check token type
        if payload.get("type") != "access":
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Import here to avoid circular imports
    from backend.app.db.models import User
    
    try:
        lookup_id = UUID(user_id)
    except (TypeError, ValueError):
        lookup_id = user_id

    user = (
        db.query(User)
        .options(
            load_only(
                User.id,
                User.email,
                User.password_hash,
                User.is_active,
                User.is_superuser,
            )
        )
        .filter(User.id == lookup_id)
        .first()
    )
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    return user


async def get_current_active_superuser(
    current_user: Annotated["User", Depends(get_current_user)]
):
    """
    Get the current user and verify they are a superuser.
    
    Args:
        current_user: The authenticated user from get_current_user.
        
    Returns:
        User: The authenticated superuser.
        
    Raises:
        HTTPException: If user is not a superuser.
    """
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user


def verify_token_type(token: str, expected_type: str) -> bool:
    """
    Verify that a token is of the expected type.
    
    Args:
        token: The JWT token to verify.
        expected_type: The expected token type ('access' or 'refresh').
        
    Returns:
        bool: True if token type matches, False otherwise.
    """
    try:
        payload = decode_token(token)
        return payload.get("type") == expected_type
    except JWTError:
        return False
