---
name: works
description: >
  存量 Java/Maven 代码的需求落地与安全修改 skill。用户输入 /works，或要求依据
  requirement.md 在既有 Maven 项目中增强功能、复用已有 Service API、分析影响范围并完成
  测试验证时使用。以 planning-with-files 保存长任务状态，按可观察行为执行纵向 TDD 切片，
  保护已有工作区改动，并以可复现的测试证据而不是口头声明作为完成条件。
---

# Works

自主发现项目目录和 `requirement.md`，在存量仓库中完成需求，同时把误改范围和未验证声明降到最低。模型容易在长任务后段急于实现、省略验证或绕过 Service 直接操作 Mapper，因此所有推进依据都写入磁盘，并由架构边界检查、命令退出码和证据文件判定，而不是依赖对话记忆。

## Start here — TDD takes precedence over delivery speed

这是本 skill 的最高优先级执行顺序，先于分析后的“快速实现”、最小改动和交付速度：

1. 自主定位项目和 requirement。
2. 初始化 planning 会话及 `tdd_slice.py init`。
3. 运行 `tdd_slice.py probe`，证明 Maven 没有跳过测试。
4. 只做影响分析和写当前 Req 的一个测试；不得修改生产代码。
5. 运行 `tdd_slice.py red` 并取得有效 `red.json`。
6. 只有此时才允许修改当前 Req 的生产代码，然后运行 Green。

任何“先把功能快速写完，再补测试/证据”的路径都属于任务失败。时间压力、需求简单、修改很小、用户未强调测试、项目原来缺测试，以及 POM 中存在 `skipTest=true`、`skipTests=true` 或 `maven.test.skip=true`，都不是例外。Skip 配置只说明默认构建可能不执行测试，必须在测试命令中显式覆盖并用新鲜报告证明目标 testcase 实际运行。

## Run contract

- 自动执行需求明确且可逆的仓库内操作；不得覆盖、回滚或格式化用户的无关改动。
- 全程无人值守，不向用户请求确认项目目录、需求路径、测试 seam、实现方案、阶段推进或“是否继续下一个 Req”。先自主搜索、推导和验证；信息仍不足时采用最保守且可逆的方案并记录假设，确实无法安全继续时写明 blocked 证据后停止，不把问题抛回给用户。只有不可逆操作、权限扩张或互斥且无法从仓库判定的业务语义才允许暂停。
- 业务入口必须优先复用现有 Service/Application Service API，不能为了少写代码从 Controller、Job、Listener、Command handler 或其他上层入口直接调用 Mapper/DAO/Repository。缺少能力时优先扩展最匹配的 Service 接口及实现，再由 Service 调用持久化层。
- 不复制已有实现。新增独立职责、数据契约或适配边界时可以新增类型，并在 `findings.md` 记录理由。
- 测试文件必须进入最终交付 diff。除非用户明确授权，不执行 `git commit`、push 或其他发布操作。
- 只把实际运行且退出码符合预期的命令标记为通过；不得根据代码外观推断测试或编译成功。
- 必须读取并执行本 skill 的 [TDD evidence gate](references/tdd-evidence.md)；`tdd` skill 可用时同时读取其测试设计原则。本 skill 的无人值守规则覆盖其中所有人工确认要求：从需求、公共接口、调用方和已有测试选择最窄 seam，并把依据写入计划文件，不询问用户。

## 1. Preconditions and persistent plan

