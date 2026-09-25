"""
Authentication & Authorization Module for Jett 2 Holiday (APS-02).
Implements:
1. Pure bcrypt password hashing and verification.
2. Signed JWT session tokens with role claims ('admin' | 'traveller').
3. FastAPI security dependencies for role gating (require_admin, require_traveller).
"""

import os
import datetime
import uuid
import re
import sqlite3
import bcrypt
import jwt
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field

# Load environment variables
load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jett2holiday_jwt_super_secret_key_aps02_hackathon_2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_HOURS", "8"))

# Hardcoded hackathon admin credentials (server-side only, never exposed or stored in DB)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin@123"

# Bearer security scheme
security_bearer = HTTPBearer(auto_error=False)


# ==========================================
# Pydantic Schemas for Auth
# ==========================================
class AdminLoginRequest(BaseModel):
    username: str = Field(..., examples=["admin"], description="Admin username")
    password: str = Field(..., examples=["admin@123"], description="Admin password")


class TravellerSignupRequest(BaseModel):
    email: str = Field(..., examples=["traveler@example.com"], description="Traveller email address")
    password: str = Field(..., min_length=6, examples=["secret123"], description="Password (min 6 characters)")
    display_name: str = Field(..., min_length=2, examples=["Rohan Sharma"], description="Traveller display name")


class TravellerLoginRequest(BaseModel):
    email: str = Field(..., examples=["traveler@example.com"], description="Traveller email address")
    password: str = Field(..., examples=["secret123"], description="Password")


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[str] = None


# ==========================================
# Password Hashing with Bcrypt
# ==========================================
def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using pure bcrypt.
    """
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against a bcrypt hash.
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# ==========================================
# JWT Token Generation & Verification
# ==========================================
def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """
    Creates a signed JWT with expiration and role claims.
    """
    to_encode = data.copy()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    expire = now_utc + (expires_delta or datetime.timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({
        "exp": expire,
        "iat": now_utc
    })
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decodes and validates a JWT token.
    Raises 401 if invalid or expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ==========================================
# FastAPI Role-Based Route Guards
# ==========================================
def get_current_token_payload(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> dict:
    """
    Extracts Bearer token from header and validates JWT signature and expiry.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(credentials.credentials)


def require_admin(payload: dict = Depends(get_current_token_payload)) -> dict:
    """
    Route guard: requires a valid JWT with role == 'admin'.
    Returns 401 if no/invalid token, 403 if valid token but wrong role.
    """
    role = payload.get("role")
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin privileges required to access this resource."
        )
    return payload


def require_traveller(payload: dict = Depends(get_current_token_payload)) -> dict:
    """
    Route guard: requires a valid JWT with role == 'traveller'.
    Returns 401 if no/invalid token, 403 if valid token but wrong role.
    """
    role = payload.get("role")
    if role != "traveller":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Traveller authentication required to access this resource."
        )
    return payload


def validate_email_format(email: str) -> bool:
    """Simple regex email validator."""
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.match(pattern, email.strip()))
