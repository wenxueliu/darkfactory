# 服务设计协调 (Service Design Coordination)

## 核心理念

服务设计的目标是产出一份可执行的服务详细设计——足够详细，让 TDD Agent 能从设计文档直接执行 RED→GREEN→REFACTOR 循环。

## 协调流程 (5 步)

### 第 1 步: 服务类型检测

1. Load `references/service-type-detection.md`
2. 读取 `service-registry.yaml` → 查找当前 `{service_id}`
3. 如果 `services[].type` 有值 → 使用显式类型
4. 否则，根据 `services[].language` 推断类型
5. 加载对应模板: `references/service-design-template-{type}.md`
6. 类型无法识别 → 默认 `backend` + 警告

单体模式: 跳过检测，默认 `backend`。

### 第 2 步: 上下文加载

1. 读取 `designs/{requirement_id}-design.md` (Stage 1 输出)
2. 从 Section 2 "服务影响分析" 提取该服务的变更内容
3. 从 Section 5 "服务交互设计" 提取该服务参与的调用序列
4. 从 Section 6 "跨服务契约" 提取该服务提供/消费的契约
5. 读取 `knowledge-base/services/{service_id}/` 下的现有知识

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
4. 生成 `tests/api-{requirement_id}-{service_id}.json` (Postman Collection)
5. 生成 `tests/api-{requirement_id}-{service_id}-env.json` (Environment 文件)
6. JSON 中的 `item[].name` 前缀与设计文档的用例 ID 一一对应

### 第 5 步: 输出与过渡

**输出产物:**
- `designs/{requirement_id}-service-{service_id}-design.md`
- `tests/api-{requirement_id}-{service_id}.json`
- `tests/api-{requirement_id}-{service_id}-env.json`

**过渡条件:**
- S1-S8 所有章节完整
- 每个组件 ≥ 2 UT 用例 + 数据构造代码块
- 每个端点 ≥ 3 API 用例
- API JSON 文件有效且与设计文档对应
- UT 用例 → 需求 AC 追溯完整

**完成确认语:** "{service_id} ({service_type}) 详细设计完成。UT: {N} cases, API: {M} cases。API 测试 JSON 已生成。"

## 并行执行

多个服务的设计可并行执行:
- sw-controller 从特性设计 Section 2 提取所有受影响服务
- 对每个服务启动 sw-service-designer 实例
- 各实例独立执行，互不阻塞
- 总控等待全部完成后再进入 Stage 3 (E2E 设计)