1. 从当前目录开始自主定位项目，不要求用户提供路径：先用 `git rev-parse --show-toplevel` 确定允许搜索的工作树边界；再检查当前目录及其逐级祖先直到 Git 根，随后在 Git 根内有限深度搜索 `requirement.md`、`pom.xml` 和 `mvnw`。以“需求文档与可解析的根/聚合 POM 属于同一项目”的最近目录作为候选根；多个候选时按当前目录直接匹配 > 祖先链匹配 > Git 根内子项目匹配 > 聚合模块关系排序，并把选择证据写入 `findings.md`。没有 Git 元数据时以当前 workspace 根作为边界。不得越过边界、跟随符号链接或扫描无关大型目录。
2. 自主读取并解析 `requirement.md`；文件名大小写或位置略有差异时，在候选项目内搜索 `*requirement*.md`、`requirements/`、`docs/`，按 Git 跟踪状态、与当前项目的关联和更新时间选择最可信来源。没有可信需求文档时记录搜索范围并标记 blocked，不询问用户。
3. 确认 Git 状态和构建入口。优先 `./mvnw`，其次 `mvn`；读取 CI、README、父 POM、模块、profile、Surefire/Failsafe、Maven Enforcer、toolchains、`.java-version` 或 `.sdkmanrc`，不要擅自设置 `JAVA_HOME`。
4. 记录 `git status --short` 作为修改前基线；已有改动属于用户，不得覆盖。
5. 初始化隔离的 planning-with-files gated 会话；若当前环境不支持硬停止门禁，则保留相同文件协议并把 gate 视为 advisory：

   ```bash
   sh <planning-with-files>/scripts/init-session.sh --gated "works-<requirement-slug>"
   ```

6. 启用结构化注入：在计划目录 `.mode` 中保留 `autonomous gate` 并加入 `inject-smart`。计划形成后直接运行 `attest-plan.sh`，不等待用户确认。若计划发生有意变更，更新后重新 attestation。
   - 记录并固定活动 `PLAN_ID`；执行目录可能漂移时同时设置 `PWF_PLAN_ROOT` 为项目根绝对路径。
   - `task_plan.md` 的任何状态、Next Step 或决策修改都会使旧 attestation 失效；在阶段边界批量修改计划，随后立即重新运行 `attest-plan.sh`。切片内高频细节只写 `findings.md`、`progress.md` 和 ledger。
7. 使用 [references/plan-contract.md](references/plan-contract.md) 填写唯一的六阶段计划。`task_plan.md` 只保存目标、状态、门禁和下一动作；分析写入 `findings.md`；命令摘要写入 `progress.md`；原始输出保存到计划目录下的 `logs/`。
8. `tdd_slice.py` 的 init/probe/red/green/verify 成功后会自动调用 `works_plan_gate.py sync`，更新 `works-state.json`、唯一 Next Step、ledger 和 attestation。不得手工伪造这些状态，也不得直接调用 `phase-status.sh` 完成 Phase 2–6；只能使用 `works_plan_gate.py complete-phase` 让磁盘证据决定能否推进。
9. 影响分析完成后，用 `works_plan_gate.py set-reqs --req <REQ-1> --req <REQ-2> ...` 按执行顺序固化完整 Req 队列。每个 Green 后自动选择第一个未完成 Req 并继续 Red；不得输出询问、等待确认或提前交付。只有队列清空后才能进入 verify/acceptance。

### Planning ownership

- 主代理是 `task_plan.md`、`progress.md` 和需求追踪矩阵的唯一写入者。
- 子代理优先承担边界清晰的只读探索、测试诊断或独立审查；也可实现单个纵向切片，但必须拥有互不重叠的文件范围和客观验收条件。每个子代理写自己的 ledger，完成时返回 [references/handoff.md](references/handoff.md) 格式的交接包。
- 交接包引用文件和日志路径，不复制大段源码或输出。主代理验证后才把结论合并进计划。
- 每完成一个阶段、每次失败和每次策略改变都立即落盘。连续两次搜索/浏览后，把关键发现写入 `findings.md`。
- 上下文压缩或恢复后，先运行 `works_plan_gate.py sync`，再读取 `works-state.json`、活动计划、`findings.md`、`progress.md` 和最新 handoff，随后执行 `session-catchup.py`；以 `works-state.json` 的状态和单一 Next Step 继续，不凭对话回忆重建进度。

## 2. Baseline gate

