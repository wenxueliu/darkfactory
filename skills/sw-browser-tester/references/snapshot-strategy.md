# Snapshot Strategy for Browser E2E Testing

## What This Is

Snapshot-based verification patterns adapted from gstack browse for the multiagents L3 browser testing layer. gstack uses a persistent daemon with `$B snapshot` / `$B snapshot -D` / `$B screenshot` commands. This document maps those patterns to Playwright's built-in capabilities in a self-contained test script context.

## gstack → Playwright Mapping

| gstack browse pattern | Playwright equivalent |
|----------------------|---------------------|
| `$B snapshot` — Accessibility tree with @e refs | `page.accessibility.snapshot()` — ARIA tree for structure verification |
| `$B snapshot -i` — Interactive elements (@e refs) | Not needed — uses `data-testid` from design doc (stable, deterministic) |
| `$B snapshot -D` — Diff vs previous snapshot | `expect(page).toHaveScreenshot({ name: '...' })` — visual diff engine |
| `$B snapshot -a` — Annotated screenshot with red overlays | `page.screenshot({ fullPage: true })` + Playwright HTML report (built-in annotation) |
| `$B screenshot` — Plain screenshot | `page.screenshot({ path: '...', fullPage: true })` |
| `$B console --errors` — Console error log | `page.on('console', msg => { ... })` listener |
| `$B network` — Network request log | `page.on('requestfailed', ...)` + `page.on('response', ...)` listeners |
| `$B css <sel> <prop>` — Computed CSS | `locator.evaluate(el => getComputedStyle(el).getPropertyValue('prop'))` |
| `$B is visible/enabled/checked` — Element state | `expect(locator).toBeVisible()/.toBeEnabled()/.toBeChecked()` |

## Snapshot Types

### Type 1: Baseline Screenshot (Before Action)

Capture the page state before a critical action. Serves as the "before" image for visual diff.

```typescript
// gstack browse: $B snapshot (stores baseline)
// Playwright: full-page screenshot before action
await page.screenshot({
  path: `${SCREENSHOT_DIR}/E2E-{ID}-before.png`,
  fullPage: true,
});
```

When to capture:
- Before clicking "Submit" / "Pay" / "Delete" / any mutation
- Before navigating to a new page
- Before filling a critical form
- Before triggering a state transition

### Type 2: After-Action Screenshot (Visual Diff)

Capture the page state after the action completes. Playwright's visual comparison engine diffs against the baseline.

```typescript
// gstack browse: $B snapshot -D (unified diff output)
// Playwright: visual comparison with auto-diff
await expect(page).toHaveScreenshot({
  name: 'E2E-CART-001-after-submit',
  fullPage: true,
  maxDiffPixels: 100,          // allowed pixel difference
  threshold: 0.2,              // pixelmatch comparison threshold (0-1)
  animations: 'disabled',       // disable CSS animations/transitions
});
```

Configurable thresholds per domain (set in `_context/config.yaml` → `sw.browser_e2e`):
- `fintech`: `maxDiffPixels: 50`, `threshold: 0.1` (strict — financial UI must not shift)
- `ecommerce`: `maxDiffPixels: 100`, `threshold: 0.2`
- `general`: `maxDiffPixels: 200`, `threshold: 0.3`
- `internal-tools`: visual regression disabled by default

### Type 3: Failure Screenshot (Evidence)

On test failure, capture the full page state for diagnosis.

```typescript
test.afterEach(async ({ page }, testInfo) => {
  if (testInfo.status !== 'passed') {
    // gstack browse: $B screenshot /tmp/bug.png + $B console
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/${testInfo.title}-FAILURE.png`,
      fullPage: true,
    });

    // Capture DOM snapshot (accessibility tree) for diagnosis
    const a11yTree = await page.accessibility.snapshot();
    require('fs').writeFileSync(
      `${SCREENSHOT_DIR}/${testInfo.title}-a11y-tree.json`,
      JSON.stringify(a11yTree, null, 2),
    );
  }
});
```

## Side-Channel Evidence (Console + Network)

Adapted from gstack browse's `$B console` and `$B network` commands. These run as passive listeners during the entire test:

```typescript
function setupDiagnostics(page: Page) {
  const diagnostics = {
    consoleErrors: [] as Array<{ type: string; text: string }>,
    failedRequests: [] as Array<{ url: string; status: number; failure: string }>,
  };

  // gstack browse: $B console --errors
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      diagnostics.consoleErrors.push({ type: msg.type(), text: msg.text() });
    }
  });

  // gstack browse: $B network
  page.on('requestfailed', (req) => {
    diagnostics.failedRequests.push({
      url: req.url(),
      status: 0,
      failure: req.failure()?.errorText ?? 'unknown',
    });
  });
  page.on('response', (res) => {
    if (res.status() >= 400) {
      diagnostics.failedRequests.push({
        url: res.url(), status: res.status(), failure: res.statusText(),
      });
    }
  });

  return diagnostics;
}
```

## Responsive Snapshot Strategy

Adapted from gstack browse's `$B responsive [prefix]` and `$B viewport WxH` commands:

```typescript
const VIEWPORTS = {
  desktop: { width: 1920, height: 1080 },
  laptop: { width: 1366, height: 768 },
  tablet: { width: 768, height: 1024 },
  mobile: { width: 375, height: 812 },
};

test.describe('Responsive layout verification', () => {
  for (const [name, viewport] of Object.entries(VIEWPORTS)) {
    test(`layout at ${name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto(BASE_URL);
      await expect(page).toHaveScreenshot({
        name: `responsive-${name}`,
        fullPage: true,
      });
    });
  }
});
```

## Console Error as Test Assertion

```typescript
test.afterEach(async ({ page }, testInfo) => {
  // gstack browse: $B console --errors would show these
  if (diagnostics.consoleErrors.length > 0) {
    console.warn(`[${testInfo.title}] Console errors:`, diagnostics.consoleErrors);
    // For P0 tests: fail on console errors
    if (testInfo.title.match(/E2E-.*-P0/)) {
      throw new Error(`Console errors in P0 test: ${diagnostics.consoleErrors.map(e => e.text).join('; ')}`);
    }
  }
});
```

## Baseline Management

```
First run: no baseline exists → Playwright auto-creates
Subsequent runs: compare against saved baseline
To update: npx playwright test --update-snapshots

Baseline storage:
{testDir}/{testFileName}-snapshots/{snapshotName}-{project}-{platform}.png
Example:
_output/test-artifacts/e2e/REQ-001/browser-e2e.spec.ts-snapshots/
  E2E-CART-001-after-submit-chromium-linux.png
```

Baselines are versioned alongside the test script. When the E2E design changes, baselines should be regenerated with `--update-snapshots`.
