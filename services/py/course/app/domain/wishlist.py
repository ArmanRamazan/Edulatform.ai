from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


@dataclass(frozen=True)
class WishlistItem:
    id: UUID
    user_id: UUID
    course_id: UUID
    course_title: str
    course_description: str
    created_at: datetime


class WishlistAddRequest(BaseModel):
    course_id: UUID


class WishlistItemResponse(BaseModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    course_title: str
    course_description: str
    created_at: datetime


class WishlistListResponse(BaseModel):
    items: list[WishlistItemResponse]
    total: int


class WishlistCheckResponse(BaseModel):
    in_wishlist: bool
