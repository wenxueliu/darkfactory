# 特性设计验证器 (Feature Design Validator)

## 触发时机

特性设计文档 (`designs/{requirement_id}-design.md`) 完成后，进入 Stage 2 之前。

## 验证清单

### V1: 完整性

- [ ] 9 个章节完整 (标注 N/A 的章节需有理由)
- [ ] Section 1: 成功标准有可衡量的目标值 (非 "提升用户体验" 等模糊描述)
- [ ] Section 2: 服务影响分析覆盖了所有受影响服务，每个服务有影响类型和风险等级
- [ ] Section 3: 用户旅程覆盖完整 happy path，每个步骤标注 AC 编号和涉及服务
- [ ] Section 4: 页面设计 (如涉及 UI) 有页面清单 + 组件清单 + 交互细节
- [ ] Section 5: 每个跨服务调用有 SLA 和降级策略 (微服务模式必检)
- [ ] Section 6: 跨服务契约有提供方和消费方声明 (微服务模式必检)
- [ ] Section 7: 部署策略有发布序列 + 回滚方案 + 监控指标

### V2: 一致性

- [ ] 服务影响分析 (Section 2) 中的服务列表与服务交互 (Section 5) 中的参与者一致
- [ ] 用户旅程 (Section 3) 中引用的 AC 编号与需求规格中的 AC 编号一致
- [ ] 跨服务契约 (Section 6) 中的端点与 per-service 涉及的端点无冲突
- [ ] 发布序列 (Section 7) 的顺序与服务依赖关系一致 (被依赖服务先发布)
- [ ] 无循环的服务依赖 (A → B → A)

### V3: 可过渡性

- [ ] 服务影响分析足够清晰，hw-service-designer 能从中提取每个服务的变更范围
- [ ] 跨服务契约足够具体，hw-service-designer 能从中生成 API 测试
- [ ] 用户旅程足够具体，hw-e2e-designer 能从中设计 E2E 场景
- [ ] 开放问题不会阻塞 Stage 2 启动 (阻塞性问题已解决或升级)

## 输出

```
PASS: → 进入 Stage 2 (per-service 详细设计)
FAIL: → 标记缺失项，回到特性设计修订。最大重试 3 轮。
       3 轮后仍未 PASS → 升级到人工决策。
```
