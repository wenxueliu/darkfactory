# Defense-in-Depth Validation

## Overview

When you fix a bug caused by invalid data, adding validation at one place feels sufficient. But that single check can be bypassed by different code paths, refactoring, or edge cases.

**Core principle:** Validate at EVERY layer data passes through. Make the bug structurally impossible.

## Why Multiple Layers

Single validation: "We fixed the bug"
Multiple layers: "We made the bug impossible"

Different layers catch different cases:
- Entry validation catches most bugs
- Business logic catches edge cases
- Environment guards prevent context-specific dangers
- Debug logging helps when other layers fail

## The Four Layers

### Layer 1: Entry Point Validation

**Purpose:** Reject obviously invalid input at API boundary

```python
def kv_put(self, key, value, cas=None):
    """Put KV with input validation."""
    if not key or not key.strip():
        raise ValueError("key cannot be empty")
    if not key.startswith("workflows/"):
        raise ValueError(f"key must start with 'workflows/': {key}")
    if value is None:
        raise ValueError("value cannot be None")
    # ... proceed
```

```python
def sync_to_consul(req_id, deps_file):
    """Sync workflow, validating dependencies."""
    if not req_id or not req_id.strip():
        raise ValueError("req_id cannot be empty")
    if not re.match(r'^[a-zA-Z0-9_-]+$', req_id):
        raise ValueError(f"req_id contains invalid characters: {req_id}")
    if not os.path.exists(deps_file):
        raise FileNotFoundError(f"dependencies file not found: {deps_file}")
    # ... proceed
```

### Layer 2: Business Logic Validation

**Purpose:** Ensure data makes sense for this operation

```python
def claim_task(self, req_id, task_name, agent_id):
    """Claim task with CAS, validating business rules."""
    # Validate task exists
    task_status = self.kv_get(f"workflows/{req_id}/tasks/{task_name}/status")
    if task_status is None:
        raise TaskNotFoundError(f"Task {task_name} not found in {req_id}")

    # Validate task is claimable
    if task_status.raw != "PENDING":
        raise TaskNotClaimableError(
            f"Task {task_name} status is {task_status.raw}, expected PENDING"
        )

    # Validate agent is registered
    agent = self.service_check(agent_id)
    if not agent:
        raise AgentNotRegisteredError(f"Agent {agent_id} not registered")

    # ... proceed with CAS
```

### Layer 3: Environment Guards

**Purpose:** Prevent dangerous operations in specific contexts

```python
# In watchdog.py
def rollback_task(self, req_id, task_name):
    """Rollback task, with safety guard."""
    # Never rollback in production without explicit confirmation
    if os.environ.get("HARNESS_ENV") == "production":
        if not os.environ.get("HARNESS_CONFIRM_ROLLBACK"):
            raise RuntimeError(
                "Refusing to rollback in production without HARNESS_CONFIRM_ROLLBACK"
            )

    # Never rollback a task that's already been rolled back > max_retries
    retry_count = int(self.kv_get(f"workflows/{req_id}/tasks/{task_name}/retry_count").raw or 0)
    if retry_count >= self.max_retries:
        raise MaxRetriesExceededError(
            f"Task {task_name} exceeded max retries ({self.max_retries})"
        )

    # ... proceed with rollback
```

### Layer 4: Debug Instrumentation

**Purpose:** Capture context for forensics

```python
def kv_put(self, key, value, cas=None):
    """Put KV with diagnostic logging."""
    if "DEBUG_KV" in os.environ:
        import traceback
        stack = traceback.format_stack()
        print(f"DEBUG kv_put: key={key}, cas={cas}", file=sys.stderr)
        print(f"DEBUG kv_put value preview: {str(value)[:200]}", file=sys.stderr)
        print(f"DEBUG kv_put stack:\n{''.join(stack[:-1])}", file=sys.stderr)

    # ... proceed
```

## Applying the Pattern

When you find a bug:

1. **Trace the data flow** — Where does bad value originate? Where is it used?
2. **Map all checkpoints** — List every point data passes through
3. **Add validation at each layer** — Entry, business, environment, debug
4. **Test each layer** — Try to bypass layer 1, verify layer 2 catches it

## Example: Empty Task Name in Consul KV

**Bug:** Empty `task_name` caused Consul KV write to `workflows/req-001/tasks//status`

**Data flow:**
1. Agent calls `claim_next_task.py` without `--task-name`
2. Script defaults `task_name = ""`
3. `_consul.py` writes to `workflows/req-001/tasks//status`
4. Aggregator reads empty key, crashes on parse

**Four layers added:**

- **Layer 1 (Entry):** `claim_next_task.py` validates `--task-name` is required, exits 1 if empty
- **Layer 2 (Business):** `_consul.py` `kv_put()` validates key does not contain `//` (double slash = likely empty segment)
- **Layer 3 (Environment):** Aggregator's `check_dependencies()` logs WARNING and skips task with empty name instead of crashing
- **Layer 4 (Debug):** All Consul KV writes log key and caller when `DEBUG_KV=1`

**Result:** Bug impossible to reproduce — empty task names are caught at entry, rejected at business layer, handled gracefully at orchestrator layer, and fully traceable via debug logging.

## Key Insight

All four layers are necessary. During testing, each layer catches bugs the others miss:

- Different code paths bypass entry validation
- Direct Consul API calls bypass business logic checks
- Edge cases on different environments need environment guards
- Debug logging identifies the structural pattern causing repeated issues

**Don't stop at one validation point.** Add checks at every layer.

## Harness-Specific Patterns

### Consul KV Validation

```python
# Always validate KV paths
VALID_KV_PREFIXES = ["workflows/", "agents/", "alerts/", "framework/"]

def validate_kv_key(key):
    if not any(key.startswith(p) for p in VALID_KV_PREFIXES):
        raise ValueError(f"Invalid KV key prefix: {key}")
    if "//" in key:
        raise ValueError(f"KV key contains empty segment: {key}")
    return key
```

### CAS Operation Guards

```python
def cas_atomic_write(self, key, new_value, expected_cas):
    """CAS write with defense-in-depth."""
    # Layer 1: validate inputs
    validate_kv_key(key)

    # Layer 2: verify current state
    current = self.kv_get(key)
    if current is None:
        raise KeyError(f"Cannot CAS on non-existent key: {key}")

    # Layer 3: environment guard (never bypass CAS in production)
    if os.environ.get("HARNESS_ENV") == "production" and expected_cas == 0:
        raise RuntimeError("Refusing unconditional write in production (CAS=0)")

    # Layer 4: perform CAS with logging
    if "DEBUG_CAS" in os.environ:
        print(f"DEBUG CAS: key={key}, expected_cas={expected_cas}, actual_cas={current.modify_index}",
              file=sys.stderr)

    return self.kv_put(key, new_value, cas=expected_cas)
```

### Agent Lifecycle Guards

```python
# In auto_register.py
def register_agent():
    """Register agent with defense-in-depth."""
    # Layer 1: validate agent identity
    agent_id = os.environ.get("AGENT_ID")
    if not agent_id:
        die(1, "AGENT_ID environment variable required")

    # Layer 2: check for duplicate registration
    existing = consul.kv_get(f"agents/{agent_id}/status")
    if existing and existing.raw == "active":
        die(1, f"Agent {agent_id} is already registered and active. "
                "Deregister first or use a different AGENT_ID.")

    # Layer 3: verify service name matches registered services
    service_name = os.environ.get("SERVICE_NAME")
    if not service_name:
        die(1, "SERVICE_NAME environment variable required")

    # Layer 4: proceed with registration
    consul.service_register(agent_id, service_name)
```
