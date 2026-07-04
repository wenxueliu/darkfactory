# DeepSeek (chat.deepseek.com) — Text Injection Details

## DOM structure

DeepSeek uses a **native HTMLTextAreaElement** wrapped in React.

```html
<textarea
  rows="1"
  placeholder="Send a message..."
  ...>
</textarea>
```

Located at: `document.querySelector("textarea")`

## Why `el.value = "..."` alone fails

React's controlled-component pattern intercepts value changes via
its own synthetic event system. Setting `.value` directly bypasses
React's state — the UI shows the new text, but React still thinks
the value is empty, and on next render React will **overwrite** your
text with the empty state.

## The working strategy: native setter + input event

```js
const ta = document.querySelector("textarea");
const setter = Object.getOwnPropertyDescriptor(
    window.HTMLTextAreaElement.prototype, "value"
).set;
setter.call(ta, text);
ta.dispatchEvent(new Event("input", { bubbles: true }));
ta.dispatchEvent(new Event("change", { bubbles: true }));
```

This is the canonical "fill a React-controlled textarea" pattern.
The native setter writes through React's tracker, and the input
event tells React to re-render with the new value.

## Why we need `bubbles: true`

React listens at the **root** (the entire document, not the input
itself) via event delegation. Without `bubbles: true`, your event
fires on the textarea but React's root listener never sees it.

## Edge cases

### Auto-growing textarea

DeepSeek's textarea auto-grows as you type. After injecting, you may
need to wait 100-200ms for the layout to settle before pressing Enter.

### Long text (>2000 chars)

DeepSeek has a 4000-char hard limit on the input. Beyond that, the
textarea will silently truncate. Solution: split into multiple
"Continue" messages, OR use the API instead.

### Markdown in input

DeepSeek auto-formats as you type (e.g. starts a list when you write `-`).
This is fine; just be aware that what you inject may be auto-restructured.

## Response extraction

DeepSeek streams responses. The selector has changed across versions:

- v1: `.message-content`
- v2: `.ds-message` or `[class*='message'][class*='assistant']`

Current default: `.ds-message, .markdown-content, [class*='message'][class*='assistant']`

Always take the LAST matching element. If the page has multiple
conversations visible (split view), this breaks down — but DeepSeek
doesn't do split view in the main chat.

## Sub-1-second response time

DeepSeek is **fast** — typically responds in 5-15s even for long
prompts. The default `--max-wait 180` is conservative; you can
typically lower to 60s.

## Submit button vs Enter

The DeepSeek textarea accepts both Enter (submits) and Shift+Enter
(newline). Our script sends plain Enter via `KeyboardEvent`, which
DeepSeek treats as submit.

If the textarea is empty after inject (race condition), the Enter
does nothing. Add a 500ms sleep before Enter if this happens.

## When DeepSeek refuses to respond

If you see "Server is busy" — this is rate limiting on DeepSeek's
side. Wait 30-60 seconds and retry. The script doesn't auto-retry;
you'll need to re-run.
