# Module-parallel execution

在 `impact-check` 后把每个 Req 按 Maven module 拆成 `module-plan.json`。任务粒度固定为 `Req × module`，每项包含 `id`、`req`、`module`、`depends_on`、`write_scope`、`changed_behaviors` 和 `database_dependencies`。

对 DAG 做拓扑分 Wave。同一 Wave 的任务必须写入范围互不重叠，并受 `max_parallel` 限制。公共模块、父 POM、共享生成物或 migration 冲突必须建成前置独占任务，不能放入并行 Wave。

## Wave 执行

读取 `status.next_action.tasks` 后，主 Agent 先锁定当前 `HEAD` 为该 Wave 唯一的 `base_commit`。在同一轮为每项创建独立任务分支和 Git worktree，再从对应 worktree 启动一个全新 Subagent；禁止 Subagent 在主工作区或其他任务的 worktree 中写入。分支名必须包含规范化 task id（把 Git ref 禁止的字符替换为 `-`，例如 `REQ-1:user-service` 使用 `works/REQ-1-user-service`），所有分支都直接从同一个 `base_commit` 创建，不得从同 Wave 的其他任务提交派生。不要顺序等待。每个 Subagent只可：

1. 修改任务 `write_scope` 内的生产文件。
2. 新建一个测试文件，不读取、修改或模仿 baseline 中已有测试。
3. 使用 Mockito 隔离 `database_dependencies`；禁止 Spring test context、真实 DataSource、ORM/MyBatis context、Testcontainers、H2 或数据库 URL。
4. 只运行 `mvn -pl <module> -Dtest=<Class#method> -DskipTests=false -Dmaven.test.skip=false test`。`-am` 只允许编译依赖，禁止无 selector、`verify`、`package` 或全量测试。
5. 提交且只提交一个 `source_commit`，其唯一父提交必须是 `base_commit`，返回结构化 task result。

主 Works Agent 等整个 Wave 的 Subagent 全部结束后，先验证各 worktree 的分支、基线和单一提交，再按 task id 稳定排序逐个 `git cherry-pick` 到主分支，并记录每次 cherry-pick 产生的 `merged_commit`。不得让 Subagent自行合并。发生越权修改、合并冲突或失败测试时，不得覆盖解决或推进 Wave；中止本 Wave，修订任务/DAG 后从新的共同基线重新派发。worktree 和任务分支至少保留到 `wave-check` 通过，之后才可清理。

把每个结果写到 `evidence/task-results/<normalized-task-id>-<sha256前8位>.json`；normalized task id 使用与分支相同的字符替换规则，哈希按原始 task id 计算，以保证 Windows 文件名兼容且避免碰撞：

```json
{
  "task": "REQ-1:user-service",
  "status": "PASS",
  "base_commit": "base123",
  "source_commit": "task123",
  "merged_commit": "merged123",
  "branch": "works/REQ-1-user-service",
  "worktree": "/absolute/project/.worktree/REQ-1-user-service",
  "changed_files": ["user-service/src/main/java/UserService.java"],
  "covered_files": ["user-service/src/main/java/UserService.java"],
  "test_file": "user-service/src/test/java/UserServiceWorksTest.java",
  "testcase": "UserServiceWorksTest#createsUser",
  "database_mocks": ["UserRepository"],
  "test_command": ["mvn", "-pl", "user-service", "-Dtest=UserServiceWorksTest#createsUser", "-DskipTests=false", "-Dmaven.test.skip=false", "test"],
  "test_evidence": {"exit": 0, "executed": 1, "failures": 0, "errors": 0}
}
```

结果齐备并完成合并后运行 `wave-check`。CLI 会静态检查范围和 Mockito 策略，并由主控制面重新执行每个精确 testcase。只有整个 Wave 通过才能进入下一 Wave。

最终 `coverage_scope` 明确记录为 `changed-code-only`；不得声称执行了完整回归、数据库集成或跨模块 E2E 测试。