1. 运行项目原有的最小可信测试命令；若代价可接受，再运行完整基线。保存命令、退出码、测试数量和日志路径。
2. 分类失败，禁止把所有失败都解释为生产代码缺陷：

   | 失败类型 | 处理 |
   |---|---|
   | 修改前已有测试失败 | 记录 baseline failure；若与需求无关，可隔离后继续，但最终明确披露；若相关则阻塞 |
   | 新 characterization test 失败 | 先审查测试预期、fixture 和 seam；不能据此擅自修复生产代码 |
   | 本次 diff 引入失败 | 回到当前 TDD 切片修复 |
   | 环境、依赖或配置失败 | 诊断基础设施，不将其记为 Red，也不声称功能失败 |

3. 本阶段只建立修改前原有测试基线；此时不要在尚未完成影响分析的 seam 上提前编写 characterization test。
4. 基线确认后、任何新功能测试或生产代码修改前，运行 `scripts/tdd_slice.py init`，把当前含用户既有改动的工作区保存为 TDD 内容基线。初始化失败时不得进入实现阶段。
5. 搜索父/子 POM、profiles、Surefire/Failsafe 和 CI 中的测试跳过配置。选择一个现有稳定通过的 testcase，运行 `tdd_slice.py probe`。所有测试命令至少包含 `-DskipTests=false -Dmaven.test.skip=false`，并覆盖脚本发现的自定义 `skip*test*` 属性；只有本次新建/变化的报告证明目标 testcase 执行并通过时 preflight 才完成。无法解除 skip 时标记 blocked，不能进入实现。

## 3. Impact map

解析每条 requirement，并在 `findings.md` 建立追踪矩阵：

| Req ID | 可观察行为 | 入口/seam | Service API | Mapper/Repository | 直接调用方 | 配置/数据影响 | 测试 | 风险 |
|---|---|---|---|---|---|---|---|---|

通过符号搜索、调用方、实现类、配置、序列化、数据库迁移和已有测试交叉验证候选修改点。不要声称识别了不可证明的“全部影响”；记录已覆盖的直接依赖和无法静态确认的反射、SPI、动态配置等风险。

### Service boundary gate

对每条 requirement 沿调用链执行 `入口 → Service 接口 → Service 实现 → Mapper/DAO/Repository` 检查：

1. 搜索现有 Service 接口、实现、调用方和测试，按业务语义而不是名称相似度选择复用点。
2. 如果已有 Service API 能表达该用例，入口层只能调用该 API；禁止重复其逻辑或直接调用底层 Mapper。
3. 如果 Service 能力缺失，在职责最匹配的 Service 中增加最小业务方法并保持兼容，由 Service 负责校验、授权、事务、跨 Mapper 编排和领域规则。
4. Mapper/DAO/Repository 只负责持久化查询与写入，不承载业务编排；Service 内可以调用它们，但应优先复用已有 Service 方法，避免跨领域复制查询或更新逻辑。
5. 只有项目已有且有测试、调用惯例或架构文档证明的模式才允许绕过普通 Service：CQRS 中隔离、只读、无业务规则的 Query handler；Mapper/Repository 自身实现与切片测试；或项目已有同类模式的迁移/基础设施批处理。Spring Data REST 仅在项目已经明确采用该资源模型，且目标操作不绕过已有 Service、领域不变量、授权、审计、事件或事务编排时视为既定例外；它不为普通 Controller 或新的业务写路径提供许可。写操作、跨表操作、带权限/幂等/状态转换/事务/副作用的操作不得使用只读例外。
6. 若发现拟修改入口新增了 Mapper/DAO/Repository 依赖，默认判定为架构门禁失败；重新设计为 Service API，除非已记录上述例外证据。
7. `tdd_slice.py init` 会记录现存入口→持久层违规基线；每次 Green 和 Phase 4–6 都运行 `service_boundary.py verify`。任何新增的 Controller/Endpoint/Job/Listener/Consumer/Handler → Mapper/DAO/Repository 或 `JdbcTemplate`、`EntityManager`、`SqlSession`、`DSLContext` 等直接数据访问依赖都会阻止推进。先寻找至少两个相邻同类调用链，复用现有 Service；确无能力时扩展职责匹配的 Service API。

