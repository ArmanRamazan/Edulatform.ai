from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserRole(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    password_hash: str
    name: str
    role: UserRole
    is_verified: bool
    created_at: datetime
    email_verified: bool = False
    referral_code: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: UserRole = UserRole.STUDENT


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class PendingTeacherResponse(BaseModel):
    id: UUID
    email: str
    name: str
    created_at: datetime


@dataclass(frozen=True)
class PublicProfile:
    id: UUID
    name: str
    bio: str | None
    avatar_url: str | None
    role: UserRole
    is_verified: bool
    created_at: datetime
    is_public: bool


class VisibilityUpdate(BaseModel):
    is_public: bool


class PublicProfileResponse(BaseModel):
    id: UUID
    name: str
    bio: str | None
    avatar_url: str | None
    role: UserRole
    is_verified: bool
    created_at: datetime
    is_public: bool


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    role: UserRole
    is_verified: bool
    email_verified: bool
    created_at: datetime
