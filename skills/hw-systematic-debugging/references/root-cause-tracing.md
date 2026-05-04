# Root Cause Tracing

## Overview

Bugs often manifest deep in the call stack (git init in wrong directory, file created in wrong location, database opened with wrong path). Your instinct is to fix where the error appears, but that's treating a symptom.

**Core principle:** Trace backward through the call chain until you find the original trigger, then fix at the source.

## When to Use

**Use when:**
- Error happens deep in execution (not at entry point)
- Stack trace shows long call chain
- Unclear where invalid data originated
- Need to find which test/code triggers the problem
- Multiple components involved (Aggregator, Watchdog, Agent, Consul KV)

## The Tracing Process

### 1. Observe the Symptom

```
Error: Consul KV key not found at workflows/req-001/tasks/build-api
```

### 2. Find Immediate Cause

**What code directly causes this?**
```python
# consul_client.py
response = urllib.request.urlopen(f"{consul_addr}/v1/kv/{key}")
# Key doesn't exist → 404 response
```

### 3. Ask: What Called This?

```
consul_client.kv_get("workflows/req-001/tasks/build-api/status")
  → called by aggregator.get_task_status("build-api")
  → called by aggregator.check_dependencies("req-001")
  → called by aggregator.poll_workflows()
  → called by daemon.run_aggregator_loop()
```

### 4. Keep Tracing Up

**What value was passed?**
- `key` = `"workflows/req-001/tasks/build-api/status"`
- Task "build-api" was referenced but never created
- The `dependencies.json` referenced a non-existent task

### 5. Find Original Trigger

**Where did the invalid reference come from?**
```python
# sync_to_consul.py line 42
deps = json.load(open("dependencies.json"))
# dependencies.json has a typo: "build-api" instead of "build-api-service"
```

## Adding Diagnostic Instrumentation

When you can't trace manually, add instrumentation:

### Python (Harness Framework)

```python
import traceback
import sys

def kv_get(self, key, **kwargs):
    """Get KV with diagnostic logging."""
    if "DEBUG_KV" in os.environ:
        stack = traceback.format_stack()
        print(f"DEBUG kv_get: key={key}", file=sys.stderr)
        print(f"DEBUG kv_get stack:\n{''.join(stack[:-1])}", file=sys.stderr)
    # ... proceed with actual get
```

### Bash (stage-bridge scripts)

```bash
# Before the problematic operation
echo "DEBUG: entering task claim" >&2
echo "DEBUG: CONSUL_ADDR=$CONSUL_ADDR" >&2
echo "DEBUG: AGENT_ID=$AGENT_ID" >&2
echo "DEBUG: REQ_ID=$REQ_ID" >&2
echo "DEBUG: PWD=$(pwd)" >&2
```

**Critical:** Use stderr for debug output (stdout may be consumed by JSON parsing downstream).

**Run and capture:**
```bash
DEBUG_KV=1 python -m harness_framework.daemon 2>&1 | grep 'DEBUG kv_get'
```

## Finding Which Component Is Broken

In a multi-component system (Aggregator → Watchdog → Agent → Consul), bisect components:

```
1. Verify Consul KV state directly: curl Consul API
   → State correct? Problem is in framework/agent.
   → State wrong? Problem is in sync/initialization.

2. Verify Aggregator: check daemon logs for activation
   → Aggregator working? Problem is downstream.
   → Aggregator not activating? Check dependencies/published flag.

3. Verify Watchdog: check if task was recovered/retried
   → Watchdog recovered? Problem was Agent death/timeout.
   → Watchdog didn't recover? Check Watchdog config/health checks.

4. Verify Agent: check Consul service registration and heartbeat
   → Agent registered? Check stage-bridge scripts.
   → Agent not registered? Check register_agent.py execution.
```

## Real Example: Task Stuck in BLOCKED State

**Symptom:** Task "run-tests" stuck in BLOCKED, never transitions to PENDING

**Trace chain:**
1. Aggregator not activating "run-tests"
2. Aggregator sees dependency "build-service" as not DONE
3. Consul KV shows "build-service" status = DONE
4. BUT: Consul KV key is `build-service` while dependency references `build_service` (underscore vs hyphen)
5. Dependency declaration in `dependencies.json` has wrong task name

**Root cause:** Name mismatch between declared dependency and actual Consul KV key

**Fix:** Unify task naming convention (kebab-case everywhere). Added validation in `sync_to_consul.py` to check dependency references against declared tasks.

**Also added defense-in-depth:**
- Layer 1: `sync_to_consul.py` validates all `depends_on` references exist
- Layer 2: Aggregator logs a WARNING when a dependency target is not found after 3 poll cycles
- Layer 3: WebAPI `/api/workflow/<req_id>` endpoint shows unresolved dependencies in red
- Layer 4: Integration test that validates dependency resolution end-to-end

## Key Principle

**NEVER fix just where the error appears.** Trace back to find the original trigger.

## Stack Trace Tips

- **Python:** `traceback.format_stack()` shows complete call chain
- **Bash:** `set -x` for command tracing, `PS4='+ ${BASH_SOURCE}:${LINENO}:'` for file:line
- **In tests:** Use `print(..., file=sys.stderr)` not logger — logger may be suppressed
- **Before operation:** Log before the dangerous operation, not after it fails
- **Include context:** Function args, env vars, working directory, timestamps