开始实现前检查：

- 每条 requirement 都有可观察行为和验收测试位置。
- 候选修改符合现有架构；新增类型有明确的新职责。
- 每条入口调用都经过 Service boundary gate，矩阵中列出复用或扩展的 Service API；没有无证据的 Mapper 直调。
- 明确 IN/OUT scope、兼容性风险和回滚面。
- 计划的下一动作精确到一个纵向切片，而不是“一次实现所有功能”。

影响图确定后、生产代码修改前，仅为“将被修改且缺少行为保护”的公共 seam 增加 characterization test，并确认它在修改前通过。仅被调用但行为不变的 API 不强制补测试。

## 4. Vertical TDD loop

一次只处理一个最小行为切片：

1. **Orient**：重读计划的 Goal、Current Phase、Next Step，以及矩阵中当前 Req ID。
2. **Red gate**：只写一个公共 seam 行为测试，不改生产代码；必须为目标测试方法提供稳定 testcase ID，通过 `tdd_slice.py red` 运行最窄测试命令并生成该 Req ID 的 `red.json`。只有目标 testcase 在本次新建/变化的 Surefire/Failsafe 报告中出现 assertion failure 才有效；无关失败、旧报告、编译、fixture、依赖、环境或 test error 不是有效 Red。
3. **Production edit gate**：读取 `red.json`，确认 Req ID、测试文件哈希、命令和 assertion failure 均有效后，才允许首次修改当前切片的生产代码。没有 `red.json` 时禁止 Write/Edit/apply_patch 或 shell 写入任何生产路径。
4. **Green gate**：只实现使当前测试通过的最小改动；先复用或扩展 Service API，再由 Service 使用 Mapper/Repository。必须通过 `tdd_slice.py green` 运行与 Red 完全相同的选择器并生成 `green.json`；Red 测试内容不得被弱化或改写。
5. **Local regression**：运行当前测试、相关 characterization tests 和受影响模块测试。多模块 Maven 默认考虑 `-pl <module> -am`。
6. **Evidence**：把 `red.json`、`green.json`、命令、退出码、测试数和日志路径写入 `progress.md`；更新追踪矩阵。
7. **Review**：检查 `git diff --check`、本次 diff 和用户原有改动边界。满足当前切片验收条件后才进入下一切片。

Green 成功后不要向用户汇报阶段性完成并询问是否继续。读取 `works-state.json` 中的 `remaining_reqs`，立即进入下一 Req 的 Orient→Red；只以 ledger/plan 记录阶段进度。

当运行环境支持子代理时，重要切片使用隔离验收：实现者写 handoff 后，由 fresh verifier 仅根据 requirement、diff 和磁盘证据返回 `PASS`、`CHANGES_REQUIRED` 或 `BLOCKED`。主代理仍需复跑关键测试；子代理的 DONE/PASS 不是完成证据。为避免共享上下文放大实现偏见，verifier 不继承实现过程，只读取最小 handoff 和引用制品。

### Repair loop

测试未通过时留在当前切片，执行最多三轮有差异的修复：

1. 根据完整错误和最小复现定位根因，做定向修复。
2. 同类失败再次出现时，必须改变诊断假设或工具，不重复相同操作。
3. 第三次仍失败时，重新检查 requirement、seam、fixture、模块边界和计划；写 handoff 包进行独立审查（有子代理时优先隔离审查）。

三轮后仍无进展，标记 blocked 并给出证据，不得通过删测试、弱化断言、跳过模块或伪造日志推进。连续两轮同类失败时优先换用 fresh worker 或 fresh verifier，避免 tunnel vision；出现新的可验证假设时可以开启下一轮，并在计划中记录为何值得继续。

## 5. Acceptance loop

所有切片完成后按由窄到宽的顺序验证：

