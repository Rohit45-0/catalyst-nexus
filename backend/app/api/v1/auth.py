"""
Authentication & User Management API Endpoints
==============================================

Handles user registration, login, JWT token management,
and user profile operations.
"""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import secrets

from backend.app.core.config import settings
from backend.app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    get_current_user,
)
from backend.app.db.base import get_db
from backend.app.db.schemas import (
    UserCreate,
    UserResponse,
    Token,
    UserUpdate,
)
from backend.app.db.models import User
from backend.app.services.auth.instagram_oauth import InstagramOAuthService

from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Configure OAuth for Google
starlette_config = Config(environ={
    "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID or "",
    "GOOGLE_CLIENT_SECRET": settings.GOOGLE_CLIENT_SECRET or "",
})
oauth = OAuth(starlette_config)
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    Args:
        user_data: User registration data including email, password, and username.
        db: Database session dependency.
        
    Returns:
        UserResponse: Created user data (excluding password).
        
    Raises:
        HTTPException: If email already exists.
    """
    # Check if user already exists
    existing_user = User.get_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.
    
    Args:
        form_data: OAuth2 password request form containing username and password.
        db: Database session dependency.
        
    Returns:
        Token: Access token and token type.
        
    Raises:
        HTTPException: If credentials are invalid.
    """
    user = User.get_by_email(db, form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get current authenticated user's information.
    
    Args:
        current_user: Current authenticated user from JWT token.
        
    Returns:
        UserResponse: Current user's data.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Update current user's profile information.
    
    Args:
        user_update: Fields to update.
        current_user: Current authenticated user.
        db: Database session dependency.
        
    Returns:
        UserResponse: Updated user data.
    """
    update_data = user_update.model_dump(exclude_unset=True)
    
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.get("/wallet")
async def get_wallet(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Return current wallet balance and a mock pricing reference."""
    pricing = [
        {"action": "Full Campaign Pipeline", "cost_cents": 100, "label": "$1.00"},
        {"action": "Generate Blog Post",      "cost_cents": 10,  "label": "$0.10"},
        {"action": "Generate Reel (6s Sora)", "cost_cents": 50,  "label": "$0.50"},
        {"action": "AI Chatbot",              "cost_cents": 0,   "label": "Free"},
    ]
    return {
        "balance_cents": current_user.wallet_balance,
        "balance_display": f"${current_user.wallet_balance / 100:.2f}",
        "pricing": pricing,
    }


@router.post("/logout")
async def logout(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Logout current user (token invalidation handled client-side).
    
    In a production system, you might want to implement token blacklisting
    using Redis for server-side token invalidation.
    
    Returns:
        dict: Logout confirmation message.
    """
    # Note: For production, implement token blacklisting with Redis
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Refresh the access token for authenticated user.
    
    Args:
        current_user: Current authenticated user.
        
    Returns:
        Token: New access token.
    """
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(current_user.id), "email": current_user.email},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/google/login")
async def google_login(request: Request, mode: str = "login"):
    """Initiates the Google OAuth2 login flow. Mode can be 'login' or 'register'."""
    request.session["google_auth_mode"] = mode
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    if not redirect_uri:
        raise HTTPException(status_code=500, detail="Google OAuth not configured (missing redirect URI)")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handles the callback from Google, creates/logs in the user based on mode, and returns a JWT token."""
    mode = request.session.get("google_auth_mode", "login")
    frontend_url = "http://localhost:5173"
    
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=f"{frontend_url}/login?error=OAuthFailed")
        
    user_info = token.get("userinfo")
    if not user_info or not user_info.get("email"):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=f"{frontend_url}/login?error=NoEmailProvided")

    email = user_info["email"]
    name = user_info.get("name", "")
    avatar = user_info.get("picture", "")

    # Check if user already exists (by email)
    user = User.get_by_email(db, email)
    
    if not user:
        if mode == "login":
            # Trying to login but account doesn't exist
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=f"{frontend_url}/login?error=AccountNotFound")
        
        # Create a new user account linked to Google
        dummy_password = secrets.token_urlsafe(32)  # They will never use this
        user_data = UserCreate(
            email=email,
            password=dummy_password,
            username=name,
            full_name=name
        )
        user = User(
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            username=user_data.username,
            full_name=user_data.full_name,
            avatar_url=avatar,
            is_active=True,
            is_verified=True,  # Google verified the email
            wallet_balance=500  # Default $5.00 credits
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Issue our JWT access token exactly like the normal login flow
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires
    )
    
    # Redirect to frontend with the token as a query parameter
    # The frontend will read the token from the URL and store it in localStorage
    frontend_url = "http://localhost:5173"
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"{frontend_url}/login?token={access_token}")


@router.get("/instagram/login-url")
async def instagram_login_url(
    db: Session = Depends(get_db),
):
    state = secrets.token_urlsafe(24)
    service = InstagramOAuthService(db)
    return {"login_url": service.get_login_url(state), "state": state}


@router.get("/instagram/callback")
async def instagram_callback(
    code: str = Query(...),
    state: str = Query(default=""),
    db: Session = Depends(get_db),
):
    service = InstagramOAuthService(db)
    data = await service.exchange_code_for_token(code)
    ig = await service.get_instagram_business_account(data.get("access_token", ""))
    return {
        "success": bool(ig),
        "state": state,
        "instagram": ig,
        "message": "Instagram/Facebook auth callback received",
    }
