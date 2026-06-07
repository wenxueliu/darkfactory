---
name: multi-component-diagnostics
description: Multi-component system diagnostic instrumentation template. Use when debugging systems with multiple layers (e.g., Aggregator → Watchdog → Agent → stage-bridge → Consul KV) — before proposing any fix, gather evidence at each layer.
---

# Multi-Component Diagnostics

**When to use:** Systems with multiple components (chain of services, message queues, distributed state). Single-component bugs rarely need this; multi-component bugs always benefit.

## Iron Rule

**Add diagnostic instrumentation BEFORE proposing fixes.** Without per-layer evidence you are guessing which layer broke. The instrumentation is the cheapest debugging tool you have — write it once, run once, find the failing layer.

## Per-Layer Evidence Template

For each component boundary, capture:

| What | Why |
|------|-----|
| **Data entering component** | Detects corrupt input from upstream |
| **Data exiting component** | Detects component-local mutation / drop |
| **Environment/config propagation** | Detects stale config, missing secrets, wrong endpoint |
| **State at this layer** | Detects lost writes, replay, ordering bugs |

**Run once to gather evidence showing WHERE it breaks.**
**THEN analyze evidence to identify failing component.**
**THEN investigate that specific component.**

## Reference Example: Harness Multi-Component

```bash
# Layer 1: Consul KV state (canonical state)
curl -s "http://127.0.0.1:8500/v1/kv/workflows/<req_id>/tasks/<task>/status?raw"
echo "=== Task status in Consul ==="

# Layer 2: Aggregator log (writes to KV)
tail -50 /tmp/harness-daemon.log | grep "req_id"

# Layer 3: Watchdog state (reads from KV)
curl -s "http://127.0.0.1:8500/v1/health/service/<agent_name>"

# Layer 4: Agent heartbeat (writes heartbeat to KV)
python scripts/heartbeat.py --check
```

**Output analysis pattern:**
- If Layer 1 shows correct state but Layer 3 is wrong → KV is correct, Watchdog is broken
- If Layer 1 is wrong but Layer 2 logged correct writes → Aggregator is broken
- If Layer 2 never logged the write → Agent never published → Agent is broken
- If Layer 3 sees fresh data but the action is wrong → action handler is broken

## Reusable Template (Copy-Paste)

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

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Logging inside the suspected component only | Adds evidence at ALL boundaries, then filter |
| Logging after the bug is "fixed" | Add logs FIRST, run, gather evidence, then propose fix |
| Logging only errors, not successes | A missing success log IS the evidence |
| Forgetting the config layer | 30% of multi-component bugs are config propagation, not code |
| "I'll just look at the code" | Multi-component bugs are rarely visible in code review alone |

## Cleanup

After root cause is found, remove diagnostic logs. Tag them with a unique prefix (e.g. `[DEBUG-a4f2]`) so cleanup is a single grep.

## See Also

- `references/root-cause-tracing.md` — backward tracing technique
- `references/defense-in-depth.md` — adding validation at multiple layers
