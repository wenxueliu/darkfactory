# Worked Example: AI Night Shift v1→v2→v3 Convergence

**Date**: 2026-06-19
**Topic**: How to clean up AI-generated tech debt at night (autonomous agent pipeline)
**Outcome**: 3-AI pipeline produced v1 (2 weeks) → v2 (4 weeks) → v3 (5 weeks, with Gemini-specific blind spots)

**Note**: This example was originally produced under the legacy **3-stage hierarchical** workflow (ChatGPT proposer → DeepSeek critic → Gemini arbiter). It is kept here as a *historical record* of how the same convergence outcome would unfold under peer-PK with the agent as scheduler — but the *exact* round sequence shown below is not how `peer_debate.py` would drive it today. In peer-PK the agent could decide to ask Gemini first as a fresh-eyes reviewer of an existing proposal, or run a parallel second round of clarifications, etc. The *insights* (table at the bottom) are unchanged.

---

## Stage 1: ChatGPT (proposer) — 7 rounds

**Q1**: Design a 5-layer DAG for "AI Night Shift"
**Q2**: What's ADI (AI Debt Index)?
**Q3**: 24×7 double loop, 90-day roadmap?
**Q4**: MVP scope for 2 weeks?
**Q5**: Refactor Agent design?
**Q6**: ADI v0.1?
**Q7**: Risk and circuit breakers?

**Output**: 18KB markdown plan, 5-layer architecture, Refactor-P0, 2 weeks.

**Key positions**:
- Refactor Agent as P0 (demo-pretty, applies to all repos)
- 5-layer DAG: L1 Collection → L2 Analysis → L3 Governance → L4 Evolution → L5 Feedback
- 2 weeks hard timeline
- 90-day phased rollout

---

## Stage 2: DeepSeek (critic) — 2 rounds, brutal

**Round 1 — "打脸" (Slap in the face)**: 5 cuts to v1

1. **5-layer is "emperor's new clothes"** — L3/L4/L5 are empty, 2.5 layers in practice
2. **LLM not a regex engine** — "no business logic change" is psychology placebo
3. **Missing prompt version binding** — no prompt_hash, no audit
4. **No grad/rollback strategy** — once merged, no revert
5. **Cross-file dependency is broken** — rename utils.helper() in one file, callers in other files not updated

**Round 2 — v2 4-decision arbitration**:

1. **P0 reversal**: Refactor → UT (UT is LLM-friendly, "if Refactor breaks, UT goes red")
2. **Architecture cut 2 layers**: 5 → 3 layer linear
3. **Timeline doubled**: 2 weeks → 4 weeks
4. **3 Hard Requirements added** (must-have):
   - Coverage gate (≥2pp file-level increase)
   - Audit (prompt_hash + llm_request_id + temperature)
   - AST pre-check (single-file only)

**Output**: v2 plan with 3-layer + UT-P0 + 4 weeks.

---

## Stage 3: Gemini (arbiter) — 1 round, blind to prior

**Question to Gemini**: "Review this v2 plan independently. What did ChatGPT and DeepSeek both miss?"

**Gemini's response** (without seeing v2's text, only the topic):

**Highest-risk blind spot** (3rd-party unique finding):
> "Test Pollution Nightmare — running untrusted LLM-generated tests in your production environment is a ticking bomb. When the UT Agent writes tests to hit +2pp coverage, it'll mock or invoke dependencies. If the target repo talks to real databases / cloud APIs / local filesystems, the LLM-generated tests can: trigger real API calls that DELETE data, pollute a shared staging DB, or execute malicious commands. Because v2's tech stack is FastAPI + pytest on a standard VM, there's no containerized isolation."

**3 structural changes** Gemini demanded:

1. **AST regex → native ast module** — Gemini noted: "AST validation CANNOT use regex. Python's ast module is native. Relying on regex to catch signature changes will leak breaking changes into the MR."

2. **FastAPI direct execution → async task queue** (Huey/Celery) — "GitLab times out webhooks after 10 seconds. If 3 concurrent pushes, your FastAPI worker blocks."

3. **Bare pytest → Docker-in-Docker ephemeral containers** — "Every L2 execution MUST run in an isolated, short-lived container. The container clones a fresh repo, runs pytest inside the sandbox. 12-minute hard timeout."

**Output**: v3 plan with 5 weeks + 3 structural changes from Gemini.

---

## What 3-AI consultation actually delivered

| Insight | First surfaced by | Why others missed it |
|---|---|---|
| 5-layer architecture | ChatGPT | architecturally ambitious, looks good on paper |
| Architecture is over-engineered for 2 weeks | DeepSeek | ChatGPT was the proposer, didn't critique self |
| P0 should be UT, not Refactor | DeepSeek | Strategic reversal — needs external POV |
| AST regex is a contradiction | Gemini | Both prior AIs used "regex AST" hand-wavily |
| Test Pollution is a security issue | Gemini | Both prior AIs only saw "test coverage", not "test execution risk" |
| Async queue is needed | Gemini | Both prior AIs assumed FastAPI handles it |
| Container isolation mandatory | Gemini | Both prior AIs assumed "test runs in CI" is enough |

**Without Gemini, v2 would have shipped with: regex AST, sync FastAPI, bare pytest. The "Test Pollution" would have bitten during the first real production push.**

---

## Time investment

- ChatGPT 7 rounds: ~20 minutes (lots of empty responses from rate limits)
- DeepSeek 2 rounds: ~3 minutes (much faster)
- Gemini 1 round: ~2 minutes
- Total orchestration: ~25 minutes
- Converged plan quality: dramatically better than any single AI would have produced

---

## Files produced

```
_context-output/
├── PLAN-20260619-001/
│   ├── night-shift-mvp-plan.md             (v1, ChatGPT)
│   └── raw-answers/q1-q7_answer.txt         (ChatGPT 7 rounds)
├── PLAN-20260619-002/
│   ├── night-shift-v2-converged-plan.md    (v2, DeepSeek)
│   └── raw-answers/
│       ├── deepseek_review.txt             (DeepSeek round 1)
│       ├── deepseek_round2.txt             (DeepSeek round 2)
│       └── gemini_review.txt               (Gemini response)
└── PLAN-20260619-003/
    └── night-shift-v3-converged-plan.md    (v3, Gemini feedback)
```

This is the canonical validation that 3-AI consultation adds real value.
