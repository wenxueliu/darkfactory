"""Debate state: 持久化所有交互 + 共识/分歧追踪。

设计原则:
- Agent (Claude) 是调度器,只读 state 决定下一步
- 每次 ask() 都原子地写 state.json
- 任意时刻可中断、可恢复
- 30 次默认上限,可在 init 时调
"""

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any


class InteractionType(str, Enum):
    PROPOSAL = "proposal"        # 初始提案 (每个 AI 一次)
    CRITIQUE = "critique"        # 批评他人
    REBUTTAL = "rebuttal"        # 回应他人批评
    CLARIFICATION = "clarification"  # 追问/澄清
    REVISION = "revision"        # 根据讨论更新自己的方案
    SYNTHESIS_VOTE = "synthesis_vote"  # 最终方案投票
    AGENT_NOTE = "agent_note"    # 调度器(Claude)加的内部注释,不消耗 AI 交互


@dataclass
class Interaction:
    """一次与一个 AI 的完整交互。"""
    idx: int
    actor: str                       # 哪个 AI
    target: str | None               # 针对哪个 AI(可空,proposal 无 target)
    type: InteractionType
    prompt_summary: str              # 调度器视角的简短描述
    prompt: str                      # 完整 prompt
    response: str                    # AI 回复全文
    timestamp: float = field(default_factory=time.time)
    cost_tokens_estimate: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Interaction":
        d = dict(d)
        d["type"] = InteractionType(d["type"])
        return cls(**d)


@dataclass
class DebateState:
    """完整 debate 状态。"""
    topic: str
    topic_description: str
    platforms: list[str]                       # 参与的 AI ID
    max_interactions: int = 30
    interactions: list[Interaction] = field(default_factory=list)
    consensus_points: list[str] = field(default_factory=list)   # 调度器(Claude)记录的共识
    open_disputes: list[str] = field(default_factory=list)     # 调度器记录的未决分歧
    started_at: float = field(default_factory=time.time)
    last_modified: float = field(default_factory=time.time)
    final_plan_path: str | None = None

    # === 计数器 ===

    @property
    def interaction_count(self) -> int:
        return len(self.interactions)

    @property
    def budget_remaining(self) -> int:
        return self.max_interactions - self.interaction_count

    @property
    def budget_exhausted(self) -> bool:
        return self.budget_remaining <= 0

    # === 索引器(便于调度器查询) ===

    def proposals(self) -> dict[str, Interaction]:
        """每个 AI 的最新 proposal(若有 revision,以 revision 为准)。"""
        result: dict[str, Interaction] = {}
        for i in self.interactions:
            if i.type == InteractionType.PROPOSAL or i.type == InteractionType.REVISION:
                result[i.actor] = i
        return result

    def interactions_by(self, actor: str) -> list[Interaction]:
        return [i for i in self.interactions if i.actor == actor]

    def interactions_of_type(self, t: InteractionType) -> list[Interaction]:
        return [i for i in self.interactions if i.type == t]

    def latest_by(self, actor: str) -> Interaction | None:
        items = self.interactions_by(actor)
        return items[-1] if items else None

    def critiques_against(self, target: str) -> list[Interaction]:
        return [
            i for i in self.interactions
            if i.target == target and i.type == InteractionType.CRITIQUE
        ]

    # === 持久化 ===

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "topic_description": self.topic_description,
            "platforms": self.platforms,
            "max_interactions": self.max_interactions,
            "interactions": [i.to_dict() for i in self.interactions],
            "consensus_points": self.consensus_points,
            "open_disputes": self.open_disputes,
            "started_at": self.started_at,
            "last_modified": self.last_modified,
            "final_plan_path": self.final_plan_path,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DebateState":
        return cls(
            topic=d["topic"],
            topic_description=d["topic_description"],
            platforms=d["platforms"],
            max_interactions=d["max_interactions"],
            interactions=[Interaction.from_dict(i) for i in d["interactions"]],
            consensus_points=d.get("consensus_points", []),
            open_disputes=d.get("open_disputes", []),
            started_at=d.get("started_at", time.time()),
            last_modified=d.get("last_modified", time.time()),
            final_plan_path=d.get("final_plan_path"),
        )

    def save(self, path: str | Path) -> None:
        self.last_modified = time.time()
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, path: str | Path) -> "DebateState":
        return cls.from_dict(json.loads(Path(path).read_text()))

    # === 给调度器(Claude)看的人类可读摘要 ===

    def summary(self) -> str:
        """一屏可看的状态摘要,供 Claude 决策用。"""
        lines = [
            f"=== DEBATE STATE ===",
            f"Topic: {self.topic}",
            f"Platforms: {', '.join(self.platforms)}",
            f"Budget: {self.interaction_count} / {self.max_interactions} used, {self.budget_remaining} remaining",
            f"",
        ]
        # proposals
        proposals = self.proposals()
        if proposals:
            lines.append(f"--- Proposals ({len(proposals)}/{len(self.platforms)}) ---")
            for actor, p in proposals.items():
                char_count = len(p.response)
                lines.append(f"  [{actor}] {p.type.value} @ idx={p.idx} ({char_count} chars)")
            lines.append("")

        # critiques matrix
        lines.append("--- Critique matrix ---")
        for target in self.platforms:
            cs = self.critiques_against(target)
            if cs:
                critics = ", ".join(f"{c.actor}@idx{c.idx}" for c in cs)
                lines.append(f"  → {target}: criticized by {critics}")
        lines.append("")

        # consensus / disputes (agent-curated)
        if self.consensus_points:
            lines.append(f"--- Consensus ({len(self.consensus_points)}) ---")
            for c in self.consensus_points:
                lines.append(f"  ✓ {c}")
            lines.append("")
        if self.open_disputes:
            lines.append(f"--- Open disputes ({len(self.open_disputes)}) ---")
            for d in self.open_disputes:
                lines.append(f"  ✗ {d}")
            lines.append("")

        # last 3 interactions
        if self.interactions:
            lines.append(f"--- Last 3 interactions ---")
            for i in self.interactions[-3:]:
                tag = f"[{i.actor}→{i.target or '-'}]" if i.target else f"[{i.actor}]"
                lines.append(f"  #{i.idx} {tag} {i.type.value}: {i.prompt_summary}")

        return "\n".join(lines)
