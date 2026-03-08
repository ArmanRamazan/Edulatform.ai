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


@dataclass(frozen=True)
class MissionCompleted:
    """Published to NATS when a user completes a mission.

    Subject: platform.mission.completed
    Stream: PLATFORM_EVENTS
    """

    event_id: str
    user_id: str
    organization_id: str
    mission_id: str
    score: float
    timestamp: str  # ISO-8601 UTC


@dataclass(frozen=True)
class BadgeEarned:
    """Published to NATS when a user earns a badge.

    Subject: platform.badge.earned
    Stream: PLATFORM_EVENTS
    """

    event_id: str
    user_id: str
    badge_type: str
    timestamp: str  # ISO-8601 UTC


@dataclass(frozen=True)
class StreakMilestone:
    """Published to NATS when a user hits a streak milestone.

    Subject: platform.streak.milestone
    Stream: PLATFORM_EVENTS
    """

    event_id: str
    user_id: str
    streak: int
    timestamp: str  # ISO-8601 UTC
