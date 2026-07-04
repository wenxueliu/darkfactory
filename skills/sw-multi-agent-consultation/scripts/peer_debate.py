#!/usr/bin/env python3
"""peer-PK multi-agent debate CLI。

设计: 3 个 AI 相互对等,各提方案,互 PK,多轮迭代。
调度: 由 agent (Claude) 驱动,通过 invoke 这个 CLI 一步步推进。
预算: 默认 30 次 AI 交互,init 时可调。

子命令:
    init      创建空 state(还未发起任何交互)
    propose   让所有 AI 各自提案(消耗 N 次,N=platforms 数)
    ask       agent 主动问某个 AI(消耗 1 次)
    note      agent 加内部注释(不消耗预算)
    consensus agent 标记一个共识点(不消耗预算)
    dispute   agent 标记一个未决分歧(不消耗预算)
    state     打印当前 state 摘要
    history   打印完整交互历史(给 Claude 看)
    finalize  标记最终方案路径(state 收尾)
"""

import argparse
import json
import sys
import time
from pathlib import Path

# 允许直接 import lib
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from lib.webbridge_client import call, health, WebBridgeError  # noqa: E402
from lib.platforms import PLATFORMS  # noqa: E402
from lib.debate.state import DebateState, InteractionType  # noqa: E402
from lib.debate.orchestrator import (  # noqa: E402
    DebateOrchestrator,
    BudgetExhausted,
    UnknownActor,
    render_history_for_agent,
)


# === 健康检查(在所有命令前可选) ===

def _ensure_webbridge_ok() -> None:
    try:
        st = health()
        if not st.get("running") or not st.get("extension_connected"):
            print(f"WARNING: webbridge not fully healthy: {st}", file=sys.stderr)
        else:
            print(f"webbridge OK: v{st.get('version', '?')}", file=sys.stderr)
    except WebBridgeError as e:
        print(f"ERROR: webbridge not reachable: {e}", file=sys.stderr)
        sys.exit(1)


# === 子命令 ===

def cmd_init(args) -> int:
    _ensure_webbridge_ok()

    if Path(args.state).exists():
        print(f"ERROR: state file already exists: {args.state}", file=sys.stderr)
        print("  Use --force to overwrite", file=sys.stderr)
        if not args.force:
            return 1

    # 读 topic 描述
    description = args.description or ""
    if args.description_file:
        description = Path(args.description_file).read_text()

    state = DebateState(
        topic=args.topic,
        topic_description=description,
        platforms=args.platforms.split(","),
        max_interactions=args.max_interactions,
    )
    state.save(args.state)
    print(f"✓ init done: {args.state}")
    print(f"  topic: {args.topic}")
    print(f"  platforms: {state.platforms}")
    print(f"  budget: {state.max_interactions}")
    print()
    print(f"Next: python peer_debate.py propose --state {args.state} --prompt-file <q.md>")
    return 0


def cmd_propose(args) -> int:
    state = DebateState.load(args.state)
    orch = DebateOrchestrator(state, args.state, session=args.session)
    prompt = Path(args.prompt_file).read_text() if args.prompt_file else args.prompt

    print(f"Budget before: {state.interaction_count}/{state.max_interactions}")
    if state.budget_exhausted:
        print("ERROR: budget exhausted", file=sys.stderr)
        return 1

    results = orch.propose(prompt, prompt_summary=args.summary)
    print(f"✓ propose done: {len(results)} AIs responded")
    for i in results:
        print(f"  [{i.actor}] {len(i.response)} chars")
    print(f"Budget after: {state.interaction_count}/{state.max_interactions}")
    return 0


def cmd_ask(args) -> int:
    state = DebateState.load(args.state)
    orch = DebateOrchestrator(state, args.state, session=args.session)

    if state.budget_exhausted:
        print("ERROR: budget exhausted", file=sys.stderr)
        return 1

    prompt = Path(args.prompt_file).read_text() if args.prompt_file else args.prompt
    itype = InteractionType(args.type)

    print(f"Budget before: {state.interaction_count}/{state.max_interactions}")
    i = orch.ask(
        args.actor, prompt,
        target=args.target,
        type=itype,
        prompt_summary=args.summary,
    )
    print(f"✓ ask done: #{i.idx} [{i.actor}→{i.target or '-'}] {itype.value}")
    print(f"  response: {len(i.response)} chars")
    print(f"Budget after: {state.interaction_count}/{state.max_interactions}")
    return 0


def cmd_note(args) -> int:
    state = DebateState.load(args.state)
    orch = DebateOrchestrator(state, args.state)
    orch.add_agent_note(args.note)
    print(f"✓ note added (no budget consumed)")
    return 0


def cmd_consensus(args) -> int:
    state = DebateState.load(args.state)
    orch = DebateOrchestrator(state, args.state)
    orch.add_consensus(args.point)
    print(f"✓ consensus point added (total: {len(state.consensus_points)})")
    return 0


def cmd_dispute(args) -> int:
    state = DebateState.load(args.state)
    orch = DebateOrchestrator(state, args.state)
    orch.add_dispute(args.point)
    print(f"✓ dispute point added (total: {len(state.open_disputes)})")
    return 0


