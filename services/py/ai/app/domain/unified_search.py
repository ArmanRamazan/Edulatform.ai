"""Domain models for unified search."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class InternalSearchResult:
    title: str
    source_path: str
    content: str


@dataclass(frozen=True)
class ExternalSearchResult:
    title: str
    url: str
    snippet: str


@dataclass(frozen=True)
class UnifiedSearchResult:
    route: str  # "internal" | "external" | "both"
    internal_results: list[InternalSearchResult] = field(default_factory=list)
    external_results: list[ExternalSearchResult] = field(default_factory=list)
