---
name: hw-systematic-debugging
description: 系统化调试技能。Use when encountering any bug, test failure, unexpected behavior, or performance issue — before proposing any fixes. 4-phase root cause investigation with iron law: no fixes without root cause first. [trigger: 调试, debugging, 报错, error, bug, test failure, 排查, 根因分析, root cause]
---

# 系统化调试 (hw-systematic-debugging)

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**The most important insight:** Build the right feedback loop, and the bug is 90% fixed. A fast, deterministic, agent-runnable pass/fail signal is the single most powerful debugging tool. Everything else (bisection, hypothesis-testing, instrumentation) just consumes that signal. Spend disproportionate effort on the feedback loop.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## The Feedback Loop (核心心法)

Before any phase, internalize this: **the feedback loop is the skill, everything else is mechanical.**

| Property | Weak Loop | Strong Loop |
|----------|-----------|-------------|
| Speed | 30+ seconds, manual steps | 2-5 seconds, fully automated |
| Signal | "Didn't crash" | Specific assertion on exact symptom |
| Determinism | Flaky, passes sometimes | Reliable, same result every run |
| Repeatability | Complex setup each time | One command, idempotent |

A 30-second flaky loop is barely better than no loop. A 2-second deterministic loop is a debugging superpower.

## When to Use

Use for ANY technical issue:
- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**
- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Human wants it fixed NOW (systematic is faster than thrashing)

## The Four Phases

You MUST complete each phase before proceeding to the next.

### Phase 1: Build Feedback Loop + Root Cause Investigation

**This phase has two parts. Start with Part A, then proceed to Part B.**

#### Part A: Build a Feedback Loop (FIRST — most important step)

**A fast, deterministic, agent-runnable pass/fail signal is the difference between guessing and debugging.** Spend disproportionate effort here. Be aggressive. Be creative. Refuse to give up.

**Ways to construct one — try in roughly this order:**

1. **Failing test** at whatever seam reaches the bug — unit, integration, e2e.
2. **Curl / HTTP script** against a running dev server with assertions on response.
3. **CLI invocation** with a fixture input, diffing stdout against a known-good snapshot.
4. **Headless browser script** — drives the UI, asserts on DOM/console/network.
5. **Replay a captured trace** — save a real network request / payload / event log to disk; replay it through the code path in isolation.
6. **Throwaway harness** — spin up a minimal subset of the system (one service, mocked deps) that exercises the bug code path with a single function call.
7. **Property / fuzz loop** — if the bug is "sometimes wrong output", run 1000 random inputs and look for the failure mode.
8. **Bisection harness** — if the bug appeared between two known states (commit, dataset, version), automate "boot at state X, check, repeat" so you can `git bisect run` it.
9. **Differential loop** — run the same input through old-version vs new-version (or two configs) and diff outputs.
10. **HITL script** — last resort. If a human must click, drive *them* with a structured script so the loop is still systematic. Captured output feeds back to you.

**Iterate on the loop itself.** Treat the loop as a product. Once you have *a* loop, ask:
- Can I make it faster? (Cache setup, skip unrelated init, narrow the test scope.)
- Can I make the signal sharper? (Assert on the specific symptom, not "didn't crash".)
- Can I make it more deterministic? (Pin time, seed RNG, isolate filesystem, freeze network.)

**Non-deterministic bugs:** The goal is not a clean repro but a **higher reproduction rate**. Loop the trigger 100×, parallelise, add stress, narrow timing windows, inject sleeps. A 50%-flake bug is debuggable; 1% is not — keep raising the rate until it's debuggable.

**When you genuinely cannot build a loop:** Stop and say so explicitly. List what you tried. Ask the user for: (a) access to the environment that reproduces it, (b) a captured artifact (HAR file, log dump, core dump, screen recording with timestamps), or (c) permission to add temporary production instrumentation. **Do not proceed to Part B until you have a loop you believe in.**

