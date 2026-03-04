from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


@dataclass(frozen=True)
class Follow:
    id: UUID
    follower_id: UUID
    following_id: UUID
    created_at: datetime


@dataclass(frozen=True)
class FollowStats:
    followers_count: int
    following_count: int


class FollowResponse(BaseModel):
    id: UUID
    follower_id: UUID
    following_id: UUID
    created_at: datetime


class FollowStatsResponse(BaseModel):
    followers_count: int
    following_count: int


class PaginatedFollowsResponse(BaseModel):
    items: list[FollowResponse]
    total: int
