"""Rule-based query classifier for routing to internal (RAG), external (web), or both."""

from __future__ import annotations

import re


_INTERNAL_KEYWORDS = {
    "our", "we", "internal", "company",
    # Russian equivalents
    "наш", "наша", "наше", "наши", "нашу", "нашим", "нашей", "нашего",
    "мы", "внутренний", "внутренняя", "внутреннее", "внутренние",
    "компания", "компании",
}

_EXTERNAL_KEYWORDS = {
    "react", "python", "docker", "kubernetes", "k8s", "redis",
    "postgresql", "postgres", "mongodb", "nginx", "kafka",
    "fastapi", "django", "flask", "express", "nextjs", "next.js",
    "typescript", "javascript", "rust", "golang", "java",
    "aws", "gcp", "azure", "terraform", "ansible",
    "git", "github", "gitlab",
}

_EXTERNAL_PHRASES = [
    "how to", "best practice", "best practices", "tutorial",
    "documentation", "docs",
]

_FILE_PATH_RE = re.compile(
    r"[\w\-]+/[\w\-]+(?:/[\w\-]+)*\.\w+",
)

_CODE_PATTERN_RE = re.compile(
    r"\b(?:def |class |import |from )\w+",
)

_URL_RE = re.compile(
    r"\b[\w\-]+\.(?:com|org|io|dev|net|ru)\b",
)


class QueryRouter:
    """Classify search queries as internal, external, or both."""

    def classify(self, query: str, org_terms: list[str] | None = None) -> str:
        """Classify a query into 'internal', 'external', or 'both'.

        Args:
            query: The search query text.
            org_terms: Organization-specific terms (concept names, project names).

        Returns:
            'internal', 'external', or 'both'.
        """
        if org_terms is None:
            org_terms = []

        query_lower = query.lower()
        words = set(re.findall(r"\w+", query_lower))

        internal_score = self._score_internal(query_lower, words, org_terms)
        external_score = self._score_external(query_lower, words)

        if internal_score > 0 and external_score == 0:
            return "internal"
        if external_score > 0 and internal_score == 0:
            return "external"
        return "both"

    @staticmethod
    def _score_internal(
        query_lower: str, words: set[str], org_terms: list[str],
    ) -> int:
        score = 0

        for term in org_terms:
            if term.lower() in query_lower:
                score += 1

        if words & _INTERNAL_KEYWORDS:
            score += 1

        if _FILE_PATH_RE.search(query_lower):
            score += 1

        if _CODE_PATTERN_RE.search(query_lower):
            score += 1

        return score

    @staticmethod
    def _score_external(query_lower: str, words: set[str]) -> int:
        score = 0

        if words & _EXTERNAL_KEYWORDS:
            score += 1

        for phrase in _EXTERNAL_PHRASES:
            if phrase in query_lower:
                score += 1
                break

        if _URL_RE.search(query_lower):
            score += 1

        return score
