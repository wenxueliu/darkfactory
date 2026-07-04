"""平台配置表:URL / 显示名 / 角色。"""

from dataclasses import dataclass
from typing import Callable

from . import extractors, injectors


@dataclass(frozen=True)
class Platform:
    id: str
    display_name: str
    role: str          # proposer | critic | arbiter
    url: str
    inject: Callable
    extract: Callable
    submit_key: str = "Enter"  # 大部分平台用 Enter 发送


PLATFORMS: dict[str, Platform] = {
    "chatgpt": Platform(
        id="chatgpt",
        display_name="ChatGPT",
        role="proposer",
        url="https://chatgpt.com/",
        inject=injectors.inject_chatgpt,
        extract=extractors.extract_chatgpt,
    ),
    "deepseek": Platform(
        id="deepseek",
        display_name="DeepSeek",
        role="critic",
        url="https://chat.deepseek.com/",
        inject=injectors.inject_deepseek,
        extract=extractors.extract_deepseek,
    ),
    "gemini": Platform(
        id="gemini",
        display_name="Gemini",
        role="arbiter",
        url="https://gemini.google.com/app",
        inject=injectors.inject_gemini,
        extract=extractors.extract_gemini,
    ),
}


# === 默认 3 阶段角色编排 ===

DEFAULT_SEQUENCE = ["chatgpt", "deepseek", "gemini"]


def get_platform(platform_id: str) -> Platform:
    if platform_id not in PLATFORMS:
        raise KeyError(
            f"unknown platform: {platform_id!r}, "
            f"available: {list(PLATFORMS)}"
        )
    return PLATFORMS[platform_id]
