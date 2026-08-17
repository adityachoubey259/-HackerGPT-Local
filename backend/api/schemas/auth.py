"""Authentication API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class AuthUserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    is_bootstrap: bool


class AuthSessionResponse(BaseModel):
    authenticated: bool
    user: AuthUserResponse | None
