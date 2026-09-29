---
name: sw-multi-agent-consultation
description: "Orchestrates a peer-PK debate among three or more AI agents via kimi-webbridge, with proposal, mutual critique, convergence, and a capped round-trip budget. Use for multi-agent reviews, third-party perspectives, convergence discussions, or requests such as ask ChatGPT and DeepSeek, compare 3 AIs, 三方评审, 多 AI 协作, multi-agent debate, or peer PK."
metadata:
  version: "2.0.0"
  external_dependencies:
    - name: kimi-webbridge
      version: "*"
      type: MCP
      required: false
      purpose: optional browser-backed access to peer AI platforms
---

# Multi-Agent Consultation: Peer-PK Debate

Drive 3+ AI agents through a **peer-to-peer debate** that converges on a
high-stakes plan or decision. Unlike a fixed pipeline (proposer→critic→arbiter),
this is a flexible state machine: any AI can be asked anything, any number of
times, until either consensus is reached or the budget runs out.

## When to use this skill

Use when **single-model bias is a real risk** AND you have 10-30 minutes:

- Architectural decisions with long blast radius
- Plans that combine research + critique + synthesis
- Topics where one AI's known weakness is another's strength
- Decisions you want **defensible** — backed by adversarial review, not one voice

**Do NOT use** for:
- Simple Q&A (one round, one AI is enough)
- Time-sensitive decisions (3+ AI roundtrips = 5+ min minimum)
- Topics you can't share (PII, NDA'd specs)

## The Peer-PK Design

```

## Input Contract

| Input | Required | Description |
|---|---:|---|
| `topic` | Yes | 需要多方观点的决策、方案或争议。 |
| `platforms` | No | 至少三个 peer 平台；默认配置由运行环境提供。 |
| `budget` | No | 最大 round-trip 数；默认 30，必须有上限。 |
| `state_path` | No | 可恢复的 JSON 状态文件路径。 |

## External Dependency Metadata

`kimi-webbridge` 是可选 MCP 依赖。不可用时返回 `BLOCKED`/`NEEDS_USER_INPUT`，不得把单模型意见伪装成 peer 共识；状态文件仍可用于保存已完成的讨论。

## Output Contract

写入原子 JSON debate state，并返回 `CONSENSUS`、`DISPUTE`、`BUDGET_EXHAUSTED` 或 `BLOCKED`，包含各平台提案、批评、证据、未解决争议、共识理由、round-trip 计数和最终建议。

## Acceptance Criteria

- 至少三个独立 peer 完成 proposal 或明确记录不可用原因。
- 每轮消耗计数准确，达到预算后停止调用并基于已有证据收敛。
- 结论区分共识、少数意见和未解决争议，不把投票当作事实证明。
- 状态写入具备原子性，可从中断处恢复且不重复扣减预算。
                  ┌────────── Claude (agent) ──────────┐
                  │  reads state, decides next ask     │
                  │  marks consensus/disputes          │
                  └────────────────────────────────────┘
                       │                │
        ┌──────────────┼────────────────┼──────────────┐
        ▼              ▼                ▼              ▼
   [ChatGPT]       [DeepSeek]       [Gemini]       [...N]
   (peer)          (peer)           (peer)

   Each AI can be asked: PROPOSAL · CRITIQUE · REBUTTAL ·
                         CLARIFICATION · REVISION · SYNTHESIS_VOTE
```

**Key properties:**
1. **No fixed roles.** Any AI may be asked to propose, critique, rebut, or
   revise — the agent decides what each AI does at each step.
2. **No fixed order.** Parallel `propose` first (3 interactions), then
   free-form critique/rebuttal rounds until convergence.
3. **Budget-bounded.** Default 30 total AI round-trips per debate. Once
   exhausted, no more AI calls — the agent must synthesize and write the
   final plan from what it has.
4. **Agent is the scheduler.** The agent reads `state.json` after each step,
   decides what to ask next (or to mark a consensus / dispute / finalize).
   The CLI is dumb transport — it does not decide.
5. **State persists.** Every interaction is atomic JSON; the debate is
   resumable from any point. `note`/`consensus`/`dispute` cost zero budget.

## Interaction Types

| Type | When | Example |
|---|---|---|
| `proposal` | First time each AI contributes | "Design a 5-week AI Night Shift MVP" |
| `critique` | AI reviews another's proposal | "Review ChatGPT's plan, find 3 weaknesses" |
| `rebuttal` | AI responds to a critique of its own work | "Address DeepSeek's 5 cuts, defend or revise" |
| `clarification` | Agent needs more detail from a specific AI | "What's the test coverage gate threshold?" |
| `revision` | AI updates its own plan based on discussion | "Update your plan to address the Gemini points" |
| `synthesis_vote` | AI votes on a proposed final synthesis | "Rank these 3 candidate plans 1-2-3 with reasons" |

## How to invoke

```bash
SKILL=~/.claude/skills/multi-agent-consultation
STATE=/tmp/my-debate.json

# 1. Init state (default 3 platforms, 30 budget)
python $SKILL/scripts/peer_debate.py init \
    --state $STATE \
    --topic "AI Night Shift MVP design" \
    --description-file ./topic.md \
    --platforms chatgpt,deepseek,gemini

# 2. Round 1: parallel proposals (3 budget)
python $SKILL/scripts/peer_debate.py propose \
    --state $STATE \
    --prompt-file ./topic.md \
    --summary "initial proposal"

# 3. Agent reads state, decides next round
python $SKILL/scripts/peer_debate.py state --state $STATE

# 4. Round 2: DeepSeek critiques ChatGPT (1 budget)
python $SKILL/scripts/peer_debate.py ask \
    --state $STATE \
    --actor deepseek \
    --target chatgpt \
    --type critique \
    --prompt-file ./critique-prompt.md \
    --summary "DS critiques GPT"

# 5. Agent marks consensus (no budget)
python $SKILL/scripts/peer_debate.py consensus \
    --state $STATE \
    --point "All 3 agree on 3-layer pipeline"

# 6. ... continue ask/note/consensus/dispute until converged or budget out

# 7. Synthesize: dump structured JSON for agent to read & write final plan
python $SKILL/scripts/peer_debate.py synthesize --state $STATE

# 8. Mark final plan path
python $SKILL/scripts/peer_debate.py finalize --state $STATE --plan-path ./final.md
```