def cmd_state(args) -> int:
    state = DebateState.load(args.state)
    print(state.summary())
    return 0


def cmd_history(args) -> int:
    state = DebateState.load(args.state)
    print(render_history_for_agent(state))
    return 0


def cmd_finalize(args) -> int:
    state = DebateState.load(args.state)
    orch = DebateOrchestrator(state, args.state)
    orch.mark_finalized(args.plan_path)
    print(f"✓ finalized: {args.plan_path}")
    print(f"  total interactions: {state.interaction_count}/{state.max_interactions}")
    print(f"  consensus points: {len(state.consensus_points)}")
    print(f"  open disputes: {len(state.open_disputes)}")
    return 0


def cmd_synthesize(args) -> int:
    """输出结构化历史给 Claude,让 Claude 写最终方案。

    这个命令本身不发任何 AI 调用,只是 dump 状态。
    Claude 读完后用 Write 工具写最终方案,然后调 finalize。
    """
    state = DebateState.load(args.state)
    out = {
        "topic": state.topic,
        "topic_description": state.topic_description,
        "platforms": state.platforms,
        "budget_used": f"{state.interaction_count}/{state.max_interactions}",
        "consensus_points": state.consensus_points,
        "open_disputes": state.open_disputes,
        "interactions": [
            {
                "idx": i.idx,
                "actor": i.actor,
                "target": i.target,
                "type": i.type.value,
                "prompt_summary": i.prompt_summary,
                "response_excerpt": i.response[:500] + ("..." if len(i.response) > 500 else ""),
            }
            for i in state.interactions
        ],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


# === CLI ===

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="peer-PK multi-agent debate via kimi-webbridge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # init
    sp = sub.add_parser("init", help="create empty debate state")
    sp.add_argument("--state", required=True, help="state.json path")
    sp.add_argument("--topic", required=True, help="short topic name")
    sp.add_argument("--description", default="", help="topic description")
    sp.add_argument("--description-file", help="read description from file")
    sp.add_argument("--platforms", default="chatgpt,deepseek,gemini",
                    help="comma-separated platform IDs")
    sp.add_argument("--max-interactions", type=int, default=30,
                    help="total AI interaction cap (default: 30)")
    sp.add_argument("--force", action="store_true", help="overwrite existing state")
    sp.set_defaults(func=cmd_init)

    # propose
    sp = sub.add_parser("propose", help="ask all AIs to propose")
    sp.add_argument("--state", required=True)
    sp.add_argument("--prompt", help="prompt text")
    sp.add_argument("--prompt-file", help="read prompt from file")
    sp.add_argument("--summary", default="initial proposal", help="short label")
    sp.add_argument("--session", default="multi-agent-debate")
    sp.set_defaults(func=cmd_propose)

    # ask
    sp = sub.add_parser("ask", help="agent asks one AI")
    sp.add_argument("--state", required=True)
    sp.add_argument("--actor", required=True, help="which AI to ask (chatgpt/deepseek/gemini)")
    sp.add_argument("--target", help="which AI this is about (for critique/rebuttal)")
    sp.add_argument("--type", default="clarification",
                    choices=[t.value for t in InteractionType],
                    help="interaction type")
    sp.add_argument("--prompt", help="prompt text")
    sp.add_argument("--prompt-file", help="read prompt from file")
    sp.add_argument("--summary", required=True, help="short label for the agent")
    sp.add_argument("--session", default="multi-agent-debate")
    sp.set_defaults(func=cmd_ask)

    # note (no budget)
    sp = sub.add_parser("note", help="add agent note (no budget)")
    sp.add_argument("--state", required=True)
    sp.add_argument("--note", required=True)
    sp.set_defaults(func=cmd_note)

    # consensus (no budget)
    sp = sub.add_parser("consensus", help="mark a consensus point (no budget)")
    sp.add_argument("--state", required=True)
    sp.add_argument("--point", required=True)
    sp.set_defaults(func=cmd_consensus)

    # dispute (no budget)
    sp = sub.add_parser("dispute", help="mark an open dispute (no budget)")
    sp.add_argument("--state", required=True)
    sp.add_argument("--point", required=True)
    sp.set_defaults(func=cmd_dispute)

    # state
    sp = sub.add_parser("state", help="print state summary")
    sp.add_argument("--state", required=True)
    sp.set_defaults(func=cmd_state)

    # history
    sp = sub.add_parser("history", help="print full interaction history")
    sp.add_argument("--state", required=True)
    sp.set_defaults(func=cmd_history)

    # synthesize (read-only dump for Claude)
    sp = sub.add_parser("synthesize", help="dump structured state (for Claude to write final plan)")
    sp.add_argument("--state", required=True)
    sp.set_defaults(func=cmd_synthesize)

    # finalize
    sp = sub.add_parser("finalize", help="mark final plan path")
    sp.add_argument("--state", required=True)
    sp.add_argument("--plan-path", required=True)
    sp.set_defaults(func=cmd_finalize)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except BudgetExhausted as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except UnknownActor as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main() or 0)
