# ChatGPT (chatgpt.com) — Text Injection Details

## DOM structure

ChatGPT uses **ProseMirror** as the editor. The input element is:

```html
<div id="prompt-textarea" contenteditable="true" ...>
  <p data-placeholder="Ask anything"><br></p>
</div>
```

Located at: `document.querySelector("#prompt-textarea")`

## Why simple `.value =` or `.innerText =` fails

ProseMirror is a controlled editor with its own state machine. Setting
`.innerText` or `.value` directly is silently ignored because ProseMirror
intercepts the change. The element is also wrapped in React, so you
must trigger React's synthetic event system, not raw DOM events.

## The working strategy: ClipboardEvent paste

```js
const editor = document.querySelector("#prompt-textarea");
editor.focus();

const dt = new DataTransfer();
dt.setData("text/plain", text);

editor.dispatchEvent(new ClipboardEvent("paste", {
    clipboardData: dt,
    bubbles: true,
    cancelable: true,
}));
```

This triggers ProseMirror's paste handler, which:
1. Reads `clipboardData.getData("text/plain")`
2. Splits on newlines into ProseMirror nodes (preserving structure)
3. Inserts them at the current selection
4. Fires React's `onChange` to update the underlying state

## Edge cases

### Long text (>4000 chars)

ProseMirror handles it but visually lags. The DOM might not reflect
the full text immediately. Wait 200-500ms before pressing Enter.

### Multimodal content (images)

Set `dt.setData("text/html", "<img src='...'>")` and `text/plain`
simultaneously. Currently the script only sends text.

### Already-existing text

The `fill` action in webbridge clears-then-inserts. Our manual
`ClipboardEvent` approach does **not** clear — if the editor has prior
text, your paste appends. To clear first:

```js
editor.focus();
// Select all
document.execCommand("selectAll", false, null);
document.execCommand("delete", false, null);
// Then paste
```

## Response extraction

After submitting (Enter), ChatGPT streams the response. The last
`[data-message-author-role="assistant"]` element holds the full response.

**Important**: there are MULTIPLE assistant message elements on long
conversations. Always take the LAST one.

```js
const els = document.querySelectorAll("[data-message-author-role='assistant']");
const last = els[els.length - 1];
const text = last.innerText;
```

## Rate limits

Free tier: ~20 messages/3 hours.
Paid tier: much higher, but the `get_conversation_limit_reached` error
appears after 40+ messages in 3 hours.

If rate-limited, the page shows a banner, not an error toast. The
extraction will return whatever the page currently has, even the rate
limit message. Validate before using.

## When ChatGPT silently fails

Symptoms:
- Returns a 0-char response after max_wait
- Returns an error message like "Something went wrong"
- Returns a rate limit banner

**Workaround**: re-run with `--platforms deepseek,gemini` to skip
ChatGPT. The script will continue from stage 2.
