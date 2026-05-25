# 3-Stage 设计委托模式

**Type:** Pattern
**Created:** 2026-05-04
**Scope:** enterprise
**Author:** hw-controller

## Summary

hw-controller 将设计阶段工作委托给三个专用 Agent 依次执行，总控负责串联、验证和决策，不直接编写设计文档的编排模式。

## Details

设计阶段被拆分为 3 个可验证的阶段，每个阶段由独立 Agent 完成，总控（hw-controller）负责启动、验证和成果物收集。

**Stage 1: 特性设计 (hw-feature-designer)**
- 输入：需求规格文档 + 知识库(ADRs/patterns/lessons) + 服务注册表
- 前置要求：必须先完成服务能力调查（代码级调查，不能凭名称臆想）
- 输出：跨服务设计文档（服务影响分析、用户旅程、服务交互、跨服务契约、部署策略）
- 验证：通过 feature-design-validator.md 检查 G1-G4

**Stage 2: 服务详细设计 (hw-service-designer)**
- 对 Stage 1 识别的每个受影响服务并行启动设计
- 输入：Stage 1 输出（服务影响分析 + 能力摘要）+ 服务代码仓库路径
- 输出：per-service 设计文档 × N + API 测试设计 × N
- 验证：通过 service-design-validator.md 检查 V1-V4
- 并行度：最多 max_parallel_services 个同时设计（默认 4）

**Stage 3: E2E 测试设计 (hw-e2e-designer)**
- 输入：Stage 1（用户旅程）+ 所有 Stage 2（API 契约 + 错误处理）
- 输出：E2E 测试设计文档
- 验证：通过 e2e-design-validator.md 检查 V1-V5

**协调机制**：Stage 1 → 总控收集服务影响列表 → 启动 Stage 2（并行）→ 所有 Stage 2 完成 → 总控收集所有 per-service 设计 → 启动 Stage 3 → Stage 3 完成 → 进入 ADR 创建和多模型验证。

## Context

适用于涉及多个服务的复杂特性设计场景。单体模式时 Stage 2 可以简化（一个服务即整体应用），微服务模式时 Stage 2 的并行度优势明显。

## Usage

由 hw-controller 在 design phase 自动执行。需要确保 hw-feature-designer、hw-service-designer、hw-e2e-designer 三个 Agent skill 已部署并可从 hw-controller 触发。每个阶段的输出路径遵循约定：designs/{id}-design.md / designs/{id}-service-{service_id}-design.md / designs/{id}-e2e-design.md。

## Related

- ADR-0004: Agent 主动认领任务而非框架推送（设计委托使用了类似的 Agent 职责分离思想）
- DAG 依赖推进模式（3-Stage 之间也有类似 DAG 的阶段依赖关系）
- 可追溯性矩阵（设计完成后需要建立从需求 AC 到设计决策到任务的追溯链）
