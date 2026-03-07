# ADR-003: Python vs Rust Language Selection Criteria

**Status:** Accepted
**Date:** 2025-12-15
**Decision makers:** Core team

## Context
Platform needs both rapid development and high performance. Need clear criteria for when to use which language.

## Decision
**Rust** when: p99 latency < 50ms OR throughput > 10K RPS required.
**Python** for everything else.

Current allocation:
- **Python (8 services):** identity, course, enrollment, payment, notification, ai, learning, rag
- **Rust (2+ services):** api-gateway, search, embedding-orchestrator, video-processor

## Consequences
**Positive:**
- Business logic in Python = faster iteration, larger talent pool
- Performance-critical paths in Rust = predictable latency
- Clear decision boundary = no debates per service

**Negative:**
- Two ecosystems to maintain (cargo + uv)
- Cross-language FFI complexity (rag-chunker via pyo3)
- Smaller Rust talent pool for contributions

## Alternatives considered
1. **All Python** — simpler, but gateway/search would be too slow
2. **All Rust** — fastest, but 5x slower development velocity
3. **Go for performance paths** — good middle ground, but team has Rust expertise
