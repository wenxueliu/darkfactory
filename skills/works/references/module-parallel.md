# Module-parallel execution

在 `impact-check` 后把每个 Req 按 Maven module 拆成 `module-plan.json`。任务粒度固定为 `Req × module`，每项包含 `id`、`req`、`module`、`depends_on`、`write_scope`、`changed_behaviors` 和 `database_dependencies`。

对 DAG 做拓扑分 Wave。同一 Wave 的任务必须写入范围互不重叠，并受 `max_parallel` 限制。公共模块、父 POM、共享生成物或 migration 冲突必须建成前置独占任务，不能放入并行 Wave。

## Wave 执行

读取 `status.next_action.tasks` 后，主 Agent 先锁定当前 `HEAD` 为该 Wave 唯一的 `base_commit`，然后在同一轮启动全新、只读 Subagent。所有 Subagent读取同一基线，不创建 worktree、分支或 commit，也不得写主工作区；它们只返回 unified Git patch 和结构化结果。不要顺序等待。每个 Subagent只可：

1. 基于只读源码设计任务 `write_scope` 内的生产修改。
2. 为修改行为设计一个全新的 Mockito 测试文件，不读取、修改或模仿 baseline 中已有测试。
3. 在测试补丁中用 Mockito 隔离 `database_dependencies`；禁止 Spring test context、真实 DataSource、ORM/MyBatis context、Testcontainers、H2 或数据库 URL。
4. 返回只包含任务生产文件和一个新测试文件的 patch，以及主 Agent应执行的精确 testcase；不声称已经编译或测试。
5. 不执行写文件、Maven、`git apply`、commit 或 merge。

主 Works Agent 等整个 Wave 的结果全部返回后，把 patch 写入 `evidence/task-results/patches/`，确认共享工作区仍位于共同基线且没有 tracked 修改，再校验哈希、文件范围和同 Wave 不重叠约束。`patch-check` 通过后按 task id 稳定排序逐个执行 `git apply`、`mvn -pl <module> -Dtest=<Class#method> -DskipTests=false -Dmaven.test.skip=false test` 和单一 commit。主 Agent是唯一写入者和测试执行者。发生 patch 冲突、越权修改或失败测试时，不得手工覆盖冲突或推进 Wave；中止本 Wave，回退尚未提交的当前 patch，修订任务/DAG 后从新的共同基线重新派发。

Subagent 返回后，先把候选结果写到 `evidence/task-results/<normalized-task-id>-<sha256前8位>.json`，状态使用 `PATCH_READY`，此时不含 `commit`、`test_evidence`。normalized task id 使用字符替换规则，哈希按原始 task id 计算，以保证 Windows 文件名兼容且避免碰撞。运行 `patch-check` 通过后主 Agent才可应用补丁。每项提交和定向测试通过后，把同一结果更新为以下最终结构：

```json
{
  "task": "REQ-1:user-service",
  "status": "PASS",
  "base_commit": "base123",
  "patch_file": "patches/REQ-1-user-service-acde1234.patch",
  "patch_sha256": "64位sha256",
  "commit": "merged123",
  "changed_files": ["user-service/src/main/java/UserService.java"],
  "covered_files": ["user-service/src/main/java/UserService.java"],
  "test_file": "user-service/src/test/java/UserServiceWorksTest.java",
  "testcase": "UserServiceWorksTest#createsUser",
  "database_mocks": ["UserRepository"],
  "test_command": ["mvn", "-pl", "user-service", "-Dtest=UserServiceWorksTest#createsUser", "-DskipTests=false", "-Dmaven.test.skip=false", "test"],
  "test_evidence": {"exit": 0, "executed": 1, "failures": 0, "errors": 0}
}
```

结果齐备并完成提交后运行 `wave-check`。CLI 会用稳定 `patch-id` 证明主提交与 Subagent 补丁语义一致，静态检查范围和 Mockito 策略，并由主控制面重新执行每个精确 testcase。只有整个 Wave 通过才能进入下一 Wave。

最终 `coverage_scope` 明确记录为 `changed-code-only`；不得声称执行了完整回归、数据库集成或跨模块 E2E 测试。
