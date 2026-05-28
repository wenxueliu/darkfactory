# Black灯 Factory — Quickstart

> **New here?** Start with [README.md](../README.md) for overview and installation. This is a complete tutorial covering four onboarding scenarios.

> From zero to first delivery. Just follow the conversation.

---

## First, Tell Me About Your Situation

Black灯 Factory (HW) is a **human-AI collaborative software generation system** — you make the decisions, AI agents do the execution. Before we begin, I need to know where you stand.

**Pick your scenario:**

| Your situation | Jump to |
|----------------|---------|
| I have an existing project, want to add HW | [Scenario A: Add to Existing Project](#scenario-a-add-to-existing-project) |
| I'm starting a brand new project | [Scenario B: New Project](#scenario-b-new-project) |
| I have multiple microservices to orchestrate | [Scenario C: Microservices Multi-Repo](#scenario-c-microservices-multi-repo) |
| I just want to see what it looks like | [Scenario D: 5-Minute Tour](#scenario-d-5-minute-tour) |

---

## Scenario A: Add to Existing Project

### Step 1: Know Your Project

Answer three questions before you start:

1. **What language is your project?** Python / Java / Go / TypeScript / ... (use `*` for auto-detect)
2. **Monolith or microservices?** Monolith = one git repo, one deployable service
3. **How strict do you want quality gates?**
   - Fintech / compliance → full (security + logic + performance), frequent human checkpoints
   - Internal tools → logic only, minimal interruption
   - General business → default (all three), escalate to human after 3 iterations

### Step 2: Create Configuration

Create `_context/` under your project root:

```bash
mkdir -p _context/memory/sw-shared
mkdir -p _context/memory/sw-controller
```

**`_context/config.yaml`** (adjust based on your answers above):

```yaml
sw:
  architecture: "monolith"
  business_domain: "general"            # general | fintech | ecommerce | internal-tools
  min_iteration_before_human: 3         # AI iterations before escalating to human
  enabled_reviewers: "logic"            # start conservative, add security,performance later
  knowledge_base_auto_update: true
  merge_strategy: "merge"
```

**`_context/config.user.yaml`**:

```yaml
communication_language: English
user_name: Your Name
```

> See the Configuration section in `CLAUDE.md` for all configurable options.

### Step 3: Copy Skills

Copy the `skills/` directory from the HW repo into your project root. **Minimum 4 skills:**

| Skill | Role |
|-------|------|
| `sw-controller` | Orchestrator: requirements → design → decomposition → execution |
| `sw-tdd-agent` | TDD enforcer: RED → GREEN → REFACTOR |
| `sw-reviewer-logic` | Logic reviewer: correctness bugs and edge cases |
| `sw-worktree-controller` | Task executor: completes one task in an isolated worktree |

Optional but recommended:

| Skill | Role |
|-------|------|
| `sw-reviewer-security` | Security review |
| `sw-reviewer-performance` | Performance review |
| `sw-setup` | Environment initialization |

### Step 4: Update .gitignore

```bash
echo ".worktree/" >> .gitignore
echo "_context-output/" >> .gitignore
```

### Step 5: Take It for a Spin

In Claude Code:

```
/sw-controller I want to add a health check endpoint to the project
```

You'll see sw-controller kick off and walk through:
1. Requirement clarification (asks you a few questions)
2. Design output (generates design doc)
3. Task decomposition (generates tasks.yaml)
4. Task execution (launches worktree-controller → tdd-agent → reviewer)
5. Merge after quality gates pass

> For a quick taste, try: `/sw-controller demo mode: add a /health endpoint`

---

## Scenario B: New Project

### Step 1: Initialize Project Skeleton

```bash
mkdir my-project && cd my-project
git init

# Create base directories
mkdir -p src tests
mkdir -p _context/memory/sw-shared
mkdir -p _context/memory/sw-controller
mkdir -p skills
```

### Step 2: Configure

**`_context/config.yaml`**:

```yaml
sw:
  architecture: "monolith"
  business_domain: "general"
  min_iteration_before_human: 3
  enabled_reviewers: "security,logic,performance"
  knowledge_base_auto_update: true
  merge_strategy: "merge"
```

### Step 3: Copy Skills

Copy all `sw-*` skill directories from the HW repo's `skills/` into your `skills/`.

### Step 4: Let sw-controller Guide You

```
/sw-controller I'm starting a new project. Tech stack: {Python FastAPI / Go Gin / Java Spring Boot / ...}.
Core functionality: {one-sentence description}
```

sw-controller will guide you through:
1. **Requirements spec** — expands your one-liner into a full requirements document
2. **Design doc** — generates architecture, API, and test design
3. **Task decomposition** — breaks design into parallel TDD tasks
4. **Development** — implements tasks following TDD iron law (test first, code second)
5. **Review** — logic, security, and performance review layers
6. **Delivery** — merge, integration tests, release checklist

### Step 5: Harvest Knowledge

After your first development cycle, check `_context/memory/sw-shared/knowledge-base/`:
- `patterns/` — reusable patterns discovered
- `decisions/ADR-0001-*.md` — architecture decision records
- `lessons/` — lessons learned

These get automatically referenced in future development cycles.

---

## Scenario C: Microservices Multi-Repo

Before you start: you have multiple independent service repos (e.g. `user-service`, `order-service`, `web-frontend`).

### Step 1: Create Workspace

```bash
mkdir sw-workspace && cd sw-workspace
git init  # this repo only holds _context + skills, not service code
```

### Step 2: Clone All Services

```bash
mkdir -p services
git clone git@github.com:org/user-service.git services/user-service
git clone git@github.com:org/order-service.git services/order-service
git clone git@github.com:org/web-frontend.git services/web-frontend
```

> Key point: each `services/{id}/` keeps its own `.git/`, its own remote, its own CI/CD. Co-location just puts them in the same working directory — git independence is fully preserved.

### Step 3: Configure for Microservices

**`_context/config.yaml`**:

```yaml
sw:
  architecture: "microservices"

  microservices:
    max_parallel_services: 4
    integration_test_mode: "docker-compose"
    contract_first: true

  business_domain: "general"
  min_iteration_before_human: 3
  enabled_reviewers: "security,logic,performance"
  merge_strategy: "merge"
```

### Step 4: Auto-Discover Services

```
/sw-controller initialize: discover all services and build registry
```

sw-controller invokes sw-knowledge-agent to scan every repo under `services/`, auto-generating `_context/memory/sw-shared/service-registry.yaml`. It detects language, framework, API endpoints, and DB schema for each service — no manual metadata entry needed.

### Step 5: Start a Cross-Service Requirement

```
/sw-controller When a user places an order, we need to check their credit score.
This touches user-service (new credit score API), order-service (call credit check),
and web-frontend (show credit limit on checkout page)
```

Key differences from monolith mode:

| Phase | Microservices Behavior |
|-------|----------------------|
| Requirements | Adds "Service Impact Analysis" table — which services change, how |
| Design | 3-agent pipeline: Feature Designer (cross-service) → Service Designer (per service, parallel) → E2E Designer |
| Decomposition | Tasks grouped by service. Cross-service deps marked CONTRACT (parallel OK + mock) |
| Execution | Worktrees created per service under `.worktree/{service-id}/` |
| Quality | Extra contract-testing layer between API tests and E2E |
| Delivery | Multi-service coordinated release with rollback waves |

---

## Scenario D: 5-Minute Tour

No project setup needed. Experience HW directly inside the HW repo:

```
/sw-controller demo mode: run the simplest example from reference/
```

sw-controller skips config checks and runs a minimal path with defaults:
1. Generates a sample requirement
2. Walks through the full flow: requirements → design → decomposition → execution → merge
3. You'll see how agents collaborate, how quality gates work, how worktrees are managed

Expect 5-10 minutes end to end.

---

## After Your First Run

Congrats! You've used Black灯 Factory. Here's where to go next:

**I want to understand an agent deeply:**
- `skills/sw-controller/SKILL.md` — full orchestrator capability table
- `skills/sw-tdd-agent/SKILL.md` — TDD cycle details
- `skills/sw-reviewer-logic/SKILL.md` — logic review dimensions

**I want to tune configuration for my team:**
- Configuration section in `CLAUDE.md` — all configurable keys and defaults
- Adjust `_context/config.yaml` — review strictness, business domain, human intervention frequency

**I want to add a new business domain template:**
- `skills/sw-controller/references/template-router.md` — how to register a new domain template
- `skills/sw-controller/references/requirements-spec-template.md` — base template structure

**I ran into a problem:**
- Check `_context/memory/sw-shared/human-interventions.md` — any blocking escalations
- Check `_context/memory/sw-controller/global-state.yaml` — current phase and progress
- Describe the problem directly to sw-controller — it self-diagnoses

---

## Cheat Sheet

### Common Commands

| Command | What it does |
|---------|-------------|
| `/sw-controller {requirement}` | Start a new requirement |
| `/sw-controller status` | Show current progress |
| `/sw-controller continue` | Resume from last interruption |
| `/sw-controller escalate` | Escalate a blocker to human decision |

### Directory Map

| Directory | Contents | Maintained by |
|-----------|----------|---------------|
| `_context/config.yaml` | Project configuration | You (human) |
| `_context/memory/sw-shared/` | Requirements, designs, tasks, reviews | sw-controller (auto) |
| `_context/memory/sw-controller/` | Orchestration state, worktree registry | sw-controller (auto) |
| `.worktree/` | Isolated dev environments | Auto created/destroyed |
| `skills/` | Agent skill definitions | Updated with HW releases |
| `contracts/` | Cross-service API contracts | sw-controller + human review |
| `_context/memory/sw-shared/knowledge-base/` | Accumulated architecture knowledge | sw-controller (auto) |

---

---

**Ready?** Pick your scenario, open Claude Code, and type `/sw-controller` to start your first human-AI collaborative development session.

---

## Next Steps

| I want to… | Go here |
|------------|---------|
| Learn core design concepts | [concepts.md →](concepts.md) |
| Browse the full agent catalog | [agents.md →](agents.md) |
| Deep-dive into the knowledge base | [knowledge-base.md →](knowledge-base.md) |
| Understand system architecture | [architecture.md →](architecture.md) |
| View configuration reference | [configuration.md →](configuration.md) |
| Understand the orchestrator's capabilities | `skills/sw-controller/SKILL.md` |
| Learn the TDD execution flow | `skills/sw-tdd-agent/SKILL.md` |
| Use HW on Codex | [INSTALL-codex.md →](INSTALL-codex.md) |
| Use HW on OpenCode | [INSTALL-opencode.md →](INSTALL-opencode.md) |
