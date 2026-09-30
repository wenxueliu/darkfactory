# 服务设计协调 (Service Design Coordination)

## 核心理念

服务设计的目标是产出一份可执行的服务详细设计——足够详细，让 TDD Agent 能从设计文档直接执行 RED→GREEN→REFACTOR 循环。

## 协调流程 (5 步)

### 第 1 步: 服务类型检测

1. Load `references/service-type-detection.md`
2. 读取 `paths.evidence.service_registry` → 查找当前 `{service_id}`
3. 如果 `services[].type` 有值 → 使用显式类型
4. 否则，根据 `services[].language` 推断类型
5. 解析对应定义包: `service-design/{type}`，使用其 manifest 选择模板、门禁和验证器
6. 类型无法识别 → 默认 `backend` + 警告

即使只有一个仓库也执行检测；服务类型来自注册表或仓库代码，无法识别时才默认 `backend` 并警告。

### 第 2 步: 上下文加载

根据 `design_scope` 选择唯一上游：

- `single_service`: 读取 `paths.evidence.requirement_document` 和
  `paths.evidence.requirements_gate_report`，从需求 AC 和服务边界提取变更内容；
- `cross_service_detail`: 读取 `paths.evidence.bundle_manifest` 和
  `paths.evidence.feature_design`，从 Section 2 "服务影响分析"、Section 5
  "服务交互设计" 和 Section 6 "跨服务契约" 提取该服务内容。

两种模式都读取 `paths.evidence.service_knowledge_root` 下的现有知识。

### 第 3 步: 架构与接口设计

按服务类型模板的 S1-S6 章节逐节填充:

- **后端:** S1 技术决策 → S2 架构设计 → S3 API/接口设计 → S4 状态管理 → S5 错误处理 → S6 安全设计
- **前端:** S1 技术决策 → S2 组件架构 → S3 API 集成 → S4 客户端状态 → S5 错误UI → S6 客户端安全
- **BFF:** S1 技术决策 → S2 BFF架构 → S3 API设计(双面) → S4 数据聚合/转换 → S5 错误/降级 → S6 安全
- **数据管道:** S1 技术决策 → S2 管道架构 → S3 数据Schema/转换 → S4 状态管理(checkpoint) → S5 错误/重试 → S6 数据安全

### 第 4 步: 测试用例设计

#### L1 UT 设计 (对应模板 Section S7)

1. Load `references/test-case-template.md`
2. 每个 public 方法 ≥ 2 UT 用例 (1 happy + 1 error/boundary)
3. 每个组件 ≥ 1 edge 用例
4. 所有输入/输出为具体值，无占位符
5. 每条用例附带数据构造代码块 (输入 + mock + 预期输出)
6. 填充 UT 用例 → 需求 AC 追溯表

#### L2 API 测试设计 (对应模板 Section S8)

1. Load `references/api-test-case-template.json`
2. Load `references/api-test-postman-schema.md`
3. 每个端点 ≥ 3 API 用例 (正常 ×1 + 异常 ×1 + 认证/权限 ×1)
4. 生成 `paths.artifact_targets.api_collection` (Postman Collection)
5. 生成 `paths.artifact_targets.api_environment` (Environment 文件)
6. 有数据驱动场景时生成 `paths.artifact_targets.api_data`；执行 Newman
   时将报告写入 `paths.artifact_targets.api_report`
7. JSON 中的 `item[].name` 前缀与设计文档的用例 ID 一一对应

### 第 5 步: 输出与过渡

**输出产物:**
- `paths.artifact_targets.design_document`
- `paths.artifact_targets.gate_report`
- `paths.artifact_targets.api_collection`
- `paths.artifact_targets.api_environment`
- 可选的 `paths.artifact_targets.api_data` 和 `paths.artifact_targets.api_report`
- `cross_service_detail` 成功时更新 `paths.artifact_targets.bundle_manifest`
  中的当前服务条目；`single_service` 只发布解析后的服务设计产物，不创建
  feature bundle manifest

**过渡条件:**
- S1-S8 所有章节完整
- 每个组件 ≥ 2 UT 用例 + 数据构造代码块
- 每个端点 ≥ 3 API 用例
- API JSON 文件有效且与设计文档对应
- UT 用例 → 需求 AC 追溯完整

**完成确认语:** "{service_id} ({service_type}) 详细设计完成。UT: {N} cases, API: {M} cases。API 测试 JSON 已生成。"

## 并行执行

多个服务的设计可并行执行:
- 跨服务时，sw-controller 从特性设计 Section 2 提取所有受影响服务
- 单服务时，sw-controller 直接启动 `sw-service-designer(single_service)`
- 跨服务时，对每个服务启动 `sw-service-designer(cross_service_detail)` 实例
- 各实例独立执行，互不阻塞
- 只有跨服务时总控等待全部完成后再进入 Stage 3 (E2E 设计)
