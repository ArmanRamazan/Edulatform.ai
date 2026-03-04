from __future__ import annotations

import random
import string
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


def generate_referral_code() -> str:
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=8))
    return f"REF-{suffix}"


@dataclass(frozen=True)
class Referral:
    id: UUID
    referrer_id: UUID
    referee_id: UUID
    referral_code: str
    status: str
    reward_type: str | None
    created_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True)
class ReferralStats:
    referral_code: str
    invited_count: int
    completed_count: int
    rewards_earned: int


class ApplyReferralRequest(BaseModel):
    referral_code: str


class CompleteReferralRequest(BaseModel):
    referee_id: UUID


class ReferralResponse(BaseModel):
    id: UUID
    referrer_id: UUID
    referee_id: UUID
    referral_code: str
    status: str
    reward_type: str | None
    created_at: datetime
    completed_at: datetime | None


class ReferralStatsResponse(BaseModel):
    referral_code: str
    invited_count: int
    completed_count: int
    rewards_earned: int
