from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    """Per-organization LLM configuration."""

    internal_provider: str = "gemini"  # "gemini" | "self_hosted"
    internal_model_url: str | None = None
    external_provider: str = "gemini"  # always "gemini" for now
    embedding_provider: str = "gemini"  # "gemini" | "self_hosted"
    data_isolation: str = "standard"  # "strict" | "standard"

    def to_dict(self) -> dict:
        return {
            "internal_provider": self.internal_provider,
            "internal_model_url": self.internal_model_url,
            "external_provider": self.external_provider,
            "embedding_provider": self.embedding_provider,
            "data_isolation": self.data_isolation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LLMConfig:
        return cls(
            internal_provider=data.get("internal_provider", "gemini"),
            internal_model_url=data.get("internal_model_url"),
            external_provider=data.get("external_provider", "gemini"),
            embedding_provider=data.get("embedding_provider", "gemini"),
            data_isolation=data.get("data_isolation", "standard"),
        )
