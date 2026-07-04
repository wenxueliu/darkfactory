"""3 个 AI 平台的响应提取器。

每个 AI 把"AI 回复"渲染在不同的 DOM 结构里,通过 accessibility tree
或 querySelector 拿到最后一条 assistant 消息的纯文本。

策略: 等到流式输出结束(无新 token 一段时间)+ 抓最后一条消息。
"""

import json
import re
import time
from typing import Any

from .webbridge_client import call


# === 通用: 等响应"稳定" ===

def _wait_until_idle(
    *,
    session: str,
    selector: str,
    poll_interval: float = 2.0,
    stable_for: float = 8.0,
    max_wait: float = 180.0,
) -> str:
    """等 selector 里的文本长度稳定 stable_for 秒后返回。

    适用于流式输出(ChatGPT/Gemini 都用 streaming)。
    """
    last_text = ""
    last_change = time.time()
    deadline = time.time() + max_wait

    while time.time() < deadline:
        code = f"""
        (() => {{
            const els = document.querySelectorAll({json.dumps(selector)});
            if (!els.length) return "";
            // 取最后一个
            const last = els[els.length - 1];
            return last.innerText || last.textContent || "";
        }})()
        """
        result = call("evaluate", {"code": code}, session=session, timeout=10)
        # 解包 {ok, data:{type, value}} → value
        text = ""
        if isinstance(result, dict):
            data = result.get("data") or {}
            if isinstance(data, dict):
                text = data.get("value") or ""

        if text != last_text:
            last_text = text
            last_change = time.time()
        else:
            if time.time() - last_change >= stable_for:
                return last_text

        time.sleep(poll_interval)

    return last_text  # timeout,返回最后一次内容


# === 平台特定提取器 ===

def extract_chatgpt(*, session: str, **kwargs) -> str:
    """ChatGPT: assistant 消息用 [data-message-author-role='assistant'] 标记。"""
    selector = "[data-message-author-role='assistant']"
    return _wait_until_idle(session=session, selector=selector, **kwargs)


def extract_deepseek(*, session: str, **kwargs) -> str:
    """DeepSeek: assistant 消息用 .ds-message 或 .message-content。"""
    # 实际 selector 因版本而异,优先用 .ds-message,fallback 到通用类
    selector = ".ds-message, .markdown-content, [class*='message'][class*='assistant']"
    return _wait_until_idle(session=session, selector=selector, **kwargs)


def extract_gemini(*, session: str, **kwargs) -> str:
    """Gemini: 模型回复在 <message-content> 或 .model-response。"""
    selector = "message-content, .model-response, [data-test-id*='response']"
    return _wait_until_idle(session=session, selector=selector, **kwargs)


# === 注册表 ===

EXTRACTORS = {
    "chatgpt": extract_chatgpt,
    "deepseek": extract_deepseek,
    "gemini": extract_gemini,
}


def clean_response(raw: str) -> str:
    """清洗响应文本(去前后空白、合并多余换行)。"""
    text = raw.strip()
    # 合并连续 3+ 空行到 2 个
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text