1. 对所有 Req ID 运行 `tdd_slice.py verify`；它必须重跑每个保存的精确测试命令，确认目标 testcase 仍执行并通过，并确认当前生产指纹等于最后 Green checkpoint。缺少 Red→Green 链、证据被修改、测试被改写/禁用、选择器不一致或 Green 后追加生产修改时立即失败并重开 Phase 4。
2. 新功能测试和 characterization tests。
3. 受影响模块及其依赖模块测试。
4. 项目规定的完整测试或 CI 等价命令。
5. 必要时 integration/Failsafe、静态检查、格式检查和 package/compile；优先项目已有命令，不把单独 `mvn compile` 当成充分验收。
6. 对照 requirement 逐行审计追踪矩阵和最终 diff。
7. 搜索本次变更新增的 Mapper/DAO/Repository 注入和调用；任何上层入口直调都必须有已记录且测试覆盖的架构例外，否则验收失败。项目已有 ArchUnit 或 Spring Modulith 时，运行并按现有风格补充层级/模块依赖测试，避免入口包依赖 mapper/repository 或模块 internal 包。

第 2–5 项的代表性真实命令必须通过 `works_plan_gate.py check --name <名称> -- <命令>` 运行，保存退出码、日志及哈希；Phase 5 没有成功的 `acceptance.json` 不能完成。

任一验收失败都重新打开对应阶段或切片，更新 `Current Phase` 与 `Next Step`，进入 Repair loop。只有所有必要命令通过、每条 requirement 有证据、工作区边界检查通过时，才把验证阶段标为 complete。planning-with-files 的停止门禁以磁盘状态为准；不得为了结束会话提前把阶段标记为 complete。

## 6. Delivery and handoff

最终报告必须包含：

- requirement 完成情况及 Req ID；
- 修改和新增文件，以及新增类型的理由；
- 实际运行的验证命令、结果、测试数量和日志路径；
- baseline 已有失败、未运行检查及原因；
- 用户原有改动是否保持不变；
- 未决风险和恢复执行所需的活动 plan ID。

交付前运行 planning-with-files 的 `check-complete.sh`。它只验证计划状态，不会执行测试，也不能作为测试 oracle；完成必须同时满足“真实命令与追踪矩阵证据门”和“六阶段状态门”。若平台即将压缩、暂停或转交代理，先写 handoff 包并刷新单一 `Next Step`。

## Anti-shortcut checks

在每次阶段切换和最终交付前逐项确认：

- 是否出现了实现代码先于有效 Red？若是，回退到可证明的 Red-Green 证据，不伪造历史。
- 是否每个 Req ID 都有脚本生成且 `verify` 通过的 `red.json`/`green.json`？人工填写 progress 表不算 TDD 证据。
- 是否把“命令看起来正确”当成“测试已通过”？必须有真实退出码。
- 是否为赶进度缩小了测试范围却没有披露？恢复必要验证或标明 blocked/incomplete。
- 是否一次修改了多个未验证行为？拆回单一纵向切片。
- 是否仍有 pending/in_progress 阶段、未覆盖 Req ID 或未读失败日志？不得完成。
- 是否因上下文变长开始重复搜索或遗忘约束？写入磁盘、生成 handoff，并从计划重新定向。
- 是否从入口层新增了 Mapper/DAO/Repository 调用，或复制了已有 Service 逻辑？若是，回到影响分析并改为复用/扩展 Service。

## References

- [Plan contract](references/plan-contract.md) — 六阶段 gated 计划和证据格式。
- [Handoff protocol](references/handoff.md) — 子代理、压缩和跨会话恢复交接包。
- [Evaluation loop](references/evaluation.md) — 真实仓库回归评测与 skill 迭代方法。
- [MiniMax M2.7 field profile](references/minimax-m2.7.md) — 官方能力与实际公开反馈的差异及对应防护。
- [Service boundary](references/service-boundary.md) — Service 与 Mapper/Repository 的分层规则、例外和权威依据。
- [TDD evidence gate](references/tdd-evidence.md) — 可执行的 dirty-baseline、Red、Green 和最终验证协议。
