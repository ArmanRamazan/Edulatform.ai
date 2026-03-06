## Sprint-30 Impact Report — AI Coaching Stream

**Delivered:** 2 tasks, 0 failures | Scope: `ai` service

---

### What Was Delivered

Sprint-30 shipped two foundational pieces of the AI coaching layer:

- **MockLLMProvider** — a deterministic fallback LLM provider for the `ai` service, activated when `GEMINI_API_KEY` is absent. Returns hardcoded demo responses (Python closures, Rust ownership examples) so the service boots and responds in local/test environments without a live API key.
- **SSE Coach Streaming** — a Server-Sent Events endpoint that streams coach responses token-by-token to the client, enabling real-time coaching UX without long-polling or full response buffering.

Together these unblock frontend development of the mission coaching session UI and allow QA to test streaming behavior without Gemini quota dependency.

---

### Metrics Potentially Affected

| Metric | Direction | Reason |
|---|---|---|
| AI service uptime / error rate | ↑ positive | Mock fallback prevents cold-start crashes in staging |
| Coach session completion rate | ↑ positive | Streaming reduces perceived latency, improves UX |
| Credit burn rate (coach credits) | ⚠ untracked | Credit check missing in stream handler (H1) — charges may not be deducted |
| Session ownership violations | ⚠ untracked | User ID not stored at session creation (H2) — cross-user session access undetected |

---

### Monitoring Recommendations

1. **Alert on mock mode activation** — until `ALLOW_MOCK_LLM` opt-in flag is added, emit a `WARNING`-level log (not `INFO`) on MockLLMProvider init. Set a Prometheus counter `ai_mock_llm_active_total` and alert if it increments in production.
2. **Track SSE stream errors** — instrument stream abandonment (client disconnect mid-stream) and generator exceptions as separate error counters.
3. **Credit deduction audit** — query `payment.user_subscriptions` + `learning.xp_points` to confirm credit consumption correlates with coach session events. A mismatch signals H1 is actively losing revenue.
4. **Session ownership anomalies** — log and alert on any stream request where resolved `user_id` ≠ `session_data.user_id` once H2 is fixed; this serves as an integrity canary.

---

### Known Risks & Required Follow-ups

> **Code review verdict: FAIL — do not merge to `main` until resolved.**

| Priority | Item | Risk if unresolved |
|---|---|---|
| 🔴 H1 | Add `credit_service.check_and_consume()` to stream handler | Coach responses delivered without consuming credits — revenue leak |
| 🔴 H2 | Store and verify `user_id` in session at creation + stream + end | Any authenticated user can stream another user's coaching session |
| 🟡 M1 | Pre-check session existence before returning `StreamingResponse` | 404 errors surface mid-stream instead of synchronously — broken UX |
| 🟡 M2 | Convert `/stream` to `POST` or move message to request body | Message content exposed in server access logs and browser history |
| 🟡 M3 | Require explicit `ALLOW_MOCK_LLM=true` env flag; upgrade log to `WARNING` | Misconfigured production deploy silently serves demo responses with no operator alert |