#### Part B: Root Cause Investigation (after feedback loop is built)

1. **Read Error Messages Carefully**
   - Don't skip past errors or warnings
   - They often contain the exact solution
   - Read stack traces completely
   - Note line numbers, file paths, error codes

2. **Reproduce Consistently** (using the feedback loop from Part A)
   - Run the loop. Watch the bug appear.
   - **Confirm:** The loop produces the failure mode the **user** described — not a different failure that happens to be nearby. Wrong bug = wrong fix.
   - Does it happen every time? Or at a known reproduction rate?
   - Capture the exact symptom (error message, wrong output, timing) so later phases can verify the fix.

3. **Check Recent Changes**
   - What changed that could cause this?
   - Git diff, recent commits, git log --oneline
   - New dependencies, config changes
   - Environmental differences (OS, Python version, env vars)

4. **Gather Evidence in Multi-Component Systems**

   **WHEN system has multiple components (Aggregator → Watchdog → Agent → stage-bridge → Consul KV):**

   **BEFORE proposing fixes, add diagnostic instrumentation:**
   ```
   For EACH component boundary:
     - Log what data enters component
     - Log what data exits component
     - Verify environment/config propagation
     - Check state at each layer

   Run once to gather evidence showing WHERE it breaks
   THEN analyze evidence to identify failing component
   THEN investigate that specific component
   ```

   **Example (Harness multi-component system):**
   ```bash
   # Layer 1: Consul KV state
   curl -s "http://127.0.0.1:8500/v1/kv/workflows/<req_id>/tasks/<task>/status?raw"
   echo "=== Task status in Consul ==="

   # Layer 2: Aggregator log
   tail -50 /tmp/harness-daemon.log | grep "req_id"

   # Layer 3: Watchdog state
   curl -s "http://127.0.0.1:8500/v1/health/service/<agent_name>"

   # Layer 4: Agent heartbeat
   python scripts/heartbeat.py --check
   ```

5. **Trace Data Flow**

   See `references/root-cause-tracing.md` for the complete backward tracing technique.

   **Quick version:**
   - Where does bad value originate?
   - What called this with bad value?
   - Keep tracing up until you find the source
   - Fix at source, not at symptom

### Phase 2: Pattern Analysis

**Find the pattern before fixing:**

1. **Find Working Examples**
   - Locate similar working code in same codebase
   - What works that's similar to what's broken?

2. **Compare Against References**
   - If implementing pattern, read reference implementation COMPLETELY
   - Don't skim - read every line
   - Understand the pattern fully before applying

3. **Identify Differences**
   - What's different between working and broken?
   - List every difference, however small
   - Don't assume "that can't matter"

4. **Understand Dependencies**
   - What other components does this need?
   - What settings, config, environment?
   - What assumptions does it make?

### Phase 3: Hypothesis and Testing

**Generate 3–5 ranked hypotheses before testing any of them.** Single-hypothesis generation anchors on the first plausible idea. Multiple hypotheses force broader reasoning.

Each hypothesis must be **falsifiable**: state the prediction it makes.

> Format: "If <X> is the cause, then <changing Y> will make the bug disappear / <changing Z> will make it worse."

If you cannot state the prediction, the hypothesis is a vibe — discard or sharpen it.

**Show the ranked list to the user before testing.** They often have domain knowledge that re-ranks instantly ("we just deployed a change to #3"), or know hypotheses they've already ruled out. Cheap checkpoint, big time saver. Don't block on it — proceed with your ranking if the user is unavailable.

#### Testing Protocol

1. **One variable at a time.** Each probe must map to a specific prediction. Change exactly one thing and re-run the feedback loop.

2. **Tag every debug log** with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup at the end becomes a single grep. Untagged logs survive; tagged logs die.

3. **Tool preference:**
   1. **Debugger / REPL inspection** if the env supports it. One breakpoint beats ten logs.
   2. **Targeted logs** at the boundaries that distinguish hypotheses.
   3. Never "log everything and grep".

