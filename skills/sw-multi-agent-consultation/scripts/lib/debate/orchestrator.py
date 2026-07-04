"""Debate orchestrator: 调度 AI 交互,不决策。

agent (Claude) 通过 orchestrator 调 ask(); orchestrator 只负责:
- 调 webbridge 注入 + 抓响应
- 原子地写 state
- 强制 30 次上限
"""

import time
from pathlib import Path
from typing import Any

from .state import DebateState, Interaction, InteractionType
from ..webbridge_client import call
from ..platforms import get_platform, PLATFORMS
from ..extractors import clean_response


class BudgetExhausted(RuntimeError):
    """30 次预算用完。"""


class UnknownActor(ValueError):
    """actor 不在 platforms 列表里。"""


def _press_enter(*, session: str) -> None:
    code = """
    (() => {
        const ae = document.activeElement;
        if (!ae) return {success: false};
        const opts = {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true};
        ae.dispatchEvent(new KeyboardEvent('keydown', opts));
        ae.dispatchEvent(new KeyboardEvent('keypress', opts));
        ae.dispatchEvent(new KeyboardEvent('keyup', opts));
        return {success: true};
    })()
    """
    call("evaluate", {"code": code}, session=session)


class DebateOrchestrator:
    """驱动 debate 状态机。

    用法(由 Claude 调度):
        orch = DebateOrchestrator(state, state_path)
        orch.propose("Design a 5-week AI Night Shift MVP")  # 3 interactions, parallel
        orch.ask(actor="deepseek", target="chatgpt", type=CRITIQUE,
                 prompt="Review ChatGPT's proposal, find 3 weaknesses",
                 summary="DS critiques GPT")
    """

    def __init__(
        self,
        state: DebateState,
        state_path: str | Path,
        *,
        session: str = "multi-agent-debate",
        poll_max_wait: float = 180.0,
        group_title: str = "Multi-Agent Debate",
    ):
        self.state = state
        self.state_path = Path(state_path)
        self.session = session
        self.poll_max_wait = poll_max_wait
        self.group_title = group_title

    # === 状态保存 ===

    def _save(self) -> None:
        self.state.save(self.state_path)

    # === 单次交互(核心) ===

    def _interact(
        self,
        actor: str,
        prompt: str,
        *,
        target: str | None = None,
        type: InteractionType = InteractionType.CLARIFICATION,
        prompt_summary: str = "",
    ) -> Interaction:
        """对单个 AI 跑一轮:打开/复用 tab → 注入 → 提交 → 抓响应 → 记录。"""
        if actor not in self.state.platforms:
            raise UnknownActor(f"actor {actor!r} not in platforms {self.state.platforms}")
        if self.state.budget_exhausted:
            raise BudgetExhausted(
                f"budget exhausted: {self.state.interaction_count}/{self.state.max_interactions} used"
            )

        platform = get_platform(actor)

        # 1. 打开新 tab(每次都新 tab,便于隔离)
        call(
            "navigate",
            {"url": platform.url, "newTab": True, "group_title": self.group_title},
            session=self.session,
        )
        time.sleep(4)  # 等页面渲染

        # 2. 注入
        inject_result = platform.inject(prompt, session=self.session)
        if not inject_result.get("success"):
            raise RuntimeError(
                f"inject failed for {actor}: {inject_result.get('error')}"
            )

        time.sleep(0.5)

        # 3. Enter 提交
        _press_enter(session=self.session)

        # 4. 等响应
        raw = platform.extract(session=self.session, max_wait=self.poll_max_wait)
        response = clean_response(raw)

        # 5. 记录
        idx = self.state.interaction_count + 1
        interaction = Interaction(
            idx=idx,
            actor=actor,
            target=target,
            type=type,
            prompt_summary=prompt_summary[:200],
            prompt=prompt,
            response=response,
        )
        self.state.interactions.append(interaction)
        self._save()
        return interaction

    # === 高级语义操作 ===

    def ask(
        self,
        actor: str,
        prompt: str,
        *,
        target: str | None = None,
        type: InteractionType = InteractionType.CLARIFICATION,
        prompt_summary: str = "",
    ) -> Interaction:
        """agent 主动问一个 AI(单次交互)。"""
        return self._interact(
            actor, prompt,
            target=target, type=type, prompt_summary=prompt_summary,
        )

    def propose(
        self,
        prompt_to_each: str,
        prompt_summary: str = "initial proposal",
    ) -> list[Interaction]:
        """让所有 AI 各自提案(parallel-ish,但 serial 调用以保 state 干净)。

        返回: 每个 AI 的 proposal Interaction
        """
        results = []
        for actor in self.state.platforms:
            if any(i.actor == actor and i.type == InteractionType.PROPOSAL
                   for i in self.state.interactions):
                # 已 propose 过,跳过
                continue
            i = self._interact(
                actor, prompt_to_each,
                type=InteractionType.PROPOSAL,
                prompt_summary=prompt_summary,
            )
            results.append(i)
        return results

    def add_agent_note(self, note: str) -> None:
        """调度器(Claude)加内部注释,不消耗 AI 交互预算。

        用途: 标记共识、记录分歧、备忘下一步。
        """
        i = Interaction(
            idx=self.state.interaction_count + 1,
            actor="agent",
            target=None,
            type=InteractionType.AGENT_NOTE,
            prompt_summary="agent note",
            prompt="",
            response=note,
        )
        self.state.interactions.append(i)
        self._save()

    def add_consensus(self, point: str) -> None:
        self.state.consensus_points.append(point)
        self._save()

    def add_dispute(self, point: str) -> None:
        self.state.open_disputes.append(point)
        self._save()

    def mark_finalized(self, plan_path: str) -> None:
        self.state.final_plan_path = plan_path
        self._save()


# === 辅助: 状态可视化 ===

def render_history_for_agent(state: DebateState) -> str:
    """生成给 Claude 看的人类可读历史(按时间线)。"""
    lines = [f"# Debate History: {state.topic}", ""]
    lines.append(f"Budget: {state.interaction_count}/{state.state.max_interactions if hasattr(state, 'state') else state.max_interactions}")
    lines.append(f"Consensus: {len(state.consensus_points)} | Disputes: {len(state.open_disputes)}")
    lines.append("")

    for i in state.interactions:
        if i.type == InteractionType.AGENT_NOTE:
            lines.append(f"### #{i.idx} [AGENT NOTE] {i.prompt_summary}")
            lines.append(f"  {i.response}")
            lines.append("")
            continue

        target_str = f" → {i.target}" if i.target else ""
        lines.append(
            f"### #{i.idx} [{i.actor}{target_str}] {i.type.value.upper()}"
        )
        lines.append(f"  Summary: {i.prompt_summary}")
        lines.append(f"  Prompt: {i.prompt[:200]}{'...' if len(i.prompt) > 200 else ''}")
        lines.append(f"  Response ({len(i.response)} chars):")
        # response 缩进
        for line in i.response.split("\n")[:50]:  # 截前 50 行
            lines.append(f"    {line}")
        if len(i.response.split("\n")) > 50:
            lines.append(f"    ... ({len(i.response.split(chr(10))) - 50} more lines)")
        lines.append("")

    return "\n".join(lines)
