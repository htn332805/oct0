"""
Authentication Utilities for AI Study System

Provides password hashing, JWT token management, and authentication helpers.
"""

import os
import hashlib
import hmac
import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class UserCredentials:
    """User authentication credentials."""
    user_id: int
    username: str
    email: str
    full_name: Optional[str] = None


class AuthUtils:
    """Authentication utilities for user management."""

    # JWT configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))
    JWT_ALGORITHM = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """
        Hash a password using PBKDF2 with SHA-256.

        Args:
            password: Plain text password
            salt: Optional salt, generated if not provided

        Returns:
            Tuple of (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)

        # Use PBKDF2 with SHA-256, 100,000 iterations
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )

        return hashed.hex(), salt

    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password to verify
            hashed_password: Stored password hash
            salt: Salt used for hashing

        Returns:
            True if password matches, False otherwise
        """
        computed_hash, _ = AuthUtils.hash_password(password, salt)
        return hmac.compare_digest(computed_hash, hashed_password)

    @classmethod
    def create_access_token(cls, user_credentials: UserCredentials) -> str:
        """
        Create a JWT access token for a user.

        Args:
            user_credentials: User credentials to encode in token

        Returns:
            JWT token string
        """
        expire = datetime.utcnow() + timedelta(minutes=cls.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode = {
            "sub": str(user_credentials.user_id),
            "username": user_credentials.username,
            "email": user_credentials.email,
            "full_name": user_credentials.full_name,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }

        encoded_jwt = jwt.encode(to_encode, cls.JWT_SECRET_KEY, algorithm=cls.JWT_ALGORITHM)
        return encoded_jwt

    @classmethod
    def verify_access_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT access token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, cls.JWT_SECRET_KEY, algorithms=[cls.JWT_ALGORITHM])

            # Check token type
            if payload.get("type") != "access":
                return None

            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                return None

            return payload

        except jwt.PyJWTError:
            return None

    @classmethod
    def create_session_token(cls) -> str:
        """
        Create a secure session token.

        Returns:
            Random session token string
        """
        return secrets.token_urlsafe(32)

    @classmethod
    def get_token_expiration(cls) -> datetime:
        """
        Get the default token expiration time.

        Returns:
            Datetime when tokens should expire
        """
        return datetime.utcnow() + timedelta(minutes=cls.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)


class AuthMiddleware:
    """Authentication middleware for protecting endpoints."""

    @staticmethod
    def get_current_user(token: str) -> Optional[UserCredentials]:
        """
        Extract user credentials from JWT token.

        Args:
            token: JWT access token

        Returns:
            UserCredentials if token is valid, None otherwise
        """
        payload = AuthUtils.verify_access_token(token)
        if not payload:
            return None

        return UserCredentials(
            user_id=int(payload["sub"]),
            username=payload["username"],
            email=payload["email"],
            full_name=payload.get("full_name")
        )

    @staticmethod
    def require_auth(token: str) -> UserCredentials:
        """
        Require authentication and return user credentials.

        Args:
            token: JWT access token

        Returns:
            UserCredentials for authenticated user

        Raises:
            ValueError: If authentication fails
        """
        user = AuthMiddleware.get_current_user(token)
        if not user:
            raise ValueError("Invalid or expired authentication token")
        return user