4. **Performance regressions:** Logs are usually wrong for perf. Instead: establish a baseline measurement (timing harness, `performance.now()`, profiler, query plan), then bisect. Measure first, fix second.

5. **Verify Before Continuing**
   - Hypothesis confirmed? → Phase 4
   - Didn't work? Form NEW hypothesis from remaining candidates
   - DON'T add more fixes on top

6. **When You Don't Know**
   - Say "I don't understand X"
   - Don't pretend to know
   - Research more
   - Escalate to human with specific questions

### Phase 4: Implementation

**Fix the root cause, not the symptom:**

1. **Create Failing Test Case at the Correct Seam**

   Write the regression test **before the fix** — but only if there is a **correct seam** for it.

   A **correct seam** is one where the test exercises the **real bug pattern** as it occurs at the call site. If the only available seam is too shallow (single-caller test when the bug needs multiple callers, unit test that can't replicate the chain that triggered the bug), a regression test there gives false confidence.

   **If no correct seam exists, that itself is the finding.** Note it. The codebase architecture is preventing the bug from being locked down. This is valuable information — hand it off to the post-mortem (Phase 5).

   If a correct seam exists:
   1. Turn the minimised repro into a failing test at that seam.
   2. Watch it fail.
   3. Apply the fix.
   4. Watch it pass.
   5. Re-run the Phase 1 feedback loop against the original (un-minimised) scenario.

   For writing the failing test, delegate to `hw-tdd-agent` (TDD iron law requires a failing test before any production fix).

2. **Implement Single Fix**
   - Address the root cause identified in Phase 1
   - ONE change at a time
   - No "while I'm here" improvements
   - No bundled refactoring

3. **Verify Fix**
   - Test passes now?
   - No other tests broken?
   - Issue actually resolved? (re-run the feedback loop from Phase 1)
   - Use `hw-verification-before-completion` to confirm before claiming success

4. **If Fix Doesn't Work**
   - STOP
   - Count: How many fixes have you tried?
   - If < 3: Return to Phase 1, re-analyze with new information
   - **If ≥ 3: STOP and question the architecture (step 5 below)**
   - DON'T attempt Fix #4 without architectural discussion

5. **If 3+ Fixes Failed: Question Architecture**

   **Pattern indicating architectural problem:**
   - Each fix reveals new shared state/coupling/problem in different place
   - Fixes require "massive refactoring" to implement
   - Each fix creates new symptoms elsewhere

   **STOP and question fundamentals:**
   - Is this pattern fundamentally sound?
   - Are we "sticking with it through sheer inertia"?
   - Should we refactor architecture vs. continue fixing symptoms?

   **Discuss with your human partner before attempting more fixes**

   This is NOT a failed hypothesis — this is a wrong architecture.

### Phase 5: Cleanup + Post-Mortem

**Required before declaring DONE:**

```
□ Original repro no longer reproduces (re-run the Phase 1 feedback loop)
□ Regression test passes (or absence of correct seam is documented)
□ All [DEBUG-xxxx] instrumentation removed (grep the prefix)
□ Throwaway prototypes/harnesses deleted or clearly marked
□ The hypothesis that turned out correct is stated in the commit / PR message
```

**Then ask: what would have prevented this bug?** Consider:

- Was there no good test seam? → Architectural problem → recommend architecture improvement
- Was the bug in tangled, coupled code? → Recommend refactoring
- Was there a missing specification or ambiguous behavior? → Recommend documentation/ADR
- Was it a misunderstanding of an API? → Recommend improved documentation or type safety

**If the answer involves architectural change**, hand off with specifics to the architecture improvement capability (via hw-strategic-advisor or hw-controller). Make this recommendation **after** the fix is in, not before — you have more information now than when you started.

## Red Flags — STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when already tried 2+)**
- **Each fix reveals new problem in different place**
- "I don't need a feedback loop, the bug is obvious" — No loop = no confidence
- "Let me just add a log and see what happens" — That's guessing, not probing
- "I can't build a loop, let me just look at the code" — Staring at code doesn't find root causes
- Single hypothesis before generating alternatives — Anchoring on first idea

**ALL of these mean: STOP. Return to Phase 1.**

**If 3+ fixes failed:** Question the architecture (see Phase 4.5)

## Human Partner's Signals You're Doing It Wrong

Watch for these redirections from your human partner:
- "Is that not happening?" — You assumed without verifying
- "Will it show us...?" — You should have added evidence gathering
- "Stop guessing" — You're proposing fixes without understanding
- "Ultrathink this" — Question fundamentals, not just symptoms
- "We're stuck?" (frustrated) — Your approach isn't working

**When you see these:** STOP. Return to Phase 1.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question pattern, don't fix again. |
| "No time to build a loop, I'll just check the code" | Staring at code without a signal is the slowest way to debug. |
| "Let me try this fix and see if it works" | That's not a hypothesis, that's guessing. Form a falsifiable prediction first. |
| "I'm 90% sure it's X, let me just fix it" | 90% sure without evidence = 50% sure. Instrument first. |
| "The bug is non-deterministic, I can't build a loop" | Raise the reproduction rate. 50% is debuggable; 1% is not. |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1A. Feedback Loop** | Build fast deterministic pass/fail signal (10 techniques) | Agent-runnable loop you believe in |
| **1B. Root Cause** | Read errors, reproduce via loop, check changes, gather evidence | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare | Identify differences |
| **3. Hypothesis** | Generate 3-5 ranked falsifiable hypotheses, test one variable at a time | Confirmed root cause with evidence |
| **4. Implementation** | Create failing test at correct seam, fix, verify | Bug resolved, tests pass |
| **5. Post-Mortem** | Cleanup instrumentation, document finding, ask "what would have prevented this?" | Lessons captured, architecture issues flagged |

## When Process Reveals "No Root Cause"

If systematic investigation reveals issue is truly environmental, timing-dependent, or external:

1. You've completed the process — this is a valid outcome
2. Document what you investigated and why no root cause was found
3. Implement appropriate handling (retry, timeout, error message, graceful degradation)
4. Add monitoring/logging for future investigation
5. Write to `_bmad/memory/hw-shared/lessons/` for institutional knowledge

**But:** 95% of "no root cause" cases are incomplete investigation.

## Supporting Techniques

These techniques are part of systematic debugging and available in `references/`:

- **`references/root-cause-tracing.md`** — Trace bugs backward through call stack to find original trigger
- **`references/defense-in-depth.md`** — Add validation at multiple layers after finding root cause

## Integration with Harness Agents

- **hw-tdd-agent:** Delegate to this agent for creating failing test cases (Phase 4, Step 1). The TDD iron law requires a failing test before any production fix.
- **hw-verification-before-completion:** Apply before claiming the bug is fixed. Evidence before claims, always.
- **hw-reviewer-logic:** After fixing complex logic bugs, request a logic review to verify the fix doesn't introduce new edge cases.
- **hw-controller:** Escalate to the controller when 3+ fixes failed — this may indicate an architectural issue requiring human judgment.

## On Activation

When invoked for debugging:
1. Read the error report / bug description
2. Announce which phase you're starting with — always start with Phase 1A (Build a Feedback Loop)
3. Follow each phase sequentially — do not skip steps
4. **Phase 1A is the most important phase** — spend disproportionate effort on the feedback loop
5. Update status as you progress: "Phase 1A: Building feedback loop" → "Phase 1B: Investigating root cause" → "Phase 2: Pattern analysis" → etc.
6. Report findings with evidence at each phase completion
7. At Phase 5, always ask "what would have prevented this bug?" and capture architectural insights