The agent (Claude) runs these in sequence, observing state between calls.

## CLI Reference

```
peer_debate.py
├── init      --state PATH --topic NAME [--description-file F]
│              [--platforms chatgpt,deepseek,gemini] [--max-interactions 30]
├── propose   --state PATH --prompt-file F [--summary LABEL]
├── ask       --state PATH --actor X [--target Y] [--type TYPE]
│              --prompt-file F --summary LABEL
├── note      --state PATH --note TEXT                  (no budget)
├── consensus --state PATH --point TEXT                 (no budget)
├── dispute   --state PATH --point TEXT                 (no budget)
├── state     --state PATH                              (print summary)
├── history   --state PATH                              (print full history)
├── synthesize --state PATH                             (JSON for agent)
└── finalize  --state PATH --plan-path P
```

Budget: every `propose` and `ask` consumes budget; `note/consensus/dispute`
do not. Budget cap is enforced — `BudgetExhausted` is raised if exceeded.

## How the script works

1. **Health-check** kimi-webbridge daemon (`127.0.0.1:10086/status`)
2. **Open new tab** for each interaction (auto-grouped under the session)
3. **Inject prompt** using platform-specific DOM strategy:
   - ChatGPT → ProseMirror `#prompt-textarea` (ClipboardEvent paste)
   - DeepSeek → native `<textarea>` (HTMLTextAreaElement value setter)
   - Gemini → custom `<rich-textarea>` (execCommand + paste event dual-track)
4. **Press Enter** to submit
5. **Poll for response** until stable (handles streaming)
6. **Clean** response (strip UI chrome, markdown-only)
7. **Atomic save** to state.json

For detailed platform mechanics, see:
- `references/chatgpt-injection.md`
- `references/deepseek-injection.md`
- `references/gemini-injection.md`

## After the debate: the agent's job

The CLI is transport. **Convergence is the agent's job.**

The agent:
1. Reads `state` summary after each round.
2. Reads `history` to see all responses when deciding the next move.
3. Decides: ask a critique? a rebuttal? mark a consensus? mark a dispute?
4. Stops asking when: (a) consensus reached, (b) dispute irreducible,
   (c) budget exhausted.
5. Calls `synthesize` to dump structured state.
6. **Writes the final plan** using its own judgment — synthesizing the
   AIs' proposals, critiques, and revisions.
7. Calls `finalize --plan-path <final.md>`.

The agent should follow these heuristics:
- **Consensus** (all or most agree) → likely correct, lean into it.
- **2-vs-1 disagreement** → usually the dissenter saw something. Read
  *why* before dismissing.
- **Unanimous blind spot** → the agent's domain knowledge matters here.
- **Mutual reinforcement of a bad idea** (proposer + critic both endorse
  without challenging) → walk away from that path.

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Empty response after max_wait | Streaming didn't settle, OR extraction selector wrong | Bump `--max-wait`, check selector in `lib/extractors.py` |
| `inject FAILED: editor not found` | Page didn't load, OR not logged in | Wait longer, re-login manually |
| `ChatGPT rate limit` | Too many rounds | Wait 30 min, OR use `--platforms deepseek,gemini` to skip |
| `BudgetExhausted` | 30-cap hit | Call `synthesize`, write final plan from what you have |
| Garbled text in response | Pasted HTML/markdown not fully consumed | Add explicit "respond in plain text" to prompt |
| Tab not focused after inject | Another tab took focus | Add small `setTimeout` before Enter |

## Origin & validation

This workflow evolved from a 3-stage pipeline (proposer→critic→arbiter)
that ran 2026-06-19 producing the AI Night Shift v1→v2→v3 plan convergence.
The original hierarchy was **demoted to a legacy preset** (`scripts/consult_agents.py`)
because it was too rigid: it forced a fixed order even when a topic wanted
a different shape (e.g. ask Gemini first when the topic needs fresh-eyes
review of an existing decision, not a new proposal).

The peer-PK design fixes this by:
- Letting the agent decide roles per step (no hard-coded stage 1/2/3)
- Capping total budget so the debate terminates
- Making the agent's job explicit (read state → decide → ask → repeat)
- Persisting state after every interaction (resumable)

## Files in this skill

```
~/.claude/skills/multi-agent-consultation/
├── SKILL.md                                # this file
├── scripts/
│   ├── peer_debate.py                      # peer-PK CLI (primary)
│   ├── consult_agents.py                   # legacy 3-stage CLI (preset)
│   └── lib/
│       ├── webbridge_client.py             # daemon HTTP client + health
│       ├── injectors.py                    # per-platform text injection
│       ├── extractors.py                   # per-platform response extraction
│       ├── platforms.py                    # platform registry
│       └── debate/                         # peer-PK state machine
│           ├── __init__.py
│           ├── state.py                    # DebateState, Interaction, types
│           └── orchestrator.py             # DebateOrchestrator
├── references/
│   ├── chatgpt-injection.md                # ProseMirror paste details
│   ├── deepseek-injection.md               # textarea native setter details
│   └── gemini-injection.md                 # rich-textarea dual-track details
└── examples/
    └── night-shift-convergence.md          # worked example (2026-06-19)
```
