# Executable TDD evidence gate

`scripts/tdd_slice.py` makes Red-before-Green independently checkable. It records the existing dirty worktree as the initial baseline, advances an immutable-by-protocol production checkpoint after each successful Green, runs the named tests itself, parses fresh Surefire/Failsafe XML, and hashes the Red test and logs.

## Initialize once

After the baseline phase and before writing any new feature test or production code:

```bash
python <works>/scripts/tdd_slice.py init \
  --project-root "$PROJECT_ROOT" \
  --state-dir "$PLAN_DIR/tdd"
```

The snapshot includes existing tracked, staged, unstaged and untracked production files by content hash. Those user changes are therefore the protected starting point, not mistaken for feature implementation.

## Prove Maven really executes tests

Before feature Red, choose one existing stable passing testcase and run:

```bash
python <works>/scripts/tdd_slice.py probe \
  --state-dir "$PLAN_DIR/tdd" \
  --testcase ExistingTest#knownBehavior \
  -- ./mvnw -pl module -am \
     -DskipTests=false -Dmaven.test.skip=false \
     -Dtest=ExistingTest#knownBehavior test
```

The script scans project POMs for true-valued `skip*test*` properties and requires explicit `-D<property>=false` overrides in addition to the two standard flags. Probe passes only when a new or changed report proves the selected testcase executed successfully. A POM skip flag is a build default to override, never evidence that tests are unimportant.

## Establish Red

Write one behavior test, then let the script run the narrow command:

```bash
python <works>/scripts/tdd_slice.py red \
  --state-dir "$PLAN_DIR/tdd" \
  --req REQ-1 \
  --test-file module/src/test/java/example/FeatureTest.java \
  --testcase FeatureTest#behavior \
  -- ./mvnw -pl module -am -DskipTests=false -Dmaven.test.skip=false \
     -Dtest=FeatureTest#behavior test
```

Valid Red requires all of the following:

- no production file differs from the latest successful Green checkpoint（第一个切片使用 initialized dirty-worktree baseline）；
- the named test file changed after initialization;
- the command exits non-zero;
- a fresh Surefire/Failsafe report contains at least one executed test and assertion failure;
- the named `--testcase` itself executed and contains the assertion failure; an unrelated failing test cannot establish Red;
- the report contains no test error. Compilation, fixture, dependency and environment failures are invalid Red.

The script compares report hashes before and after the command and copies only new or changed XML into the slice evidence directory, so a stale report cannot establish Red.

## Establish Green

After the minimum production change, run the exact same selector:

```bash
python <works>/scripts/tdd_slice.py green \
  --state-dir "$PLAN_DIR/tdd" \
  --req REQ-1 \
  -- ./mvnw -pl module -am -DskipTests=false -Dmaven.test.skip=false \
     -Dtest=FeatureTest#behavior test
```

The Red test content hash must be unchanged through Green, the selector must be identical, and production content must differ from this slice's Red checkpoint. A successful Green advances `checkpoint.json`, so the next Req can establish Red on top of already completed slices. If the test expectation was wrong, discard the slice evidence, correct the test, restore production to that slice's checkpoint, and establish a new Red. Do not weaken a test between Red and Green.

## Verify before phase completion

```bash
python <works>/scripts/tdd_slice.py verify \
  --state-dir "$PLAN_DIR/tdd" \
  --req REQ-1 --req REQ-2
```

`verify` fails when a requirement lacks a complete Red→Green chain, the per-slice production checkpoint chain breaks, current production differs from the final Green checkpoint, baseline/evidence/log/report hashes fail, Green has no production change, or selectors differ. After Green, later slices may append methods to the same Java/Kotlin/Groovy-style test class, but the brace-balanced body of every established target testcase must remain byte-for-byte identical. Verify also reruns every saved exact command against fresh reports and requires the target testcase to execute and pass, so `@Disabled`, class-level disabling and build exclusions cannot satisfy the gate. Save `tdd-verify.json` in acceptance evidence.

`init` refuses to overwrite an existing baseline. Req IDs are restricted to safe filename characters, preventing evidence paths from escaping the state directory. Record `baseline.sha256` in `progress.md` and the attested plan so an unexpected reinitialization or baseline change is visible during recovery.

## Skill-only enforcement boundary

This skill intentionally does not install or modify host hooks. The evidence gate detects implementation-first work because production diverges from the current checkpoint, and final verification refuses completion without a valid chain. It cannot physically intercept a write when the model ignores the skill entirely. Therefore keep the Start here sequence at the top of `SKILL.md`, make init/probe/Red explicit planning gates, and never describe planning-with-files' Stop gate as a production-write barrier.
