"""Tests for QueryRouter — rule-based query classification."""

import pytest

from app.services.query_router import QueryRouter


class TestClassifyInternalOnly:
    """Queries that should route to 'internal' only."""

    def test_org_specific_term(self):
        router = QueryRouter()
        result = router.classify("how does PaymentEngine work", org_terms=["PaymentEngine"])
        assert result == "internal"

    def test_multiple_org_terms(self):
        router = QueryRouter()
        result = router.classify(
            "difference between AuthService and UserStore",
            org_terms=["AuthService", "UserStore"],
        )
        assert result == "internal"

    def test_our_keyword(self):
        router = QueryRouter()
        result = router.classify("how does our API handle errors")
        assert result == "internal"

    def test_we_keyword(self):
        router = QueryRouter()
        result = router.classify("what conventions do we follow")
        assert result == "internal"

    def test_internal_keyword(self):
        router = QueryRouter()
        result = router.classify("internal deployment process")
        assert result == "internal"

    def test_company_keyword(self):
        router = QueryRouter()
        result = router.classify("company coding standards")
        assert result == "internal"

    def test_file_path_pattern(self):
        router = QueryRouter()
        result = router.classify("what does services/py/ai/app/main.py do")
        assert result == "internal"

    def test_code_pattern_function_def(self):
        router = QueryRouter()
        result = router.classify("where is def create_user defined")
        assert result == "internal"

    def test_code_pattern_class(self):
        router = QueryRouter()
        result = router.classify("find class UserRepository")
        assert result == "internal"

    def test_russian_our(self):
        router = QueryRouter()
        result = router.classify("как работает наш API")
        assert result == "internal"

    def test_russian_internal(self):
        router = QueryRouter()
        result = router.classify("внутренний процесс деплоя")
        assert result == "internal"

    def test_russian_company(self):
        router = QueryRouter()
        result = router.classify("стандарты компании по код ревью")
        assert result == "internal"


class TestClassifyExternalOnly:
    """Queries that should route to 'external' only."""

    def test_library_name_react(self):
        router = QueryRouter()
        result = router.classify("react useEffect cleanup pattern")
        assert result == "external"

    def test_library_name_python(self):
        router = QueryRouter()
        result = router.classify("python asyncio gather vs wait")
        assert result == "external"

    def test_library_name_docker(self):
        router = QueryRouter()
        result = router.classify("docker multi-stage build optimization")
        assert result == "external"

    def test_library_name_kubernetes(self):
        router = QueryRouter()
        result = router.classify("kubernetes pod autoscaling")
        assert result == "external"

    def test_how_to_pattern(self):
        router = QueryRouter()
        result = router.classify("how to implement retry logic")
        assert result == "external"

    def test_best_practice_pattern(self):
        router = QueryRouter()
        result = router.classify("best practices for error handling")
        assert result == "external"

    def test_tutorial_pattern(self):
        router = QueryRouter()
        result = router.classify("tutorial on fastapi dependency injection")
        assert result == "external"

    def test_documentation_pattern(self):
        router = QueryRouter()
        result = router.classify("documentation for pydantic v2 validators")
        assert result == "external"

    def test_url_pattern(self):
        router = QueryRouter()
        result = router.classify("what does docs.python.org say about generators")
        assert result == "external"

    def test_framework_fastapi(self):
        router = QueryRouter()
        result = router.classify("fastapi middleware order of execution")
        assert result == "external"

    def test_framework_nextjs(self):
        router = QueryRouter()
        result = router.classify("nextjs app router server components")
        assert result == "external"


class TestClassifyBoth:
    """Queries with mixed or no signals should route to 'both'."""

    def test_mixed_internal_and_external(self):
        router = QueryRouter()
        result = router.classify(
            "how we use react in our frontend",
            org_terms=[],
        )
        assert result == "both"

    def test_no_signals_at_all(self):
        router = QueryRouter()
        result = router.classify("explain event sourcing")
        assert result == "both"

    def test_org_term_with_library(self):
        router = QueryRouter()
        result = router.classify(
            "how does PaymentEngine use redis",
            org_terms=["PaymentEngine"],
        )
        assert result == "both"

    def test_internal_keyword_with_how_to(self):
        router = QueryRouter()
        result = router.classify("how to deploy our services")
        assert result == "both"


class TestClassifyEdgeCases:
    """Edge cases for classification."""

    def test_empty_query(self):
        router = QueryRouter()
        result = router.classify("")
        assert result == "both"

    def test_case_insensitive_keywords(self):
        router = QueryRouter()
        result = router.classify("OUR internal API")
        assert result == "internal"

    def test_case_insensitive_org_terms(self):
        router = QueryRouter()
        result = router.classify("paymentengine config", org_terms=["PaymentEngine"])
        assert result == "internal"

    def test_empty_org_terms(self):
        router = QueryRouter()
        result = router.classify("our API", org_terms=[])
        assert result == "internal"

    def test_org_terms_default_empty(self):
        router = QueryRouter()
        result = router.classify("our API")
        assert result == "internal"
