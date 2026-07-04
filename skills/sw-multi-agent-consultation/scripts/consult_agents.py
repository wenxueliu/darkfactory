#!/usr/bin/env python3
"""3-AI 协作咨询编排器。

执行流程:
1. 打开 ChatGPT(提议者):发问,拿初始方案
2. 打开 DeepSeek(评审者):把 ChatGPT 方案发去,拿评审
3. 打开 Gemini(仲裁者):把前两者摘要发去,拿第三方视角

可选阶段(每个 AI 都支持多轮追问):
- round-2: 在同一个 AI tab 里继续追问
- cross-question: 让 B 回应 A 的反驳

用法:
    python consult_agents.py --question topics/night-shift.md
    python consult_agents.py --question q.txt --output-dir out/ --platforms chatgpt,deepseek
    python consult_agents.py --question q.txt --rounds 2  # 每个 AI 追问 1 次
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# 允许直接 import lib
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from lib.webbridge_client import call, health, WebBridgeError  # noqa: E402
from lib.platforms import PLATFORMS, DEFAULT_SEQUENCE, get_platform  # noqa: E402
from lib.extractors import clean_response  # noqa: E402


# === 主流程 ===

def _press_enter(*, session: str) -> dict[str, Any]:
    """按 Enter 发送(模拟键盘事件,不依赖具体按钮)。"""
    code = """
    (() => {
        const ae = document.activeElement;
        if (!ae) return {success: false, error: "no active element"};
        // 部分平台需要 keydown + keypress + keyup 完整序列
        const opts = {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true};
        ae.dispatchEvent(new KeyboardEvent('keydown', opts));
        ae.dispatchEvent(new KeyboardEvent('keypress', opts));
        ae.dispatchEvent(new KeyboardEvent('keyup', opts));
        return {success: true, tag: ae.tagName};
    })()
    """
    return call("evaluate", {"code": code}, session=session)


def consult_one(
    platform_id: str,
    question: str,
    output_dir: Path,
    *,
    session: str,
    group_title: str,
    poll_max_wait: float = 180.0,
) -> str | None:
    """对单个 AI 完整跑一遍:打开 → 注入 → 提交 → 等待 → 提取 → 保存。

    Returns:
        清洗后的响应文本,或 None(失败时)
    """
    platform = get_platform(platform_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"[{platform.display_name}] ({platform.role})")
    print(f"  URL: {platform.url}")
    print(f"{'='*60}")

    # 1. 打开新 tab
    try:
        nav = call(
            "navigate",
            {"url": platform.url, "newTab": True, "group_title": group_title},
            session=session,
        )
        print(f"  1. open tab: tabId={nav.get('tabId')}")
    except WebBridgeError as e:
        print(f"  1. open tab FAILED: {e}")
        return None

    # 2. 等页面加载 + 登录完成
    print("  2. waiting for page ready (5s)...")
    time.sleep(5)

    # 3. 注入文本
    print("  3. inject question...")
    inject_result = platform.inject(question, session=session)
    if not inject_result.get("success"):
        print(f"  3. inject FAILED: {inject_result.get('error')}")
        return None
    print(f"  3. inject ok")

    # 4. 等 DOM 反映输入(部分平台需要几百毫秒)
    time.sleep(0.5)

    # 5. 按 Enter 提交
    print("  4. press Enter...")
    enter_result = _press_enter(session=session)
    if not enter_result.get("success"):
        print(f"  4. press Enter FAILED: {enter_result.get('error')}")
        # 不一定 fatal,有些平台自动 submit

    # 6. 等响应
    print(f"  5. waiting for response (max {poll_max_wait}s)...")
    raw = platform.extract(session=session, max_wait=poll_max_wait)
    response = clean_response(raw)

    if not response:
        print(f"  5. response EMPTY (timeout or extraction failed)")
        return None

    # 7. 保存
    out_file = output_dir / f"{platform_id}_{platform.role}_round1.txt"
    out_file.write_text(response)
    print(f"  6. saved: {out_file} ({len(response)} chars)")

    return response


def consult_all(
    question: str,
    output_dir: Path,
    *,
    platforms: list[str] = None,
    session: str = "multi-agent-consultation",
    poll_max_wait: float = 180.0,
) -> dict[str, str]:
    """跑完整 3-AI 流水线。"""
    platforms = platforms or DEFAULT_SEQUENCE
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 健康检查
    try:
        st = health()
        if not st.get("running") or not st.get("extension_connected"):
            print(f"WARNING: webbridge not fully healthy: {st}")
        else:
            print(f"webbridge OK: v{st.get('version', '?')}, uptime {st.get('uptime_seconds', '?')}s")
    except WebBridgeError as e:
        print(f"ERROR: webbridge not reachable: {e}")
        sys.exit(1)

    # 2. 写问题到 output_dir
    (output_dir / "question.txt").write_text(question)
    print(f"question saved: {output_dir}/question.txt ({len(question)} chars)")

    # 3. 顺序咨询
    results: dict[str, str] = {}
    for platform_id in platforms:
        response = consult_one(
            platform_id,
            question,
            output_dir,
            session=session,
            group_title=f"3-AI Consultation",
            poll_max_wait=poll_max_wait,
        )
        if response is not None:
            results[platform_id] = response

    # 4. 写汇总
    summary = {
        "question_file": str(output_dir / "question.txt"),
        "platforms_consulted": list(results.keys()),
        "total_chars": sum(len(v) for v in results.values()),
        "files": {
            pid: str(output_dir / f"{pid}_{get_platform(pid).role}_round1.txt")
            for pid in results
        },
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nsummary: {summary}")
    print(f"\n{'='*60}\nALL DONE. Output: {output_dir}\n{'='*60}")
    return results


# === CLI ===

def main():
    parser = argparse.ArgumentParser(
        description="3-AI consultation via kimi-webbridge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="Path to question file (markdown or plain text)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="./multi_agent_out",
        help="Output directory (default: ./multi_agent_out)",
    )
    parser.add_argument(
        "--platforms", "-p",
        default=",".join(DEFAULT_SEQUENCE),
        help=f"Comma-separated platform IDs, available: {','.join(PLATFORMS)} (default: {','.join(DEFAULT_SEQUENCE)})",
    )
    parser.add_argument(
        "--session", "-s",
        default="multi-agent-consultation",
        help="WebBridge session name (controls tab group label)",
    )
    parser.add_argument(
        "--max-wait", "-w",
        type=float,
        default=180.0,
        help="Max seconds to wait for each response (default: 180)",
    )

    args = parser.parse_args()

    # 1. 读问题
    q_path = Path(args.question)
    if not q_path.exists():
        print(f"ERROR: question file not found: {q_path}", file=sys.stderr)
        sys.exit(1)
    question = q_path.read_text()

    # 2. 解析 platforms
    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    for p in platforms:
        if p not in PLATFORMS:
            print(f"ERROR: unknown platform: {p!r}, available: {list(PLATFORMS)}", file=sys.stderr)
            sys.exit(1)

    # 3. 跑
    consult_all(
        question=question,
        output_dir=Path(args.output_dir),
        platforms=platforms,
        session=args.session,
        poll_max_wait=args.max_wait,
    )


if __name__ == "__main__":
    main()
