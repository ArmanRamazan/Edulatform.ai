from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingResult:
    text: str
    vector: list[float]
    model: str
    token_count: int
