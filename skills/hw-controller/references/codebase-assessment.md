# 代码库评估 (Codebase Assessment)

参考: Sisyphus orchestrator DNA — oh-my-openagent Phase 1 代码库状态评估

## 核心理念

在执行开放型任务之前，必须快速评估代码库状态。代码库的状态分类决定了后续的行为策略——在 "Disciplined" 的代码库中可以做更大胆的改动，在 "Legacy-Chaotic" 的代码库中则需要更谨慎，每一步都要验证。

**原则: 评估而非评判。** 有些看似 "chaotic" 的代码是有意为之的（性能优化、历史兼容、紧急修复）。在判断为不规范的代码之前，先验证是否有意为之。

## 评估流程 (3 步)

### 第 1 步: 检查配置与项目结构

检查以下文件的存在和内容（按优先级）：

| 检查项 | 信号 | 指示 |
|--------|------|------|
| linter/formatter 配置 | `.eslintrc`, `.prettierrc`, `pyproject.toml`, `checkstyle.xml`, `golangci-lint.yml` 等 | Disciplined 信号 — 团队重视代码一致性 |
| CI 配置 | `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `Makefile` 中的 test/lint target | Disciplined 信号 — 有自动化验证流程 |
| 测试文件分布 | `tests/`, `__tests__/`, `*_test.go`, `*Test.java` 等，与源码同目录 vs 集中式 | 测试的存在和位置反映团队的测试文化 |
| 构建配置 | `build.gradle`, `package.json`, `go.mod`, `Cargo.toml` 等 | 确认技术栈和依赖管理方式 |
| 环境配置 | `.env.example`, `docker-compose.yml`, `Dockerfile`, `application.yml` | 了解部署和环境管理方式 |
| 文档文件 | `README.md`, `CONTRIBUTING.md`, `ARCHITECTURE.md` | 了解团队对文档的重视程度 |
| Git 历史 | `git log --oneline -20` | 提交信息规范性、PR 大小、是否 squash merge |

### 第 2 步: 抽取代表性文件

选择 3-5 个代表性文件，检查模式一致性：

```
抽取策略:
  1. 1 个最近修改的文件 (git diff --name-only HEAD~5)
  2. 1 个核心业务逻辑文件 (service/controller/use-case)
  3. 1 个工具类/辅助文件
  4. 1 个测试文件
  5. 1 个配置文件
```

对每个文件检查：
- **命名一致性:** 同一概念是否用同样的命名？有无 `userID` / `userId` / `user_id` 混用？
- **结构一致性:** 同类型文件是否有相似的结构？（如 controller 都有 try-catch-wrapper）
- **注释风格:** 注释是描述 "what" 还是 "why"？有无过期注释？
- **错误处理一致性:** 同类型操作是否用同样的错误处理方式？
- **导入/依赖组织:** import 是否有规律可循？

### 第 3 步: 项目年龄信号

通过以下信号判断项目成熟度：

| 信号 | 新项目 (<6mo) | 中期项目 (6mo-2yr) | 老项目 (>2yr) |
|------|---------------|-------------------|---------------|
| Git 提交数 | <100 | 100-1000 | >1000 |
| 依赖版本 | 最新版 | 近 1-2 个大版本 | 可能有固定版本/内部 fork |
| 代码注释 | 少（代码自解释） | 中等 | 可能有技术债务注释 (TODO/FIXME/HACK) |
| 重构痕迹 | 几乎没有 | 有一些 | 可见明显的架构演进 |
| 测试数量 | 少但增长 | 中等 | 多但可能有跳过的 legacy 测试 |

## 状态分类

### Disciplined (规范化)

**信号:**
- 代码模式高度一致（同类文件结构相同）
- linter/formatter 配置存在且已配置
- 测试文件与源文件并存，覆盖率有指标
- CI pipeline 包含 lint + test + build
- 提交信息有规范格式 (conventional commits)
- 有架构文档或至少 README 清楚说明项目结构

**对应策略:**
- 可以信任现有模式，遵循即安全
- 新增代码直接模仿同类型文件
- 测试作为文档来读（了解预期行为）
- 可以相对大胆地重构（有测试网兜底）

### Transitional (过渡期)

**信号:**
- 新旧代码模式混合（如部分 controller 用了新框架，部分还是旧的）
- 部分模块有测试，部分没有
- linter 配置存在但规则较宽松或有大量 disabled rules
- 代码中存在 `// TODO: migrate to X` 的注释
- 部分目录结构与主结构不一致

