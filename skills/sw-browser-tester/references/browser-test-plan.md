# Browser Test Plan

## What This Is

Environment and execution configuration for L3 browser E2E testing. Defines browser selection, viewport configuration, network conditions, authentication state, and test execution parameters.

## Environment Verification (Before Any Test)

```bash
# 1. Check Playwright installation
npx playwright --version

# 2. Install browser dependencies if missing
npx playwright install --with-deps chromium

# 3. Check target URL reachable
curl -s -o /dev/null -w '%{http_code}' ${TARGET_URL}
# Expected: 2xx or 3xx

# 4. Check test data endpoint (if available)
curl -s ${TARGET_URL}/api/test/health || echo "Test data API not available"
```

### Playwright Install (if missing)

```bash
npm install -D @playwright/test
npx playwright install --with-deps chromium
# For multi-browser compatibility tests, also install:
npx playwright install --with-deps firefox webkit
```

## Browser Selection

| business_domain | Browsers Required | Rationale |
|----------------|-------------------|-----------|
| `fintech` | chromium, firefox, webkit | Financial apps: must work on all major browsers |
| `ecommerce` | chromium, firefox, webkit | Consumer-facing: must support all major browsers |
| `general` | chromium, firefox | Broad coverage without WebKit overhead |
| `internal-tools` | chromium | Team uses a single browser |

Config override in `_context/config.yaml`:
```yaml
sw:
  browser_e2e:
    browsers: ["chromium", "firefox", "webkit"]
```

## Viewport Configuration

Standard viewports adapted from gstack browse `$B responsive` pattern:

| Name | Width | Height | Device Scale Factor | Use Case |
|------|-------|--------|---------------------|----------|
| Desktop HD | 1920 | 1080 | 1 | Default desktop |
| Desktop | 1366 | 768 | 1 | Common laptop |
| Desktop Small | 1024 | 768 | 1 | Minimum desktop |
| Tablet | 768 | 1024 | 2 | iPad portrait |
| Mobile | 375 | 812 | 3 | iPhone 15 |
| Mobile Small | 320 | 568 | 2 | iPhone SE |

Viewport per test category:
- Happy path: Desktop HD (primary)
- Responsive layout: Desktop HD + Tablet + Mobile (all 3)
- Touch interactions: Mobile (primary) + Tablet
- Accessibility (keyboard nav): Desktop HD

## Network Condition Simulation

gstack browse does not have built-in network throttling. Playwright provides two approaches:

### Option 1: CDP-based (real throttling)
```typescript
const client = await page.context().newCDPSession(page);
await client.send('Network.enable');
await client.send('Network.emulateNetworkConditions', {
  offline: false,
  downloadThroughput: (1.6 * 1024 * 1024) / 8,   // 1.6 Mbps
  uploadThroughput: (750 * 1024) / 8,             // 750 Kbps
  latency: 150,                                    // ms
});
```

### Option 2: Route-based (simulate specific failures)
```typescript
// Simulate API being slow/unavailable
await page.route('**/api/**', async (route) => {
  await new Promise((resolve) => setTimeout(resolve, 5000));
  await route.continue();
});
```

Network condition presets:

| Network | Download | Upload | Latency | Use Case |
|---------|----------|--------|---------|----------|
| WiFi / 4G | 10 Mbps | 5 Mbps | 50ms | Default (no throttling) |
| 4G Slow | 1.6 Mbps | 750 Kbps | 150ms | Mobile slow connection |
| 3G | 400 Kbps | 400 Kbps | 300ms | Slow network |
| 2G/Edge | 100 Kbps | 100 Kbps | 800ms | Very slow / rural |

## Authentication State

### Option 1: storageState (recommended)
```typescript
// playwright.config.ts
export default defineConfig({
  projects: [{
    name: 'chromium',
    use: {
      storageState: '_context-output/test-artifacts/e2e/auth.json',
    },
  }],
});
```

### Option 2: auth.setup.ts (standalone setup)
```typescript
// auth.setup.ts — run once to save auth state
import { test as setup } from '@playwright/test';

setup('authenticate', async ({ page }) => {
  await page.goto(`${process.env.TARGET_URL}/login`);
  await page.fill('[data-testid="email-input"]', process.env.TEST_USER_EMAIL!);
  await page.fill('[data-testid="password-input"]', process.env.TEST_USER_PASSWORD!);
  await page.click('[data-testid="login-btn"]');
  await page.waitForSelector('.dashboard', { state: 'visible' });
  await page.context().storageState({
    path: '_context-output/test-artifacts/e2e/auth.json',
  });
});
```

### Option 3: API-based auth (no browser login)
```typescript
const tokenResp = await fetch(`${BASE_URL}/api/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: TEST_USER.email, password: TEST_USER.password }),
});
const { token } = await tokenResp.json();
await page.evaluate((t) => { localStorage.setItem('auth_token', t); }, token);
```

## Test Execution Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `timeout` | 30000ms | Per-test timeout |
| `expect.timeout` | 10000ms | Per-assertion timeout |
| `retries` | 0 (CI: 2) | Failed test retries |
| `workers` | 1 | Parallel workers (browser tests are resource-heavy) |
| `reporter` | `json` + `html` | Test report formats |
| `trace` | `on-first-retry` | Playwright trace recording |
| `screenshot` | `only-on-failure` | Automatic failure screenshot |
| `video` | `retain-on-failure` | Video recording on failure |

Config override in `_context/config.yaml`:
```yaml
sw:
  browser_e2e:
    timeout_ms: 30000
    retries: 2
    workers: 1
    trace_mode: "on-first-retry"
    screenshot_mode: "only-on-failure"
```

## playwright.config.ts Template

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  timeout: 30000,
  expect: { timeout: 10000 },
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['json', { outputFile: 'results.json' }],
    ['html', { outputDir: 'playwright-report' }],
  ],
  use: {
    baseURL: process.env.TARGET_URL ?? 'http://localhost:3000',
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Conditionally add Firefox/WebKit based on business_domain config
  ],
});
```

## Test Data Strategy

- **Seeding**: Prefer API-based seeding (NOT direct DB inserts). Ensures tests go through same code paths as real users.
- **Cleanup**: Always clean up in afterEach, even if test fails.
- **Isolation**: Each test creates unique test data (timestamp-suffixed IDs). Tests do NOT share state. No cross-test dependencies.

## TEA Config Integration

The TEA config at `_context/tea/config.yaml` provides infrastructure-level settings:
```yaml
tea_use_playwright_utils: true    # Use Playwright for browser automation
tea_browser_automation: auto      # Auto-detect browser availability
```

The browser tester reads these in Step 2 (Environment Setup):
- `tea_use_playwright_utils: false` → skip browser testing, report as SKIPPED
- `tea_browser_automation: manual` → prompt user to start browser before tests
