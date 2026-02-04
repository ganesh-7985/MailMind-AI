from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import json
import logging

from .config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()

# In-memory token storage (in production, use Redis or database)
user_credentials_store = {}

def create_oauth_flow() -> Flow:
    """Create Google OAuth flow with Gmail permissions."""
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri]
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=settings.gmail_scopes,
        redirect_uri=settings.google_redirect_uri
    )
    return flow

def create_jwt_token(user_email: str, user_name: str, picture: str = None) -> str:
    """Create JWT token for authenticated user."""
    expiration = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
    payload = {
        "sub": user_email,
        "name": user_name,
        "picture": picture,
        "exp": expiration,
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token

def verify_jwt_token(token: str) -> dict:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    payload = verify_jwt_token(token)
    
    user_email = payload.get("sub")
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Check if we have valid Google credentials stored
    if user_email not in user_credentials_store:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again."
        )
    
    return {
        "email": user_email,
        "name": payload.get("name", ""),
        "picture": payload.get("picture", "")
    }

def store_user_credentials(email: str, credentials: Credentials):
    """Store Google credentials for a user."""
    user_credentials_store[email] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes) if credentials.scopes else []
    }
    logger.info(f"Stored credentials for user: {email}")

def get_user_credentials(email: str) -> Optional[Credentials]:
    """Retrieve stored Google credentials for a user."""
    cred_data = user_credentials_store.get(email)
    if not cred_data:
        return None
    
    credentials = Credentials(
        token=cred_data["token"],
        refresh_token=cred_data.get("refresh_token"),
        token_uri=cred_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=cred_data.get("client_id", settings.google_client_id),
        client_secret=cred_data.get("client_secret", settings.google_client_secret),
        scopes=cred_data.get("scopes", settings.gmail_scopes)
    )
    return credentials

def remove_user_credentials(email: str):
    """Remove stored credentials for a user."""
    if email in user_credentials_store:
        del user_credentials_store[email]
        logger.info(f"Removed credentials for user: {email}")

def get_user_info(credentials: Credentials) -> dict:
    """Get user info from Google."""
    try:
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        return {
            "email": user_info.get("email", ""),
            "name": user_info.get("name", ""),
            "picture": user_info.get("picture", "")
        }
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information from Google"
        )