**对应策略:**
- 确认目标模式——查看最近合并的 PR 来确定团队正在迁移到哪个方向
- 新代码使用目标模式（非旧模式）
- 对无测试的模块，改前先加 characterization tests
- 改动最小化，不趁机做大范围重构（除非任务本身是迁移）

### Legacy-Chaotic (遗留混乱)

**信号:**
- 同类文件结构差异大，无明显模式可循
- 没有测试或测试已长期不运行
- 无 linter/formatter 配置
- 无 CI 或 CI 常年红色无人维护
- 依赖版本锁定在很旧的版本
- 大量注释掉的代码或过期的 TODO
- 需要手动步骤才能部署（无自动化）

**对应策略:**
- **极度谨慎。** 每次改动前先写 characterization tests 锁住现有行为
- 改动范围最小化——只改必须改的
- 不要自主重构（即使看到明显的坏味道）
- 每步改动后验证（手工 + 自动化）
- 记录发现的坏味道，但不在此次任务中修复
- 如果需要大范围改动，先提案获得批准

### Greenfield (绿地)

**信号:**
- 空目录或仅含脚手架文件
- 无实际业务代码
- 可能有 `package.json` / `go.mod` 但无 src 目录
- 无 git 历史或仅初始化提交

**对应策略:**
- 从零建立规范——现在做的选择会成为后续代码的基础模式
- 优先设立 linter + formatter + CI
- 创建第一个模块时，考虑到它会被后续模块复制模仿
- 写清晰的 README 和架构文档

## 验证步骤 (Verification)

在将代码库判定为 "undisciplined" 之前，必须执行以下验证：

### 验证 1: 不一致是有意为之吗？

```
检查项:
  - 不一致的代码是否来自不同的时期（git blame 看时间跨度）？
  - 是否有 ADR 或 comment 解释为什么此处与其他地方不同？
  - 这个 "不一致" 是否实际上是一种优化（如 bypass ORM 直接写 SQL 是为了性能）？
```

### 验证 2: 缺少测试是有原因的吗？

```
检查项:
  - 是否在 git 历史中能找到被删除的测试？（可能是有意移除）
  - 项目是否为原型/概念验证阶段？（此时无测试可以理解）
  - 是否使用了其他验证手段（如 property-based testing, contract testing）？
```

### 验证 3: "混乱" 是否只是你不熟悉？

```
检查项:
  - 使用的框架/模式是否你不够熟悉？
  - 是否可能存在你没发现的组织逻辑（如按 feature 组织 vs 按 layer 组织）？
  - 是否有 DI 框架使得显式依赖不那么明显？
```

**红牌规则:** 如果 3 项验证都通过（即找不到有意为之的证据），才可以判定为 Transitional 或 Legacy-Chaotic。否则，保持 Disciplined 假设。

## 评估产物

完成代码库评估后，输出评估摘要：

```yaml
# 代码库评估摘要
project: "{project-name}"
assessment_date: "{timestamp}"
state: "Disciplined | Transitional | Legacy-Chaotic | Greenfield"

signals:
  has_linter_config: true|false
  has_formatter_config: true|false
  has_ci_config: true|false
  has_tests: true|false
  test_coverage_indicator: "high | medium | low | none"
  pattern_consistency: "high | medium | low"
  commit_message_convention: "conventional-commits | informal | inconsistent"
  documentation_quality: "good | minimal | absent"

verified_undisciplined: true|false  # 是否经过 3 项验证后确认为不规范
false_positives_ruled_out:
  - "intentional_difference: {explanation}"
  - "missing_tests_explained: {explanation}"
  - "unfamiliarity_ruled_out: {explanation}"

recommended_posture: "confident | cautious | extremely-cautious | foundational"
```

## 与后续阶段的衔接

```
Phase 1 (Codebase Assessment) 完成后:
  → Disciplined    → Phase 2A (Exploration) 可以轻量执行
  → Transitional   → Phase 2A 需要额外关注测试覆盖
  → Legacy-Chaotic → Phase 2A 必须先找 characterization tests 的目标
  → Greenfield     → Phase 2A 重点在外部研究（无内部代码可探索）

所有状态 → 提案（针对 Open-ended）或直接进入实现（针对 Explicit）
```
