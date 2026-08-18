# Runnable fixtures

Generate four deterministic Git/Maven repositories outside the skill tree:

```bash
python3 fixtures/build_fixtures.py --output /tmp/works-eval-fixtures
```

The repositories cover Service-boundary temptation, dirty-worktree preservation, invalid Red classification, and POM test-skip overrides. Reset a fixture with `git reset --hard HEAD` and remove generated planning/build files before each candidate run. Use the same generated repository copy for the stable-skill and candidate-skill runs.

The fixture builder pins compiler, JUnit and Surefire versions in each POM. A benchmark run therefore requires a full JDK with `javac`, plus Maven dependency access or a pre-populated local Maven cache.
