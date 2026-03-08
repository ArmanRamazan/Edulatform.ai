from dataclasses import dataclass


@dataclass(frozen=True)
class MasteryUpdated:
    """Published to NATS when a user's concept mastery level changes.

    Subject: platform.mastery.updated
    Stream: PLATFORM_EVENTS
    """

    user_id: str
    organization_id: str
    concept_id: str
    new_level: float
    timestamp: str  # ISO-8601 UTC
