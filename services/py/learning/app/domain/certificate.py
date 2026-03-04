from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


@dataclass(frozen=True)
class Certificate:
    id: UUID
    user_id: UUID
    course_id: UUID
    issued_at: datetime
    certificate_number: str
    template_data: dict


class IssueCertificateRequest(BaseModel):
    course_id: UUID


class CertificateResponse(BaseModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    issued_at: datetime
    certificate_number: str


class CertificateListResponse(BaseModel):
    certificates: list[CertificateResponse]
    total: int
