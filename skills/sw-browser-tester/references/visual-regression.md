# Visual Regression Strategy

## What This Is

Screenshot comparison strategy for detecting unintended visual changes in browser E2E tests. Adapted from gstack browse's `$B snapshot -D` (diff against previous snapshot) — Playwright's built-in `toHaveScreenshot()` provides pixel-level visual comparison.

## When to Use Visual Regression

| Scenario | Use Visual Regression? | Rationale |
|----------|----------------------|-----------|
| Critical checkout/payment flow | Yes (P0) | Visual regression here = potential revenue loss |
| Landing page / marketing pages | Yes (P0) | First impression matters |
| Dashboard / data visualization | Yes (P1) | Charts must render correctly |
| Admin panels / internal tools | Optional (P2) | Visual consistency less critical |
| Loading states / spinners | No | Non-deterministic timing |
| Third-party embeds (maps, ads) | No | Content not under our control |
| Real-time data (stock tickers) | No | Values change constantly |

## Baseline Management

### First Run: Create Baselines
```bash
npx playwright test browser-e2e.spec.ts --update-snapshots
```

Baselines saved to:
```
{testFileDir}/{testFileName}-snapshots/{snapshotName}-{project}-{platform}.png
# Example:
# browser-e2e.spec.ts-snapshots/E2E-CART-001-after-submit-chromium-linux.png
```

### Subsequent Runs: Compare Against Baselines
```bash
npx playwright test browser-e2e.spec.ts
```

### Updating Baselines (Intentional Changes)
```bash
# Update all baselines
npx playwright test browser-e2e.spec.ts --update-snapshots

# Update specific test baselines only
npx playwright test browser-e2e.spec.ts -g "E2E-CART-001" --update-snapshots
```

**Policy:** Baseline updates require explicit human approval. The sw-browser-tester reports visual diffs and asks before updating.

## Threshold Configuration

Per-domain thresholds:

| business_domain | maxDiffPixels | threshold | Notes |
|----------------|---------------|-----------|-------|
| `fintech` | 50 | 0.1 | Strict — financial UI must be pixel-perfect |
| `ecommerce` | 100 | 0.2 | Moderate — some variance acceptable |
| `general` | 200 | 0.3 | Relaxed — focus on functional correctness |
| `internal-tools` | disabled | disabled | Visual regression not required |

- **maxDiffPixels**: Maximum number of different pixels before test fails
- **threshold**: Pixelmatch comparison threshold (0-1). 0 = exact match, 1 = anything matches

Config in `_context/config.yaml`:
```yaml
sw:
  browser_e2e:
    visual_regression:
      max_diff_pixels: 100
      threshold: 0.2
      enabled: true
```

## Handling Dynamic Content

### Masking Unstable Elements

Dynamic content (dates, timestamps, random IDs, avatars) causes false positives. Mask them:

```typescript
await expect(page).toHaveScreenshot({
  name: 'dashboard',
  fullPage: true,
  mask: [
    page.locator('[data-testid="current-time"]'),    // Clock
    page.locator('[data-testid="user-avatar"]'),     // Avatar image
    page.locator('.timestamp'),                       // Dates
  ],
  maxDiffPixels: 100,
});
```

Common patterns to mask:

| Pattern | Masking Selector |
|---------|-----------------|
| Dates / timestamps | `[data-testid="timestamp"]`, `.date-display` |
| User avatars | `img[class*="avatar"]`, `[data-testid="avatar"]` |
| Randomized IDs / UUIDs | Elements matching UUID regex |
| Ad placements | `.ad-container`, `iframe[src*="third-party"]` |
| Dynamic charts | Mask canvas OR replace with mock data |

### Animation Handling

```typescript
// Disable CSS animations/transitions during comparison
await expect(page).toHaveScreenshot({
  name: 'after-action',
  animations: 'disabled',  // Pauses CSS animations, transitions, requestAnimationFrame
});

// Manually wait for animations to finish (alternative)
await page.waitForTimeout(1000);
await page.evaluate(() => document.fonts.ready); // Wait for fonts
```

## Visual Diff Reporting

When a visual regression is detected:

```
Visual Regression Detected:
  Test: E2E-CART-001
  Snapshot: checkout-success-page-chromium-linux.png
  Diff pixels: 342 (threshold: 100)
  Diff image: output/E2E-CART-001-checkout-success-page-diff.png
  
  Analysis: ".order-total" element shifted 12px right.
  
  Action options:
  A) Update baseline (expected change from new feature)
  B) Fix the code (unintended regression)
```

## Cross-Platform Baselines

Screenshots differ between OS platforms due to font rendering differences:

1. **Run tests on CI (Linux)** — Baselines are generated and compared on Linux
2. **Platform-specific baselines** — Playwright postfixes snapshot names with `-linux`, `-darwin`, `-win32`
3. **Don't compare cross-platform** — Linux baseline vs Linux run only

```bash
# CI: Linux baselines are authoritative
npx playwright test browser-e2e.spec.ts --project=chromium
# Creates: *-chromium-linux.png

# Local: macOS generates its own baselines (first run)
npx playwright test browser-e2e.spec.ts --project=chromium --update-snapshots
# Creates: *-chromium-darwin.png (separate from Linux baselines)
```

## Snapshot Comparison Flow (adapted from gstack browse)

gstack browse pattern:
```
$B snapshot (baseline) → $B click @e3 (action) → $B snapshot -D (diff)
```

Playwright equivalent:
```
1. Navigate to page
2. Wait for stable state (networkidle + fonts loaded + no animations)
3. [Optional] Mask dynamic elements
4. Take "before" screenshot (or use toHaveScreenshot baseline)
5. Perform action (click, fill, submit)
6. Wait for stable state
7. Take "after" screenshot with toHaveScreenshot({ name: 'after-action' })
8. Playwright diffs against saved baseline → pass or fail
```

Unlike gstack's real-time `-D` diff (agent reads the diff output), Playwright diffs are pixel-based and reported as pass/fail with a diff image.
