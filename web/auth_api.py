"""
Authentication API Endpoints for AI Study System

Provides REST API endpoints for user registration, login, logout, and session management.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import json

from kb.auth_utils import AuthUtils, AuthMiddleware, UserCredentials
from kb.metadata_db import MetadataDB

# Initialize router and security
router = APIRouter(prefix="/api/auth", tags=["authentication"])
security = HTTPBearer()

# Pydantic models for request/response
class UserRegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: Optional[str] = None

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class MessageResponse(BaseModel):
    message: str


@router.post("/register", response_model=AuthResponse)
async def register_user(request: UserRegisterRequest):
    """
    Register a new user account.

    Creates a new user with the provided credentials and returns an access token.
    """
    try:
        # Initialize database
        db = MetadataDB()

        # Check if user already exists
        existing_user = db.get_user_by_username(request.username)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Username already registered"
            )

        # Check if email already exists
        existing_email = db.get_user_by_email(request.email)
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        # Create new user
        user_id = db.create_user(
            username=request.username,
            email=request.email,
            password=request.password,
            full_name=request.full_name
        )

        # Get created user data
        user_data = db.get_user_by_id(user_id)
        if not user_data:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve created user"
            )

        # Create user credentials object
        user_credentials = UserCredentials(
            user_id=user_data['user_id'],
            username=user_data['username'],
            email=user_data['email'],
            full_name=user_data.get('full_name')
        )

        # Create access token
        access_token = AuthUtils.create_access_token(user_credentials)

        # Create session
        session_token = AuthUtils.create_session_token()
        db.create_session(user_id, session_token, access_token)

        return AuthResponse(
            access_token=access_token,
            user=UserResponse(
                user_id=user_data['user_id'],
                username=user_data['username'],
                email=user_data['email'],
                full_name=user_data.get('full_name')
            )
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login", response_model=AuthResponse)
async def login_user(request: UserLoginRequest):
    """
    Authenticate a user and return an access token.

    Validates credentials and returns a new access token for authenticated sessions.
    """
    try:
        # Initialize database
        db = MetadataDB()

        # Get user by username
        user_data = db.get_user_by_username(request.username)
        if not user_data:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )

        # Verify password
        if not AuthUtils.verify_password(
            request.password,
            user_data['password_hash'],
            user_data['salt']
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )

        # Create user credentials object
        user_credentials = UserCredentials(
            user_id=user_data['user_id'],
            username=user_data['username'],
            email=user_data['email'],
            full_name=user_data.get('full_name')
        )

        # Create access token
        access_token = AuthUtils.create_access_token(user_credentials)

        # Create session
        session_token = AuthUtils.create_session_token()
        db.create_session(user_data['user_id'], session_token, access_token)

        return AuthResponse(
            access_token=access_token,
            user=UserResponse(
                user_id=user_data['user_id'],
                username=user_data['username'],
                email=user_data['email'],
                full_name=user_data.get('full_name')
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/logout", response_model=MessageResponse)
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Logout a user by invalidating their session.

    Requires valid access token in Authorization header.
    """
    try:
        # Verify token and get user
        user = AuthMiddleware.require_auth(credentials.credentials)

        # Initialize database
        db = MetadataDB()

        # Invalidate session
        db.invalidate_session(user.user_id, credentials.credentials)

        return MessageResponse(message="Successfully logged out")

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get current authenticated user's profile information.

    Requires valid access token in Authorization header.
    """
    try:
        # Verify token and get user
        user = AuthMiddleware.require_auth(credentials.credentials)

        # Initialize database
        db = MetadataDB()

        # Get fresh user data
        user_data = db.get_user_by_id(user.user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        return UserResponse(
            user_id=user_data['user_id'],
            username=user_data['username'],
            email=user_data['email'],
            full_name=user_data.get('full_name')
        )

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user profile: {str(e)}")


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    full_name: Optional[str] = None,
    email: Optional[EmailStr] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Update current user's profile information.

    Requires valid access token in Authorization header.
    Only full_name and email can be updated.
    """
    try:
        # Verify token and get user
        user = AuthMiddleware.require_auth(credentials.credentials)

        # Initialize database
        db = MetadataDB()

        # Update user profile
        db.update_user_profile(
            user_id=user.user_id,
            full_name=full_name,
            email=email
        )

        # Get updated user data
        user_data = db.get_user_by_id(user.user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        return UserResponse(
            user_id=user_data['user_id'],
            username=user_data['username'],
            email=user_data['email'],
            full_name=user_data.get('full_name')
        )

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")


# Dependency for getting authenticated user
async def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserCredentials:
    """
    FastAPI dependency for getting current authenticated user.

    Can be used in other routers that need user authentication.
    """
    return AuthMiddleware.require_auth(credentials.credentials)