# Gemini (gemini.google.com/app) — Text Injection Details

## DOM structure

Gemini uses a **custom element** that's not a standard textarea or
contenteditable — it's Google-internal rich-textarea.

```html
<rich-textarea class="...">
  <div contenteditable="true" ...>
    ...
  </div>
</rich-textarea>
```

Located at: `document.querySelector("rich-textarea")`
Fallback: `document.querySelector('div[contenteditable="true"]')`

## Why simple strategies fail

| Strategy | Failure mode |
|---|---|
| `el.innerText = text` | Content shows, but submit button stays disabled |
| `el.value = text` (for textarea) | Not a textarea, no .value to set |
| Single `ClipboardEvent("paste")` | Some Gemini versions need pre-warming |

## The working strategy: dual-track

```js
const rt = document.querySelector("rich-textarea")
         || document.querySelector('div[contenteditable="true"]');
rt.focus();

// 1. execCommand — triggers beforeinput event in modern browsers
try {
    document.execCommand("insertText", false, text);
} catch (e) { /* silent — fall through to paste */ }

// 2. ClipboardEvent — triggers ProseMirror-style internal update
const dt = new DataTransfer();
dt.setData("text/plain", text);
rt.dispatchEvent(new ClipboardEvent("paste", {
    clipboardData: dt,
    bubbles: true,
    cancelable: true,
}));
```

The two-step approach handles both:
- Old Gemini versions (pre-2024-Q4) that listen for `input` events
- New Gemini versions that use an internal ProseMirror-like state machine

## Why Gemini is the hardest

Gemini's frontend changes more often than ChatGPT or DeepSeek. The
selector `rich-textarea` was correct in 2024-Q4 but may shift. The
extractor in the script uses **multiple fallback selectors** for this
reason:

```js
const selector = "message-content, .model-response, [data-test-id*='response']";
```

If all fail, you need to inspect the live DOM:

```js
document.querySelectorAll("*").forEach(el => {
    if (el.textContent && el.textContent.length > 100 && el.textContent.length < 50000) {
        console.log(el.tagName, el.className, el.textContent.slice(0, 50));
    }
});
```

## Submit: Enter vs Send button

After inject, the send button (a `paper-plane-icon` or `<button>` with
`aria-label="Send message"`) becomes enabled. We press Enter via
`KeyboardEvent`, which Gemini also accepts. If Enter doesn't work, fall
back to clicking the button:

```js
const sendBtn = document.querySelector('button[aria-label="Send message"]');
sendBtn.click();
```

## Response extraction

Gemini's response is wrapped in a custom `<message-content>` element.
Streaming renders into a child `<div>` that grows. We poll until the
child's `textContent` is stable for 8s.

If `message-content` isn't found, look for:
- `.model-response` (older versions)
- `[data-test-id*='response']` (newer test-IDs)

## When Gemini is throttled

"Gemini is at capacity" or "You've reached the limit" — these are
Google account-level rate limits, NOT script bugs. The extractor
will return the rate-limit text, which you must filter out:

```python
if "capacity" in response.lower() or "limit" in response.lower():
    # re-run with --platforms chatgpt,deepseek
    raise SomeError("Gemini throttled, aborting stage 3")
```

## Gemini vs Bard

As of 2024-Q2, Bard was renamed to Gemini. The URL
`gemini.google.com/app` works. The old `bard.google.com` redirects.

## Multimodal input

Gemini accepts images in the input. To inject an image:
1. `dt.setData("text/plain", caption_text)`
2. Also set `dt.items.add(new File([blob], "image.png"))` (requires
   fetching the image first)

This is NOT implemented in the current script. Add a `--image` flag
if needed.
