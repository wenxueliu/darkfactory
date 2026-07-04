"""kimi-webbridge HTTP 客户端。

封装本地 daemon API 调用,统一处理 session / timeout / 错误。
"""

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_DAEMON = "http://127.0.0.1:10086/command"
DEFAULT_TIMEOUT = 30


class WebBridgeError(RuntimeError):
    """WebBridge 调用失败。"""


def call(
    action: str,
    args: dict[str, Any] | None = None,
    *,
    session: str = "multi-agent-consultation",
    daemon: str = DEFAULT_DAEMON,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """调一次 webbridge action,返回 JSON 结果。

    Args:
        action: action 名 (navigate / evaluate / snapshot / click / fill / ...)
        args: action 参数
        session: 顶层 session 字段(用于 tab group 归类)
        daemon: daemon URL,默认 127.0.0.1:10086
        timeout: HTTP 超时秒数

    Returns:
        daemon 返回的 JSON 解析后的 dict

    Raises:
        WebBridgeError: daemon 报错 / 网络错误 / 解析失败
    """
    payload = {
        "action": action,
        "args": args or {},
        "session": session,
    }
    req = Request(
        daemon,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise WebBridgeError(f"HTTP {e.code} from {daemon}: {body}") from e
    except URLError as e:
        raise WebBridgeError(f"connection error to {daemon}: {e}") from e
    except json.JSONDecodeError as e:
        raise WebBridgeError(f"non-JSON response from {daemon}: {e}") from e


def health() -> dict[str, Any]:
    """读 daemon 状态。返回 {running, extension_connected, ...}。"""
    # 状态走另一个端点,不走 /command
    from urllib.request import urlopen
    with urlopen("http://127.0.0.1:10086/status", timeout=5) as resp:
        return json.loads(resp.read())
