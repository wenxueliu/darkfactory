"""3 个 AI 平台的文本注入器。

每个 AI 的输入框用不同前端框架,必须用不同的 DOM 注入策略:

| 平台       | 框架                  | 注入方式                                     |
|------------|-----------------------|----------------------------------------------|
| ChatGPT    | ProseMirror           | execCommand('insertText') + paste fallback  |
| DeepSeek   | 原生 <textarea>       | native value setter + input event           |
| Gemini     | 自定义 <rich-textarea>| execCommand('insertText') + paste event      |

所有注入器返回 {success: bool, error?: str} (经 _unwrap 解包 daemon 响应)。
"""

import json
from typing import Any

from .webbridge_client import call


def _js_string_literal(s: str) -> str:
    """Python str → 安全嵌入 JS 字符串字面量。"""
    return json.dumps(s, ensure_ascii=False)


def _unwrap(result: dict[str, Any]) -> dict[str, Any]:
    """解包 daemon 响应。

    daemon 返回 {ok, data} 包装; data 是 evaluate 的 result, 即
    {type, value}; value 才是 JS 端 IIFE 真正返回的对象。
    """
    if not isinstance(result, dict):
        return {}
    data = result.get("data")
    if not isinstance(data, dict):
        return {}
    value = data.get("value")
    if isinstance(value, dict):
        return value
    return {}


def inject_chatgpt(text: str, *, session: str) -> dict[str, Any]:
    """ChatGPT (#prompt-textarea 是 ProseMirror)。

    兼容 2026 年新版 ChatGPT:
    - 优先用 execCommand('insertText') — 触发 beforeinput/input, ProseMirror 接受
    - 旧版兼容: 试 ClipboardEvent paste, 失败回退到 execCommand
    - 直接改 innerHTML / value 会被 ProseMirror 状态机拒绝
    """
    text_literal = _js_string_literal(text)
    code = f"""
    (() => {{
        const editor = document.querySelector("#prompt-textarea");
        if (!editor) return {{ success: false, error: "editor #prompt-textarea not found" }};
        editor.focus();
        try {{
            document.execCommand("selectAll", false, null);
            document.execCommand("delete", false, null);
        }} catch (e) {{ /* 静默 */ }}
        const ok = document.execCommand("insertText", false, {text_literal});
        const written = (editor.innerText || "").trim();
        if (!ok || !written) {{
            const dt = new DataTransfer();
            dt.setData("text/plain", {text_literal});
            editor.dispatchEvent(
                new ClipboardEvent("paste", {{
                    clipboardData: dt,
                    bubbles: true,
                    cancelable: true,
                }})
            );
        }}
        return {{
            success: true,
            method: ok ? "execCommand" : "paste-fallback",
            length: (editor.innerText || "").length,
        }};
    }})()
    """
    return _unwrap(call("evaluate", {"code": code}, session=session))


def inject_deepseek(text: str, *, session: str) -> dict[str, Any]:
    """DeepSeek (<textarea>,原生 HTMLTextAreaElement)。

    React 受控组件必须用原型链上的 native value setter,否则 React
    state 不会更新。
    """
    text_literal = _js_string_literal(text)
    code = f"""
    (() => {{
        const ta = document.querySelector("textarea");
        if (!ta) return {{ success: false, error: "textarea not found" }};
        const setter = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype, "value"
        ).set;
        setter.call(ta, {text_literal});
        ta.dispatchEvent(new Event("input", {{ bubbles: true }}));
        ta.dispatchEvent(new Event("change", {{ bubbles: true }}));
        return {{ success: true, length: ta.value.length }};
    }})()
    """
    return _unwrap(call("evaluate", {"code": code}, session=session))


def inject_gemini(text: str, *, session: str) -> dict[str, Any]:
    """Gemini (<rich-textarea> 自定义元素)。

    双轨: execCommand 触发 beforeinput(部分版本需要), 再 dispatch
    paste event 触发 ProseMirror-style 内部更新。
    """
    text_literal = _js_string_literal(text)
    code = f"""
    (() => {{
        const rt = document.querySelector("rich-textarea")
                || document.querySelector('div[contenteditable="true"]');
        if (!rt) return {{ success: false, error: "rich-textarea not found" }};
        rt.focus();
        try {{
            document.execCommand("insertText", false, {text_literal});
        }} catch (e) {{ /* 静默,继续 paste */ }}
        const dt = new DataTransfer();
        dt.setData("text/plain", {text_literal});
        const ok = rt.dispatchEvent(
            new ClipboardEvent("paste", {{
                clipboardData: dt,
                bubbles: true,
                cancelable: true,
            }})
        );
        return {{ success: ok }};
    }})()
    """
    return _unwrap(call("evaluate", {"code": code}, session=session))


# === 注册表 ===

INJECTORS = {
    "chatgpt": inject_chatgpt,
    "deepseek": inject_deepseek,
    "gemini": inject_gemini,
}
