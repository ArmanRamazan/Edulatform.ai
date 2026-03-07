# ADR-004: B2C to B2B Platform Pivot

**Status:** Accepted
**Date:** 2026-02-15
**Decision makers:** Product team

## Context
Original product was B2C online courses (Udemy/Coursera clone). Market is saturated. AI-powered knowledge management for engineering teams has higher value and differentiation.

## Decision
Pivot to B2B knowledge platform — "KnowledgeOS":
- **Target:** Companies onboarding engineers
- **Users:** Tech Lead (manages KB, views team progress), Engineer (learns via missions), AI Agent (via MCP)
- **Core value:** AI-powered knowledge graph + spaced repetition + coaching

Key changes:
- Organizations (multi-tenant) added to identity service
- Knowledge graph (concepts) in learning service
- RAG pipeline for company documentation
- B2B billing (org subscriptions) in payment service
- Dark Knowledge UI theme for buyer app

## Consequences
**Positive:**
- Higher revenue per customer (B2B vs B2C)
- Stronger differentiation (AI + knowledge graph)
- Existing 8 services reusable with extensions
- MCP server enables AI agent integration

**Negative:**
- B2C features (reviews, bundles, seller app) partially deprecated
- Multi-tenancy adds complexity to every service
- Longer sales cycles vs B2C self-serve

## Alternatives considered
1. **Stay B2C** — compete with Udemy/Coursera on price (losing proposition)
2. **B2B LMS** — commodity market, no differentiation
3. **Developer tools SaaS** — narrower market but more technical
